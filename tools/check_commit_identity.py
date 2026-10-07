"""Every commit in a range must have the one accepted author and committer, and no co-author or tool trailers.

    python tools/check_commit_identity.py <range or revision> "<name>" "<email>"

    python tools/check_commit_identity.py HEAD "MenQ" "…@users.noreply.github.com"        all commits reachable from HEAD
    python tools/check_commit_identity.py origin/main..HEAD "MenQ" "…"                    only the new ones

Exit 0 when every commit passes. Used by CI and by hand before a push.
"""
import re
import subprocess
import sys

FORBIDDEN = re.compile(r"(?im)^\s*(co-authored-by|generated[ -]with|signed-off-by:\s*claude)\b|noreply@anthropic\.com|claude\.com/claude-code")


def main():
    revisions, name, email = sys.argv[1], sys.argv[2], sys.argv[3]
    out = subprocess.run(["git", "log", "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e", revisions],
                         capture_output=True, check=True).stdout.decode("utf-8", "replace")
    bad, count = [], 0
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        count += 1
        sha, an, ae, cn, ce, body = record.split("\x1f", 5)
        problems = []
        if (an, ae) != (name, email):
            problems.append("author is not the accepted identity")
        if (cn, ce) != (name, email):
            problems.append("committer is not the accepted identity")
        if FORBIDDEN.search(body):
            problems.append("message carries a co-author or tool attribution line")
        if problems:
            bad.append("%s  %s" % (sha[:10], "; ".join(problems)))
    print("commits checked: %d, not accepted: %d" % (count, len(bad)))
    for line in bad:
        print("  " + line)
    return 1 if bad or not count else 0


if __name__ == "__main__":
    sys.exit(main())
