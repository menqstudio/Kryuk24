"""Internal dispatch service. Caller supplies a trusted, authenticated principal.

No HTTP routes, production migration, sending or payment execution. Money is
integer kopecks. Existing unmanaged Runtime orders remain untouched.
"""
import hashlib
import json
from dataclasses import dataclass
from runtime import Runtime, encode, now


@dataclass(frozen=True)
class Principal:
    actor: str
    role: str


class OrderFlow:
    def __init__(self, runtime: Runtime):
        self.runtime = runtime
        with runtime.db() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS dispatch_orders (
 order_id TEXT PRIMARY KEY REFERENCES orders(id), state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dispatch_commands (
 order_id TEXT NOT NULL, command_key TEXT NOT NULL, digest TEXT NOT NULL,
 result TEXT NOT NULL, PRIMARY KEY(order_id,command_key));
CREATE TRIGGER IF NOT EXISTS dispatch_guard_status
BEFORE UPDATE OF status,revision ON orders
WHEN EXISTS (SELECT 1 FROM dispatch_orders WHERE order_id=OLD.id)
 AND NOT EXISTS (SELECT 1 FROM dispatch_write_guard WHERE order_id=OLD.id)
BEGIN SELECT RAISE(ABORT,'managed order requires OrderFlow'); END;
CREATE TABLE IF NOT EXISTS dispatch_write_guard (order_id TEXT PRIMARY KEY);
''')

    @staticmethod
    def text(value, name):
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError(name + ' must be nonempty text (max 2000)')
        return value

    @staticmethod
    def money(value):
        if type(value) is not int or not 0 < value <= 999999999:
            raise ValueError('amount must be positive integer kopecks')
        return value

    def _row(self, c, oid):
        row = c.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
        if not row:
            raise LookupError('order not found')
        return row

    def adopt(self, oid, principal, revision):
        """Explicitly enrol only a NEW order. No historical state is guessed."""
        self.text(principal.actor, 'actor')
        if principal.role != 'DISPATCHER':
            raise PermissionError('dispatcher required')
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._row(c, oid)
            old = c.execute('SELECT state FROM dispatch_orders WHERE order_id=?', (oid,)).fetchone()
            if old:
                state = json.loads(old['state'])
                if state['owner'] != principal.actor:
                    raise PermissionError('another dispatcher owns this order')
                return self._view(row, state)
            if row['status'] != 'NEW' or type(revision) is not int or revision != row['revision']:
                raise ValueError('only current NEW order can be enrolled')
            test = json.loads(row['data']).get('test')
            if type(test) is not bool:
                raise ValueError('explicit test boolean required')
            state = dict(owner=principal.actor, test=test, price_version=0,
                         price=None, confirmed_version=None, driver=None,
                         paid=0, commission_settlement=None, job_verified=False,
                         feedback=None, issue=None, eta=None, call=None)
            c.execute('INSERT INTO dispatch_orders VALUES(?,?)', (oid, encode(state)))
            self.runtime.event(c, oid, 'DISPATCH_ENROLLED', {'actor': principal.actor, 'test': test})
            return self._view(row, state)

    @staticmethod
    def due(state):
        # 20% of the dispatcher-recorded customer-confirmed amount, rounded half-up.
        return (state['price'] + 2) // 5 if state['confirmed_version'] == state['price_version'] and state['price'] else None

    def _view(self, row, state):
        return {'id': row['id'], 'status': row['status'], 'revision': row['revision'],
                **state, 'commission_due': self.due(state),
                'closure': self.closure(row['status'], state),
                'sending_enabled': False, 'verification': 'TEST_ONLY' if state['test'] else 'DISPATCHER_ATTESTED'}

    @staticmethod
    def closure(status, state):
        """Deterministic checklist; does not grant permission or mutate anything."""
        checks = {
            'customer_price_confirmed': state['price'] is not None and state['confirmed_version'] == state['price_version'],
            'job_verified': state['job_verified'],
            'payment_confirmed': status in ('PAYMENT_CONFIRMED', 'CLOSED') and state['paid'] == state['price'],
            'commission_settled': state['commission_settlement'] is not None,
            'feedback_recorded': state['feedback'] is not None,
            'no_open_issue': state['issue'] is None,
        }
        missing = [name for name, passed in checks.items() if not passed]
        return {'checks': checks, 'missing': missing, 'can_close': status == 'PAYMENT_CONFIRMED' and not missing,
                'closed': status == 'CLOSED'}

    def history(self, oid):
        """Internal private audit view. HTTP adapters must enforce read access."""
        with self.runtime.db() as c:
            self._row(c, oid)
            rows = c.execute('SELECT id,kind,data,created FROM events WHERE order_id=? ORDER BY id', (oid,)).fetchall()
            return [dict(row, data=json.loads(row['data'])) for row in rows]

    def summary(self, test=False):
        """Cumulative enrolled-order counts. No fabricated revenue/profit/attribution."""
        if type(test) is not bool:
            raise ValueError('test filter must be boolean')
        with self.runtime.db() as c:
            c.execute('BEGIN')  # one consistent snapshot of status and dispatch projection
            rows = c.execute('SELECT o.status,d.state FROM orders o JOIN dispatch_orders d ON o.id=d.order_id').fetchall()
            legacy = c.execute('SELECT COUNT(*) FROM orders WHERE id NOT IN (SELECT order_id FROM dispatch_orders)').fetchone()[0]
        states = [(row['status'], json.loads(row['state'])) for row in rows]
        states = [(status, state) for status, state in states if state['test'] is test]
        paid = [(status, state) for status, state in states if status in ('PAYMENT_CONFIRMED', 'CLOSED')]
        due = sum(self.due(state) for _, state in paid)
        settled = sum(state['commission_settlement']['amount'] for _, state in paid if state['commission_settlement'])
        return {'test': test, 'scope': 'ENROLLED_ORDERS_CUMULATIVE', 'orders': len(states),
                'by_status': {status: sum(current == status for current, _ in states) for status in sorted({x[0] for x in states})},
                'paid_orders': len(paid), 'closed_orders': sum(status == 'CLOSED' for status, _ in states),
                'customer_payments_attested_kopecks': sum(state['paid'] for _, state in paid),
                'commission_due_on_paid_kopecks': due, 'commission_settled_kopecks': settled,
                'commission_outstanding_kopecks': due - settled, 'unmanaged_orders_excluded': legacy,
                'profit': 'UNKNOWN', 'cost': 'UNKNOWN', 'source_attribution': 'UNKNOWN',
                'trust': 'TEST_ONLY' if test else 'DISPATCHER_ATTESTED', 'sending_enabled': False}

    def get(self, oid):
        with self.runtime.db() as c:
            row = self._row(c, oid)
            saved = c.execute('SELECT state FROM dispatch_orders WHERE order_id=?', (oid,)).fetchone()
            if not saved:
                raise ValueError('unmanaged order')
            return self._view(row, json.loads(saved['state']))

    def command(self, oid, principal, key, revision, action, payload):
        self.text(principal.actor, 'actor')
        self.text(key, 'command key')
        if type(revision) is not int or not isinstance(payload, dict):
            raise ValueError('integer revision and payload object required')
        digest = hashlib.sha256(encode([principal.actor, principal.role, revision, action, payload]).encode()).hexdigest()
        with self.runtime.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._row(c, oid)
            saved = c.execute('SELECT state FROM dispatch_orders WHERE order_id=?', (oid,)).fetchone()
            if not saved:
                raise ValueError('unmanaged order')
            state = json.loads(saved['state'])
            if principal.role not in ('DISPATCHER', 'PARTNER'):
                raise PermissionError('unsupported role')
            if principal.role == 'DISPATCHER' and principal.actor != state['owner']:
                raise PermissionError('order owner required')
            if principal.role == 'PARTNER' and (principal.actor != state['driver'] or action != 'PARTNER_REPORT'):
                raise PermissionError('assigned partner may only report')
            old = c.execute('SELECT * FROM dispatch_commands WHERE order_id=? AND command_key=?', (oid, key)).fetchone()
            if old:
                if old['digest'] != digest:
                    raise ValueError('command key reused with different input')
                return json.loads(old['result'])
            if row['revision'] != revision:
                raise ValueError('stale revision')
            if row['status'] == 'CLOSED':
                raise ValueError('closed order is immutable')
            status = self._apply(state, row['status'], action, payload)
            c.execute('INSERT INTO dispatch_write_guard VALUES(?)', (oid,))
            c.execute('UPDATE orders SET status=?,revision=revision+1 WHERE id=?', (status, oid))
            c.execute('DELETE FROM dispatch_write_guard WHERE order_id=?', (oid,))
            c.execute('UPDATE dispatch_orders SET state=? WHERE order_id=?', (encode(state), oid))
            trust = 'PARTNER_REPORTED' if principal.role == 'PARTNER' else 'DISPATCHER_ATTESTED'
            if state['test']:
                trust = 'TEST_ONLY'
            self.runtime.event(c, oid, 'DISPATCH_' + action,
                               {'actor': principal.actor, 'role': principal.role, 'trust': trust,
                                'payload': payload, 'revision': revision + 1})
            result = self._view(self._row(c, oid), state)
            c.execute('INSERT INTO dispatch_commands VALUES(?,?,?,?)', (oid, key, digest, encode(result)))
            return result

    def _apply(self, s, status, action, p):
        fields = {
            'QUALIFY': {'evidence'}, 'QUOTE': {'amount','terms','evidence'},
            'CONFIRM_PRICE': {'price_version','evidence'},
            'ASSIGN': {'driver','acceptance'}, 'PROGRESS': {'status','evidence'},
            'PARTNER_REPORT': {'kind','evidence','amount'},
            'REPRICE': {'amount','terms','evidence','customer_confirmation'},
            'VERIFY_JOB': {'evidence'}, 'VERIFY_PAYMENT': {'amount','price_version','evidence'},
            'SETTLE_COMMISSION': {'amount','price_version','evidence'},
            'FEEDBACK': {'state','evidence'}, 'OPEN_ISSUE': {'evidence'},
            'RESOLVE_ISSUE': {'evidence'}, 'ETA': {'time','evidence'},
            'CALL_STATUS': {'state','evidence'}, 'CLOSE': {'evidence'}}
        if action not in fields or set(p) != fields[action]:
            raise ValueError('unknown action or invalid fields')
        self.text(p['evidence'] if 'evidence' in p else p['acceptance'], 'evidence')
        if action == 'QUALIFY':
            if status != 'NEW': raise ValueError('NEW required')
            return 'QUALIFIED'
        if action == 'QUOTE':
            if status != 'QUALIFIED': raise ValueError('QUALIFIED required')
            s['price'] = self.money(p['amount']); self.text(p['terms'], 'terms')
            s['price_version'] += 1
            return 'PRICE_QUOTED'
        if action == 'CONFIRM_PRICE':
            if status != 'PRICE_QUOTED' or type(p['price_version']) is not int or p['price_version'] != s['price_version']:
                raise ValueError('current quote required')
            s['confirmed_version'] = s['price_version']
            return 'CUSTOMER_CONFIRMED'
        if action == 'ASSIGN':
            if status != 'CUSTOMER_CONFIRMED': raise ValueError('customer-confirmed price required')
            s['driver'] = self.text(p['driver'], 'driver')
            return 'DRIVER_ASSIGNED'
        if action == 'PROGRESS':
            chain = {'DRIVER_ASSIGNED':'EN_ROUTE','EN_ROUTE':'ARRIVED','ARRIVED':'LOADED',
                     'LOADED':'TRANSPORTING','TRANSPORTING':'DELIVERED'}
            if chain.get(status) != p['status']: raise ValueError('invalid operational transition')
            return p['status']
        if action == 'PARTNER_REPORT':
            if p['kind'] not in ('JOB_DONE','PAYMENT','PRICE'): raise ValueError('invalid report kind')
            if p['amount'] is not None: self.money(p['amount'])
            if p['kind'] in ('PAYMENT','PRICE') and p['amount'] is None: raise ValueError('amount required')
            return status  # Immutable event only; no verified projection or price changes.
        if action == 'REPRICE':
            if status in ('NEW','QUALIFIED','PRICE_QUOTED','PAYMENT_CONFIRMED') or s['paid'] or s['commission_settlement']:
                raise ValueError('repricing requires confirmed, unsettled order')
            self.text(p['terms'], 'terms'); self.text(p['customer_confirmation'], 'customer confirmation')
            s['price'] = self.money(p['amount']); s['price_version'] += 1
            s['confirmed_version'] = s['price_version']
            return status
        if action == 'VERIFY_JOB':
            if status != 'DELIVERED': raise ValueError('DELIVERED required')
            s['job_verified'] = True
        elif action == 'VERIFY_PAYMENT':
            if status != 'DELIVERED' or not s['job_verified']: raise ValueError('verified delivered job required')
            if type(p['price_version']) is not int or p['price_version'] != s['confirmed_version']: raise ValueError('current price required')
            amount = self.money(p['amount'])
            if amount != s['price']: raise ValueError('payment must match confirmed price')
            s['paid'] = amount
            return 'PAYMENT_CONFIRMED'
        elif action == 'SETTLE_COMMISSION':
            if status != 'PAYMENT_CONFIRMED' or type(p['price_version']) is not int or p['price_version'] != s['confirmed_version']:
                raise ValueError('current paid price required')
            if type(p['amount']) is not int or p['amount'] != self.due(s): raise ValueError('commission must match 20% due')
            if s['commission_settlement']: raise ValueError('commission already settled')
            s['commission_settlement'] = p
        elif action == 'FEEDBACK':
            if p['state'] not in ('REQUESTED','RECEIVED','DECLINED'): raise ValueError('invalid feedback state')
            s['feedback'] = p
        elif action == 'OPEN_ISSUE':
            if s['issue']: raise ValueError('issue already open')
            s['issue'] = p
        elif action == 'RESOLVE_ISSUE':
            if not s['issue']: raise ValueError('no open issue')
            s['issue'] = None
        elif action == 'ETA':
            from datetime import datetime
            try: parsed = datetime.fromisoformat(p['time'])
            except (TypeError, ValueError): raise ValueError('ISO time required')
            if parsed.tzinfo is None: raise ValueError('ETA timezone required')
            s['eta'] = p
        elif action == 'CALL_STATUS':
            if p['state'] not in ('NOT_CALLED','NO_ANSWER','REACHED'): raise ValueError('invalid call state')
            s['call'] = p
        elif action == 'CLOSE':
            if status != 'PAYMENT_CONFIRMED' or not s['job_verified'] or not s['commission_settlement'] or not s['feedback'] or s['issue']:
                raise ValueError('closure requires verified job/payment, settled commission, feedback state and no open issue')
            return 'CLOSED'
        return status
