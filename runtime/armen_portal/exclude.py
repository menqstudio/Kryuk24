"""Mark rows of the portal as somebody's test, so that they are not counted as Armen's.

    python exclude.py --db DB --photos FOLDER --before 2026-10-08T10:43:00+00:00 --reason "..." --marked-by GEV \
        --expect-photos 1 --expect-answers 3 [--apply]

Every answer and photo saved up to the given moment is listed (kind, id, time; no answer text, no picture) and,
with --apply, marked in armen_excluded. Without --apply nothing is written. The expected counts must match what is
found, otherwise nothing is written either: the mark is for rows somebody has looked at, not for whatever is there.
Nothing is deleted: rows and files stay. A marked row is in no state, no count and no preview of the portal, and the
media intake does not take a marked photo in.
"""
import argparse
from datetime import datetime

from portal import Store

p = argparse.ArgumentParser()
for name in ('db', 'photos', 'before', 'reason', 'marked-by'):
    p.add_argument('--' + name, required=True)
p.add_argument('--expect-photos', type=int, required=True)
p.add_argument('--expect-answers', type=int, required=True)
p.add_argument('--apply', action='store_true')
a = p.parse_args()
limit = datetime.fromisoformat(a.before)
if limit.tzinfo is None:
    raise SystemExit('STOP: --before needs a time zone')
store = Store(a.db, a.photos)
with store.db() as c:
    found = [(kind, r['id'], r['actor'], r['created']) for kind, table in (('answer', 'armen_answers'), ('photo', 'armen_photos'))
             for r in c.execute('SELECT id,actor,created FROM ' + table + ' ORDER BY rowid') if datetime.fromisoformat(r['created']) <= limit]
    already = {(r['kind'], r['id']) for r in c.execute('SELECT kind,id FROM armen_excluded')}
for kind, ident, actor, created in found:
    print('%-6s %s… actor %s saved %s%s' % (kind, ident[:8], actor, created, ' (already marked)' if (kind, ident) in already else ''))
counts = (sum(k == 'photo' for k, *_ in found), sum(k == 'answer' for k, *_ in found))
print('found up to %s: %d photos, %d answers; expected %d and %d' % (a.before, *counts, a.expect_photos, a.expect_answers))
if counts != (a.expect_photos, a.expect_answers):
    raise SystemExit('STOP: not what was expected; nothing was marked')
if not a.apply:
    raise SystemExit('dry run: nothing was marked (add --apply)')
for kind, ident, _, _ in found:
    store.exclude(kind, ident, a.reason, a.marked_by)
state = store.state('armen', owner=True)
with store.db() as c:
    print('marked now: %d rows in armen_excluded; rows kept: %d photos, %d answers' % tuple(
        c.execute(q).fetchone()[0] for q in ('SELECT count(*) FROM armen_excluded', 'SELECT count(*) FROM armen_photos', 'SELECT count(*) FROM armen_answers')))
print('what the portal now shows for everybody: %d photos, %d answers of today' % (len(state['photos']), len(state['answers'])))
