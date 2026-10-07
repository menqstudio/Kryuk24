"""Internal approval contract. No executor, HTTP routes or external authority."""
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from runtime import encode, now


@dataclass(frozen=True)
class ApprovalPrincipal:
    actor: str
    role: str


def canonical(value):
    def check(v):
        if v is None or type(v) in (str, int, bool):return
        if type(v) is list:
            for x in v:check(x)
            return
        if type(v) is dict and all(type(k) is str for k in v):
            for x in v.values():check(x)
            return
        raise ValueError('only JSON objects/lists/strings/integers/booleans/null allowed')
    check(value)
    raw = encode(value)
    if len(raw.encode()) > 65536:raise ValueError('contract too large')
    return raw


def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()


def timestamp(value):
    if not isinstance(value, str):raise ValueError('timezone-aware expiry required')
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None or dt.utcoffset() is None:raise ValueError('timezone-aware expiry required')
    return dt.astimezone(timezone.utc)


class ApprovalStore:
    FIELDS = {'action', 'account', 'target', 'payload', 'assets', 'amount', 'inputs', 'expires_at', 'test'}

    def __init__(self, runtime, approver_actor, allowed_actions=(), clock=None):
        if not isinstance(approver_actor, str) or not approver_actor.strip():raise ValueError('explicit approver identity required')
        if not isinstance(allowed_actions, (tuple, list, set, frozenset)) or any(not isinstance(a, str) or not a.strip() for a in allowed_actions):
            raise ValueError('explicit action allowlist required')
        self.runtime = runtime
        self.approver = approver_actor
        self.allowed = frozenset(allowed_actions)  # default deny all
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        with runtime.db() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS action_approval_drafts (
 id TEXT PRIMARY KEY, draft_key TEXT UNIQUE NOT NULL, bundle TEXT NOT NULL,
 digest TEXT NOT NULL, author TEXT NOT NULL, status TEXT NOT NULL,
 claim_key TEXT, claimant TEXT, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS action_approval_events (
 id INTEGER PRIMARY KEY, draft_id TEXT NOT NULL, kind TEXT NOT NULL,
 data TEXT NOT NULL, created TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS action_approval_immutable
BEFORE UPDATE OF bundle,digest,author,draft_key ON action_approval_drafts
BEGIN SELECT RAISE(ABORT,'approval bundle is immutable'); END;
''')

    @staticmethod
    def text(x):
        if not isinstance(x, str) or not x.strip() or len(x) > 2000:raise ValueError('nonempty bounded text required')
        return x

    def principal(self, p, role):
        if not isinstance(p, ApprovalPrincipal) or p.role != role:raise PermissionError(role + ' required')
        self.text(p.actor)
        if role == 'APPROVER' and p.actor != self.approver:raise PermissionError('configured approver required')

    def bundle(self, b):
        if type(b) is not dict or set(b) != self.FIELDS:raise ValueError('exact contract fields required')
        canonical(b)
        for key in ('action', 'account', 'target'):self.text(b[key])
        if b['action'] not in self.allowed:raise PermissionError('action not allowlisted')
        if type(b['payload']) is not dict or type(b['inputs']) is not dict or not b['inputs']:
            raise ValueError('payload and nonempty dependency fingerprint map required')
        if any(not k.strip() or not isinstance(v, str) or not re.fullmatch('[a-f0-9]{64}', v) for k, v in b['inputs'].items()):
            raise ValueError('inputs require named SHA256 fingerprints')
        if type(b['assets']) is not list:raise ValueError('assets list required')
        names = set()
        for a in b['assets']:
            if type(a) is not dict or set(a) != {'id', 'sha256'}:raise ValueError('asset id/hash required')
            self.text(a['id'])
            if a['id'] in names or not isinstance(a['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', a['sha256']):raise ValueError('unique asset/hash required')
            names.add(a['id'])
        if b['amount'] is not None:
            a = b['amount']
            if type(a) is not dict or set(a) != {'currency', 'kopecks'} or a['currency'] != 'RUB' or type(a['kopecks']) is not int or a['kopecks'] < 0:
                raise ValueError('amount must be explicit nonnegative RUB kopecks or null')
        if type(b['test']) is not bool:raise ValueError('explicit test boolean required')
        timestamp(b['expires_at'])
        canonical(b)
        return b

    def row(self, c, did):
        r = c.execute('SELECT * FROM action_approval_drafts WHERE id=?', (did,)).fetchone()
        if not r:raise LookupError('draft not found')
        return r

    @staticmethod
    def view(r):return dict(id=r['id'], bundle=json.loads(r['bundle']), digest=r['digest'], status=r['status'])

    def event(self, c, did, kind, p, data):
        c.execute('INSERT INTO action_approval_events(draft_id,kind,data,created) VALUES(?,?,?,?)',
                  (did, kind, encode({'actor': p.actor, 'role': p.role, **data}), now()))

    def freshness(self, r, current_inputs):
        b = json.loads(r['bundle'])
        if timestamp(b['expires_at']) <= self.clock():return 'EXPIRED'
        if canonical(current_inputs) != canonical(b['inputs']):return 'STALE'
        return None

    def draft(self, p, key, bundle):
        self.principal(p, 'PREPARER');self.text(key);self.bundle(bundle)
        if timestamp(bundle['expires_at']) <= self.clock():raise ValueError('expiry must be in future')
        raw = canonical(bundle); dg = digest(bundle)
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            r = c.execute('SELECT * FROM action_approval_drafts WHERE draft_key=?', (key,)).fetchone()
            if r:
                if r['digest'] != dg or r['author'] != p.actor:raise ValueError('draft key reused')
                return self.view(r)
            did = 'APR-' + uuid.uuid4().hex
            c.execute('INSERT INTO action_approval_drafts VALUES(?,?,?,?,?,?,NULL,NULL,?)', (did, key, raw, dg, p.actor, 'PENDING', now()))
            self.event(c, did, 'DRAFTED', p, {'digest': dg})
            return self.view(self.row(c, did))

    def decide(self, did, p, expected_digest, decision, current_inputs, evidence):
        self.principal(p, 'APPROVER');self.text(evidence)
        if decision not in ('APPROVED', 'REJECTED'):raise ValueError('explicit decision required')
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE');r = self.row(c, did)
            if r['digest'] != expected_digest:raise ValueError('digest mismatch')
            if r['status'] != 'PENDING':raise ValueError('pending draft required')
            self.bundle(json.loads(r['bundle']))
            stale = self.freshness(r, current_inputs)
            status = stale or decision
            c.execute('UPDATE action_approval_drafts SET status=? WHERE id=?', (status, did))
            self.event(c, did, status, p, {'evidence': evidence, 'digest': expected_digest})
            return self.view(self.row(c, did))

    def revoke(self, did, p, evidence):
        self.principal(p, 'APPROVER');self.text(evidence)
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE');r = self.row(c, did)
            if r['status'] not in ('PENDING', 'APPROVED'):raise ValueError('cannot revoke consumed/terminal approval')
            c.execute("UPDATE action_approval_drafts SET status='REVOKED' WHERE id=?", (did,))
            self.event(c, did, 'REVOKED', p, {'evidence': evidence})
            return self.view(self.row(c, did))

    def claim(self, did, p, key, expected_bundle, current_inputs):
        """Reserve once. Reservation is NOT proof of external execution/success.

        Only the identical claimant/key can reconcile a reserved intent. This
        method returns no second executable grant; already_reserved is explicit.
        """
        self.principal(p, 'EXECUTOR');self.text(key);self.bundle(expected_bundle)
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE');r = self.row(c, did)
            if r['digest'] != digest(expected_bundle):raise ValueError('action/account/target/payload binding mismatch')
            if r['status'] == 'RESERVED':
                if r['claim_key'] != key or r['claimant'] != p.actor:raise ValueError('approval already consumed')
                return {'draft_id': did, 'status': 'RESERVED', 'new_reservation': False, 'execution_result': 'UNKNOWN'}
            if r['status'] != 'APPROVED':raise ValueError('approved draft required')
            stale = self.freshness(r, current_inputs)
            if stale:
                c.execute('UPDATE action_approval_drafts SET status=? WHERE id=?', (stale, did))
                self.event(c, did, stale, p, {})
                return {'draft_id': did, 'status': stale, 'new_reservation': False, 'execution_result': 'NOT_STARTED'}
            c.execute("UPDATE action_approval_drafts SET status='RESERVED',claim_key=?,claimant=? WHERE id=?", (key, p.actor, did))
            self.event(c, did, 'RESERVED', p, {'claim_key': key})
            return {'draft_id': did, 'status': 'RESERVED', 'new_reservation': True, 'execution_result': 'UNKNOWN'}

    def inspect(self, did, p):
        self.principal(p, 'APPROVER')
        with self.runtime.db() as c:
            r = self.row(c, did)
            events = [dict(e, data=json.loads(e['data'])) for e in c.execute('SELECT id,kind,data,created FROM action_approval_events WHERE draft_id=? ORDER BY id', (did,))]
            return {**self.view(r), 'history': events, 'external_execution_enabled': False}
