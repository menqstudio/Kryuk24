"""Stores the collector's read credentials on the server. Run as root; the secrets arrive on standard input only.

  <json on stdin> | sudo python3 reader_provision.py --dir /etc/kryuk24-api-read --group kryuk-api-read

Standard input: one JSON object with exactly these keys: yandex_read_token, beget_login, beget_api_password.
Anything else (an actions token, a mail credential) is refused: such a credential must not be on the collector's side.
Result: the folder (0750, root:<group>) with two files (0640, root:<group>):
  beget-read.json   beget_login, beget_api_password
  yandex-read.json  yandex_read_token
A secret is never taken from the command line, never printed and never logged. Typing it at a terminal is refused.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

FILES = {'beget-read.json': ('beget_login', 'beget_api_password'), 'yandex-read.json': ('yandex_read_token',)}
KEYS = {key for keys in FILES.values() for key in keys}


def provision(data, directory, group=None):
    if not isinstance(data, dict) or set(data) != KEYS:
        extra = sorted(set(data) - KEYS) if isinstance(data, dict) else []
        raise ValueError('exactly these keys are required: %s%s' % (', '.join(sorted(KEYS)), '; not allowed here: ' + ', '.join(extra) if extra else ''))
    if any(not isinstance(v, str) or not v or len(v) > 4096 or v != v.strip() or any(c.isspace() for c in v) for v in data.values()):
        raise ValueError('every value must be one non-empty piece of text without spaces')
    directory = Path(directory)
    directory.mkdir(mode=0o750, exist_ok=True)
    owned = group is not None and hasattr(os, 'chown')
    if owned:
        shutil.chown(directory, 'root', group)
        os.chmod(directory, 0o750)
    for name, keys in FILES.items():
        temporary = directory / (name + '.new')
        if temporary.exists():
            temporary.unlink()
        handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
        with os.fdopen(handle, 'w', encoding='utf-8') as f:
            json.dump({key: data[key] for key in keys}, f)
        if owned:
            shutil.chown(temporary, 'root', group)
            os.chmod(temporary, 0o640)
        os.replace(temporary, directory / name)
    return sorted(FILES)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', required=True)
    parser.add_argument('--group')
    args = parser.parse_args()
    if sys.stdin.isatty():
        print('REFUSED: the secrets must come through a pipe, not be typed here')
        return 2
    try:
        written = provision(json.loads(sys.stdin.buffer.read(65536).decode('utf-8-sig')), args.dir, args.group)
    except (ValueError, OSError, LookupError) as reason:
        print('REFUSED: %s' % (reason if isinstance(reason, ValueError) and not isinstance(reason, json.JSONDecodeError) else type(reason).__name__))
        return 2
    print('written: %s' % ', '.join(written))
    return 0


if __name__ == '__main__':
    sys.exit(main())
