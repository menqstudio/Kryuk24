"""Internal request ledger. Trusted dispatcher only; no HTTP or external actions."""
import hashlib
import json
import uuid
from runtime import encode, now
from order_flow import Principal


class RequestFlow:
    CHANNELS = {'PHONE', 'WHATSAPP', 'TELEGRAM', 'SITE_FORM', 'OTHER', 'UNKNOWN'}
    OUTCOMES = {'DECLINED', 'NO_RESPONSE', 'DUPLICATE', 'OUT_OF_SCOPE'}

    def __init__(self, flow):
        self.flow = flow
        self.runtime = flow.runtime
        with self.runtime.db() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS business_requests (
 id TEXT PRIMARY KEY, source_key TEXT UNIQUE NOT NULL, digest TEXT NOT NULL,
 owner TEXT NOT NULL, data TEXT NOT NULL, status TEXT NOT NULL,
 revision INTEGER NOT NULL, conversion TEXT, order_id TEXT UNIQUE, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS business_request_events (
 id INTEGER PRIMARY KEY, request_id TEXT NOT NULL, kind TEXT NOT NULL,
 data TEXT NOT NULL, created TEXT NOT NULL);
''')

    def _principal(self, p):
        if not isinstance(p, Principal) or p.role != 'DISPATCHER':
            raise PermissionError('trusted dispatcher required')
        self.flow.text(p.actor, 'actor')

    def _row(self, c, rid, p):
        self._principal(p)
        row = c.execute('SELECT * FROM business_requests WHERE id=?', (rid,)).fetchone()
        if not row:
            raise LookupError('request not found')
        if row['owner'] != p.actor:
            raise PermissionError('request owner required')
        return row

    @staticmethod
    def _view(row):
        return {k: json.loads(row[k]) if k == 'data' else row[k]
                for k in ('id', 'owner', 'data', 'status', 'revision', 'order_id', 'created')}

    def _event(self, c, rid, kind, p, data):
        c.execute('INSERT INTO business_request_events(request_id,kind,data,created) VALUES(?,?,?,?)',
                  (rid, kind, encode({'actor': p.actor, **data}), now()))

    def receive(self, p, channel, source_ref, test, evidence, contact=None):
        """Reference is supplied by a trusted intake adapter, not an untrusted visitor."""
        self._principal(p)
        if channel not in self.CHANNELS or type(test) is not bool:
            raise ValueError('known channel and explicit test boolean required')
        for value, field in ((source_ref, 'source reference'), (evidence, 'evidence')):
            self.flow.text(value, field)
        if contact is not None:
            self.flow.text(contact, 'contact')
        data = dict(channel=channel, source_ref=source_ref, test=test,
                    evidence=evidence, contact=contact,
                    trust='TEST_ONLY' if test else 'DISPATCHER_ATTESTED')
        # Test and real identities cannot collide. No fuzzy matching by phone/time.
        source_key = encode([test, channel, source_ref])
        digest = hashlib.sha256(encode(data).encode()).hexdigest()
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT * FROM business_requests WHERE source_key=?', (source_key,)).fetchone()
            if old:
                self._row(c, old['id'], p)
                if old['digest'] != digest:
                    raise ValueError('source reference reused with changed facts')
                return self._view(old)
            rid = 'REQ-' + uuid.uuid4().hex
            c.execute('INSERT INTO business_requests VALUES(?,?,?,?,?,?,?,NULL,NULL,?)',
                      (rid, source_key, digest, p.actor, encode(data), 'OPEN', 0, now()))
            self._event(c, rid, 'RECEIVED', p, {'data': data})
            return self._view(self._row(c, rid, p))

    def get(self, rid, p):
        with self.runtime.db() as c:
            return self._view(self._row(c, rid, p))

    def dispose(self, rid, p, revision, outcome, evidence, duplicate_of=None):
        if outcome not in self.OUTCOMES:
            raise ValueError('unsupported outcome')
        self.flow.text(evidence, 'evidence')
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._row(c, rid, p)
            if type(revision) is not int or revision != row['revision'] or row['status'] != 'OPEN':
                raise ValueError('current OPEN request required')
            if outcome == 'DUPLICATE':
                if duplicate_of == rid:
                    raise ValueError('cannot duplicate itself')
                target = self._row(c, duplicate_of, p)
                if json.loads(target['data'])['test'] != json.loads(row['data'])['test']:
                    raise ValueError('test/real duplicate mismatch')
            elif duplicate_of is not None:
                raise ValueError('duplicate target only for DUPLICATE')
            c.execute('UPDATE business_requests SET status=?,revision=revision+1 WHERE id=?', (outcome, rid))
            self._event(c, rid, outcome, p, {'evidence': evidence, 'duplicate_of': duplicate_of})
            return self._view(self._row(c, rid, p))

    def convert(self, rid, p, revision, pickup, destination, vehicle, contact, evidence):
        """Recoverable conversion: persist intent, idempotent intake/adopt, then link.

        Retry with the EXACT original revision and payload after interruption.
        CONVERTING remains visible until that retry succeeds; no blind rollback.
        """
        for value, field in ((pickup, 'pickup'), (destination, 'destination'),
                             (vehicle, 'vehicle'), (contact, 'contact')):
            self.flow.text(value, field)
            if len(value) > 500:
                raise ValueError(field + ' exceeds runtime limit')
        self.flow.text(evidence, 'evidence')
        if type(revision) is not int:
            raise ValueError('integer revision required')
        intent = dict(revision=revision, pickup=pickup, destination=destination,
                      vehicle=vehicle, contact=contact, evidence=evidence)
        raw = encode(intent)
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._row(c, rid, p)
            if row['conversion'] is not None:
                if row['conversion'] != raw:
                    raise ValueError('conversion input changed')
                if row['status'] == 'CONVERTED':
                    return self._view(row)
                if row['status'] != 'CONVERTING':
                    raise ValueError('invalid conversion state')
            else:
                if row['status'] != 'OPEN' or row['revision'] != revision:
                    raise ValueError('current OPEN request required')
                c.execute("UPDATE business_requests SET status='CONVERTING',conversion=?,revision=revision+1 WHERE id=?", (raw, rid))
                self._event(c, rid, 'CONVERSION_STARTED', p, intent)
            data = json.loads(row['data'])
        order = self.runtime.intake(dict(contact=contact, pickup=pickup, destination=destination,
                                        vehicle=vehicle, test=data['test'], source=data['channel'],
                                        business_request_id=rid), 'business-request:' + rid)
        self.flow.adopt(order['id'], p, 0)
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._row(c, rid, p)
            if row['status'] == 'CONVERTING':
                c.execute("UPDATE business_requests SET status='CONVERTED',order_id=?,revision=revision+1 WHERE id=?", (order['id'], rid))
                self._event(c, rid, 'CONVERTED', p, {'order_id': order['id'], 'evidence': evidence})
            return self._view(self._row(c, rid, p))

    def history(self, rid, p):
        with self.runtime.db() as c:
            self._row(c, rid, p)
            return [dict(r, data=json.loads(r['data'])) for r in c.execute(
                'SELECT id,kind,data,created FROM business_request_events WHERE request_id=? ORDER BY id', (rid,))]

    def summary(self, p, test=False):
        self._principal(p)
        if type(test) is not bool:
            raise ValueError('explicit boolean filter required')
        with self.runtime.db() as c:
            rows = [r for r in c.execute('SELECT status,data FROM business_requests WHERE owner=?', (p.actor,))
                    if json.loads(r['data'])['test'] is test]
        return {'test': test, 'scope': 'OWNER_REQUEST_LEDGER_CUMULATIVE', 'requests': len(rows),
                'by_status': {s: sum(r['status'] == s for r in rows) for s in sorted({r['status'] for r in rows})},
                'conversion_meaning': 'ORDER_CREATED_NOT_PAID_OR_COMPLETED',
                'profit': 'UNKNOWN', 'sending_enabled': False}
