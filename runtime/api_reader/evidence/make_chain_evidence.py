"""How the chain evidence is made: real read-only API readings through the patched queue code into a THROWAWAY database.

  python evidence/make_chain_evidence.py <out.json>        (on the owner's Windows account; read token only)

It copies fixtures/server_base into a temp folder, applies install_patch there, plans today in a new empty
database, then runs: dry-run -> write run (claim, observe) -> second write run -> second dry-run.
The server and its database are not contacted. Nothing secret is written: the result is checked before saving.
"""
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import install_patch                                       # noqa: E402
import bro_api_reader as R                                 # noqa: E402

out = Path(sys.argv[1])
if out.exists():
    sys.exit('refused: %s exists' % out)
work = Path(tempfile.mkdtemp(prefix='kryuk-chain-'))
code = work / 'code'
code.mkdir()
for path in (HERE / 'fixtures' / 'server_base').glob('*.py'):
    shutil.copy(path, code / path.name)
applied = install_patch.apply(code)
sys.path.insert(0, str(code))
import ops_api                                             # noqa: E402  the copies the patch installed
import ops_work                                            # noqa: E402

db = work / 'runtime.sqlite'
ops = ops_work.Operations(db)
day = ops_api.today()
ops.plan(day)
secrets = R.windows_user_store()


def counts():
    with sqlite3.connect(db) as c:
        return {'observations': c.execute('SELECT count(*) FROM ops_observations').fetchone()[0],
                'events': c.execute('SELECT count(*) FROM ops_events').fetchone()[0],
                'revisions': c.execute('SELECT sum(revision) FROM ops_tasks').fetchone()[0]}


def api_tasks():
    return [{'job': t['job'], 'kind': t['kind'], 'status': t['status'], 'revision': t['revision'], 'worker': t['worker'],
             'observations': [{'trust': o['trust'], 'source': o['source'], 'actor': o['actor'][:9] + '<32 hex>', 'observed_at': o['observed_at'],
                               'summary': json.loads(o['summary'])} for o in t['observations']]}
            for t in ops.report(day)['tasks'] if t['job'] in R.API_JOBS]


report = {'what': 'real read-only API readings through dry-run -> claim -> lease -> observe -> second run into a THROWAWAY '
                  'database on Windows; the server and its database were not contacted',
          'collector_version': R.VERSION, 'started': R.utc_now(), 'day': day,
          'patched_files_sha256': {name: applied[name] for name in install_patch.BASE},
          'kinds_planned': {t['job']: t['kind'] for t in ops.report(day)['tasks']}}
report['counts'] = {'before': counts()}
report['dry_run'] = ops_api.dry_run(db, day, secrets)
report['counts']['after_dry_run'] = counts()
report['write_run'] = ops_api.run_api(ops, day, secrets)
report['counts']['after_write'] = counts()
report['tasks_after_write'] = api_tasks()
report['second_write_run'] = ops_api.run_api(ops, day, secrets)
report['counts']['after_second_write'] = counts()
report['second_dry_run'] = ops_api.dry_run(db, day, secrets)
report['counts']['after_second_dry_run'] = counts()
report['other_tasks_untouched'] = all(t['status'] == 'PENDING' and not t['observations'] for t in ops.report(day)['tasks'] if t['job'] not in R.API_JOBS)
report['finished'] = R.utc_now()
R.no_secret(secrets, report)                               # raises instead of saving if a secret is anywhere in it
out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8', newline='\n')
shutil.rmtree(work, ignore_errors=True)

c = report['counts']
print('version', R.VERSION, 'day', day)
print('dry-run        :', [(r['job'], r['reading']['status'], r['would_write'], r.get('would_set')) for r in report['dry_run']['results']])
print('write          :', [(r['job'], r['outcome'], r.get('reading')) for r in report['write_run']['results']])
print('second write   :', [(r['job'], r['outcome']) for r in report['second_write_run']['results']])
print('second dry-run :', [(r['job'], r['would_write'], r.get('why')) for r in report['second_dry_run']['results']])
print('counts', c)
print('dry-run wrote nothing:', c['before'] == c['after_dry_run'], '| second run wrote nothing:', c['after_write'] == c['after_second_write'] == c['after_second_dry_run'])
print('other tasks untouched:', report['other_tasks_untouched'])
