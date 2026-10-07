"""Internal role-controlled facade; no authentication server or live actions."""
import copy
import json
from dataclasses import dataclass
from order_flow import Principal
from action_approval import ApprovalPrincipal


@dataclass(frozen=True)
class Identity:
    actor: str
    roles: frozenset


class BusinessService:
    def __init__(self, requests, approvals, executor, owner_actor, inputs_provider):
        if not callable(inputs_provider):raise ValueError('trusted inputs provider required')
        approvals.text(owner_actor)
        if owner_actor != approvals.approver:raise ValueError('owner/approver identity mismatch')
        if requests.runtime.path != approvals.runtime.path or executor.approvals is not approvals:
            raise ValueError('one consistent runtime and approval store required')
        self.requests = requests
        self.orders = requests.flow
        self.approvals = approvals
        self.executor = executor
        self.owner = owner_actor
        self.inputs_provider = inputs_provider
        self.runtime = requests.runtime

    def role(self, identity, role):
        if not isinstance(identity, Identity) or type(identity.roles) is not frozenset:
            raise PermissionError('trusted identity required')
        self.approvals.text(identity.actor)
        if role not in identity.roles:raise PermissionError(role + ' role required')
        if role == 'OWNER' and identity.actor != self.owner:raise PermissionError('configured owner required')

    def receive(self, identity, channel, source_ref, test, evidence, contact=None):
        self.role(identity, 'DISPATCHER')
        return self.requests.receive(Principal(identity.actor,'DISPATCHER'),channel,source_ref,test,evidence,contact)

    def convert(self, identity, rid, revision, **fields):
        self.role(identity,'DISPATCHER')
        return self.requests.convert(rid,Principal(identity.actor,'DISPATCHER'),revision,**fields)

    def dispose(self, identity, rid, revision, outcome, evidence, duplicate_of=None):
        self.role(identity,'DISPATCHER')
        return self.requests.dispose(rid,Principal(identity.actor,'DISPATCHER'),revision,outcome,evidence,duplicate_of)

    def request(self, identity, rid):
        if isinstance(identity,Identity) and 'OWNER' in identity.roles:
            self.role(identity,'OWNER')
            with self.runtime.db() as c:
                row=c.execute('SELECT * FROM business_requests WHERE id=?',(rid,)).fetchone()
                if not row:raise LookupError('request not found')
                return self.requests._view(row)
        self.role(identity,'DISPATCHER')
        return self.requests.get(rid,Principal(identity.actor,'DISPATCHER'))

    def order(self, identity, oid):
        # The order is read internally, but never returned before identity/ownership checks.
        if not isinstance(identity,Identity) or type(identity.roles) is not frozenset:raise PermissionError('trusted identity required')
        self.approvals.text(identity.actor)
        state=self.orders.get(oid)
        if 'OWNER' in identity.roles:
            self.role(identity,'OWNER');return state
        if 'DISPATCHER' in identity.roles and identity.actor==state['owner']:return state
        if 'PARTNER' in identity.roles and identity.actor==state['driver']:
            return {k:state[k] for k in ('id','status','revision','driver','eta','call','test')} | {
                'reporting_only':True,'report_trust':'TEST_ONLY' if state['test'] else 'PARTNER_REPORTED'}
        raise PermissionError('order read denied')

    def order_command(self, identity, oid, key, revision, action, payload):
        self.order(identity,oid)  # enforce read/association first
        # OWNER alone is read-only for order accounting; it grants no dispatcher role.
        if 'DISPATCHER' in identity.roles:
            self.role(identity,'DISPATCHER');role='DISPATCHER'
        elif 'PARTNER' in identity.roles:
            self.role(identity,'PARTNER');role='PARTNER'
        else:raise PermissionError('order write role required')
        self.orders.command(oid,Principal(identity.actor,role),key,revision,action,payload)
        # Return only role-safe projection, never raw financial state to partner.
        return self.order(identity,oid)

    def order_history(self, identity, oid):
        state=self.order(identity,oid)
        if state.get('reporting_only'):raise PermissionError('full audit restricted')
        return self.orders.history(oid)

    def board(self, identity, test=False):
        self.role(identity,'OWNER')
        if type(test) is not bool:raise ValueError('boolean test filter required')
        with self.runtime.db() as c:
            c.execute('BEGIN')
            requests=[self.requests._view(r) for r in c.execute('SELECT * FROM business_requests ORDER BY created,id')
                      if json.loads(r['data'])['test'] is test]
            orders=[self.orders._view(r,json.loads(r['state'])) for r in c.execute(
                'SELECT o.*,d.state FROM orders o JOIN dispatch_orders d ON o.id=d.order_id ORDER BY o.created,o.id')
                    if json.loads(r['state'])['test'] is test]
            legacy=c.execute('SELECT COUNT(*) FROM orders WHERE id NOT IN (SELECT order_id FROM dispatch_orders)').fetchone()[0]
        # Compact cards deliberately omit contact/evidence/address/payload from the board.
        request_cards=[{k:r[k] for k in ('id','owner','status','revision','order_id','created')} |
                       {'channel':r['data']['channel']} for r in requests]
        order_cards=[{k:o[k] for k in ('id','owner','status','revision','closure')} for o in orders]
        return {'test':test,'requests':request_cards,'orders':order_cards,
                'counts':{'requests':len(requests),'managed_orders':len(orders),
                          'closed_orders':sum(o['status']=='CLOSED' for o in orders),
                          'conversions_incomplete':sum(r['status']=='CONVERTING' for r in requests)},
                'unmanaged_orders_excluded_all_test_classes':legacy,
                'profit':'UNKNOWN','external_execution_enabled':False}

    def _inputs(self, bundle):
        # A trusted configured provider reads current state; no caller-input fingerprint.
        self.approvals.bundle(bundle)
        return self.inputs_provider(copy.deepcopy(bundle))

    def proposal(self, identity, key, bundle):
        self.role(identity,'PREPARER')
        # Bind to the provider's snapshot rather than trusting submitted fingerprints.
        current=self._inputs(bundle)
        if current != bundle['inputs']:raise ValueError('proposal inputs already stale')
        return self.approvals.draft(ApprovalPrincipal(identity.actor,'PREPARER'),key,bundle)

    def decide(self, identity, did, expected_digest, decision, evidence):
        self.role(identity,'OWNER')
        p=ApprovalPrincipal(identity.actor,'APPROVER')
        bundle=self.approvals.inspect(did,p)['bundle']
        return self.approvals.decide(did,p,expected_digest,decision,self._inputs(bundle),evidence)

    def revoke(self, identity, did, evidence):
        self.role(identity,'OWNER')
        return self.approvals.revoke(did,ApprovalPrincipal(identity.actor,'APPROVER'),evidence)

    def execute_simulation(self, identity, did, key, bundle):
        self.role(identity,'EXECUTOR')
        return self.executor.execute(did,ApprovalPrincipal(identity.actor,'EXECUTOR'),key,bundle,self._inputs(bundle))

    def reconcile_simulation(self, identity, did, key, bundle):
        self.role(identity,'EXECUTOR')
        return self.executor.reconcile(did,ApprovalPrincipal(identity.actor,'EXECUTOR'),key,bundle)

    def action(self, identity, did):
        self.role(identity,'OWNER')
        p=ApprovalPrincipal(identity.actor,'APPROVER')
        return {'approval':self.approvals.inspect(did,p),'execution':self.executor.inspect(did,p)}
