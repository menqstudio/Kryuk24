"""Inventory of the project folder: every file on disk with size, git state, full sha256, class and destination.

    python tools/make_inventory.py        writes docs/inventory/FILES.csv and prints the totals

Files under _private/ are listed without their names and are not read. .git, tools/.venv and caches are left out.
"""
import collections
import csv
import hashlib
import re
import subprocess
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
RULES = [   # first match wins: (pattern on the posix path, class, destination)
    (r'^_private/', 'private material', 'local only, protected backup'),
    (r'^_drive_staging/04_Photo/00_real_source/', 'media: originals (plates and people visible)', 'Drive, restricted access'),
    (r'^_drive_staging/', 'media, renders, mockups, archive', 'Drive'),
    (r'(^|/)\.mcp\.json$|settings\.local\.json$', 'machine-specific configuration', 'local only'),
    (r'\.zip$', 'generated package', 'local only (Desktop\\ZIP or Drive)'),
    (r'^site/', 'canonical code: the live site', 'GitHub'),
    (r'^runtime/api_reader/(evidence|fixtures)/', 'test fixture or evidence', 'GitHub'),
    (r'^runtime/api_reader/', 'canonical code: API reader (installed)', 'GitHub'),
    (r'^runtime/server/', 'canonical code: as installed on the VPS', 'GitHub'),
    (r'^runtime/server_patches/', 'canonical code: copies of server patches', 'GitHub'),
    (r'^runtime/wip/', 'work in progress: proxy, gate, trial', 'GitHub, marked WIP'),
    (r'^runtime/received/', 'reference: packages as received', 'GitHub'),
    (r'^tools/tests/', 'tests: site checks', 'GitHub'),
    (r'^tools/', 'tools: generators and checks', 'GitHub'),
    (r'^research/', 'accepted source: prices, launch package', 'GitHub'),
    (r'^brand/', 'brand assets: sources and renders used by the tools', 'GitHub'),
    (r'^photo/', 'media: processed photos for publication', 'GitHub'),
    (r'^offers/', 'offers and kits for the owner', 'GitHub'),
    (r'^reports/', 'report to the owner and its sources', 'GitHub'),
    (r'^docs/', 'documentation', 'GitHub'),
    (r'^(README\.md|\.gitignore|\.mcp\.json\.example)$|^\.github/|^\.claude/', 'entry point, configuration, CI, instructions', 'GitHub'),
    (r'.', 'unclassified', 'look'),
]


def git(*args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True).stdout.decode('utf-8', 'replace')


def main():
    tracked = set(n for n in git('ls-files', '-z').split('\0') if n)
    rows = []
    for path in sorted(repo.rglob('*')):
        rel = path.relative_to(repo).as_posix()
        if not path.is_file() or rel.startswith('.git/') or '/.venv/' in '/' + rel or '__pycache__/' in rel or '/_shots/' in '/' + rel:
            continue
        private = rel.startswith('_private/')
        kind, where = next((k, w) for pattern, k, w in RULES if re.search(pattern, rel))
        rows.append({'path': '_private/<file %d>%s' % (len(rows), path.suffix) if private else rel, 'bytes': path.stat().st_size,
                     'git': 'tracked' if rel in tracked else 'not in git',
                     'sha256': '' if private else hashlib.sha256(path.read_bytes()).hexdigest(), 'class': kind, 'destination': where})
    out = repo / 'docs' / 'inventory'
    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'FILES.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    total = sum(r['bytes'] for r in rows)
    print('rows %d | tracked %d (%.1f MB) | not in git %d | all %.1f MB' % (
        len(rows), sum(r['git'] == 'tracked' for r in rows), sum(r['bytes'] for r in rows if r['git'] == 'tracked') / 1e6,
        sum(r['git'] != 'tracked' for r in rows), total / 1e6))
    for label in ('destination', 'class'):
        by = collections.defaultdict(lambda: [0, 0])
        for r in rows:
            by[r[label]][0] += 1
            by[r[label]][1] += r['bytes']
        print('== by', label)
        for key, (n, size) in sorted(by.items()):
            print('  %-58s %4d files %7.1f MB' % (key, n, size / 1e6))


if __name__ == '__main__':
    main()
