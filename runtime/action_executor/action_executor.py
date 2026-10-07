"""Simulation-only executor journal; no network, publishing, sending or payments."""
import json
from runtime import encode, now
from action_approval import digest


class SimulationAdapter:
    """Durable local fake service with lookup/readback. Never an external proof."""
    def __init__(self, runtime, actions):
        self.runtime = runtime
        self.actions = frozenset(actions)
        with runtime.db() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS executor_simulated_effects (
 execution_key TEXT PRIMARY KEY, bundle_digest TEXT NOT NULL, result TEXT NOT NULL)''')

    def validate(self, bundle):
        if bundle['test'] is not True or bundle['action'] not in self.actions:
            raise PermissionError('simulation test action required')

    def perform(self, key, bundle):
        self.validate(bundle)
        dg = digest(bundle)
        result = {'simulation': True, 'execution_key': key, 'bundle_digest': dg,
                  'result_digest': digest({'account': bundle['account'], 'target': bundle['target'],
                                           'payload': bundle['payload'], 'assets': bundle['assets'],
                                           'amount': bundle['amount']})}
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT * FROM executor_simulated_effects WHERE execution_key=?', (key,)).fetchone()
            if old:
                if old['bundle_digest'] != dg:raise ValueError('simulated service key mismatch')
                return json.loads(old['result'])
            c.execute('INSERT INTO executor_simulated_effects VALUES(?,?,?)', (key, dg, encode(result)))
        return result

    def lookup(self, key):
        with self.runtime.db() as c:
            row = c.execute('SELECT result FROM executor_simulated_effects WHERE execution_key=?', (key,)).fetchone()
            return None if row is None else json.loads(row['result'])

    def verify(self, key, bundle, result):
        # Independently read the simulated-service table rather than trust a response.
        actual = self.lookup(key)
        return (type(result) is dict and actual is not None and actual == result
                and result.get('simulation') is True and result.get('execution_key') == key
                and result.get('bundle_digest') == digest(bundle)
                and result.get('result_digest') == digest({'account': bundle['account'], 'target': bundle['target'],
                    'payload': bundle['payload'], 'assets': bundle['assets'], 'amount': bundle['amount']}))


class SimulationExecutor:
    """One new attempt per approval; unknown attempts are never blindly retried."""
    def __init__(self, approvals, adapter):
        if not isinstance(adapter, SimulationAdapter):raise TypeError('simulation adapter required')
        self.approvals = approvals
        self.runtime = approvals.runtime
        if adapter.runtime.path != self.runtime.path:raise ValueError('same local simulation DB required')
        self.adapter = adapter
        with self.runtime.db() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS action_execution_journal (
 draft_id TEXT PRIMARY KEY, execution_key TEXT UNIQUE NOT NULL,
 actor TEXT NOT NULL, bundle_digest TEXT NOT NULL,
 status TEXT NOT NULL, result TEXT, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS action_execution_events (
 id INTEGER PRIMARY KEY, draft_id TEXT NOT NULL, kind TEXT NOT NULL,
 data TEXT NOT NULL, created TEXT NOT NULL);
''')

    def event(self, c, did, kind, data):
        c.execute('INSERT INTO action_execution_events(draft_id,kind,data,created) VALUES(?,?,?,?)',
                  (did, kind, encode(data), now()))

    @staticmethod
    def view(r):
        return {'draft_id': r['draft_id'], 'status': r['status'],
                'result': json.loads(r['result']) if r['result'] else None,
                'trust': 'SIMULATED_ONLY', 'external_execution_enabled': False,
                'retry_allowed': False}

    def _binding(self, did, p, key, bundle):
        self.approvals.principal(p, 'EXECUTOR');self.approvals.text(key)
        self.approvals.bundle(bundle);self.adapter.validate(bundle)
        with self.runtime.db() as c:
            approved = self.approvals.row(c, did)
            if approved['digest'] != digest(bundle):raise ValueError('approval binding mismatch')
            collision = c.execute('SELECT draft_id FROM action_execution_journal WHERE execution_key=?', (key,)).fetchone()
            if collision and collision['draft_id'] != did:raise ValueError('execution key belongs to another draft')
            old = c.execute('SELECT * FROM action_execution_journal WHERE draft_id=?', (did,)).fetchone()
            if old and (old['actor'] != p.actor or old['execution_key'] != key or old['bundle_digest'] != digest(bundle)):
                raise PermissionError('execution binding mismatch')
            return old

    def execute(self, did, p, key, bundle, current_inputs):
        old = self._binding(did, p, key, bundle)
        if old:return self.view(old)  # replay never calls adapter.perform
        reservation = self.approvals.claim(did, p, key, bundle, current_inputs)
        if reservation['status'] != 'RESERVED':
            return {'draft_id': did, 'status': reservation['status'], 'retry_allowed': False,
                    'trust': 'SIMULATED_ONLY', 'external_execution_enabled': False}
        if not reservation['new_reservation']:
            # Crash gap: approval reserved but execution journal not written.
            # No evidence that perform was absent; reconciliation only.
            with self.runtime.db() as c:
                old = c.execute('SELECT * FROM action_execution_journal WHERE draft_id=?', (did,)).fetchone()
            if old:return self.view(old)
            return {'draft_id': did, 'status': 'UNKNOWN', 'reason': 'RESERVED_WITHOUT_JOURNAL',
                    'retry_allowed': False, 'trust': 'SIMULATED_ONLY', 'external_execution_enabled': False}
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT * FROM action_execution_journal WHERE draft_id=?', (did,)).fetchone()
            if old:return self.view(old)
            c.execute('INSERT INTO action_execution_journal VALUES(?,?,?,?,?,NULL,?)',
                      (did, key, p.actor, digest(bundle), 'UNKNOWN', now()))
            self.event(c, did, 'ATTEMPT_STARTED', {'actor': p.actor, 'execution_key': key})
        # Durable UNKNOWN is written before touching the fake service.
        # Any exception leaves UNKNOWN; it cannot grant another attempt.
        try:
            result = self.adapter.perform(key, bundle)
            if not self.adapter.verify(key, bundle, result):return self._unknown(did, 'READBACK_MISMATCH')
            return self._verified(did, result, 'SIMULATION_VERIFIED')
        except Exception:
            # Do not leak adapter error text, which can contain credentials/content.
            return self._unknown(did, 'ADAPTER_OR_JOURNAL_ERROR')

    def _unknown(self, did, reason):
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM action_execution_journal WHERE draft_id=?', (did,)).fetchone()
            if row['status'] != 'SIMULATION_VERIFIED':self.event(c, did, 'OUTCOME_UNKNOWN', {'reason': reason})
            return self.view(row)

    def _verified(self, did, result, kind):
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM action_execution_journal WHERE draft_id=?', (did,)).fetchone()
            if row['status'] == 'SIMULATION_VERIFIED':return self.view(row)
            c.execute("UPDATE action_execution_journal SET status='SIMULATION_VERIFIED',result=? WHERE draft_id=?", (encode(result), did))
            self.event(c, did, kind, {'result_digest': digest(result)})
            return self.view(c.execute('SELECT * FROM action_execution_journal WHERE draft_id=?', (did,)).fetchone())

    def reconcile(self, did, p, key, bundle):
        old = self._binding(did, p, key, bundle)
        with self.runtime.db() as c:
            r = self.approvals.row(c, did)
            if r['status'] != 'RESERVED' or r['claim_key'] != key or r['claimant'] != p.actor:
                raise PermissionError('matching reserved action required')
        if old and old['status'] == 'SIMULATION_VERIFIED':return self.view(old)
        if old is None:
            with self.runtime.db() as c:
                c.execute('BEGIN IMMEDIATE')
                c.execute('INSERT OR IGNORE INTO action_execution_journal VALUES(?,?,?,?,?,NULL,?)',
                          (did, key, p.actor, digest(bundle), 'UNKNOWN', now()))
                self.event(c, did, 'RECOVERY_STARTED', {'actor': p.actor})
        try:
            result = self.adapter.lookup(key)
            if result is None:return self._unknown(did, 'NO_RESULT_FOUND_NO_RETRY')
            if not self.adapter.verify(key, bundle, result):return self._unknown(did, 'READBACK_MISMATCH')
            return self._verified(did, result, 'RECONCILED_SIMULATION_VERIFIED')
        except Exception:
            return self._unknown(did, 'RECONCILIATION_OR_JOURNAL_ERROR')

    def inspect(self, did, p):
        self.approvals.principal(p, 'APPROVER')
        with self.runtime.db() as c:
            self.approvals.row(c, did)
            row = c.execute('SELECT * FROM action_execution_journal WHERE draft_id=?', (did,)).fetchone()
            events = [dict(e, data=json.loads(e['data'])) for e in c.execute(
                'SELECT id,kind,data,created FROM action_execution_events WHERE draft_id=? ORDER BY id', (did,))]
            return {'execution': self.view(row) if row else None, 'history': events,
                    'external_execution_enabled': False}
