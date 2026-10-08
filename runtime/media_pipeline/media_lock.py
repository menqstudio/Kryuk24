"""One operation of the media pipeline at a time, across processes.

Intake, processing, submit, clean-up and rollback each change files and database rows in several steps. Two of them
running at once could see each other's half-done work (review of 08.10.2026: a repair removing a file another intake
had just registered; a rollback archiving the history while an intake was adding to it). They take this lock for
their whole run. It is a lock of the operating system on one file in the media folder, so it holds between processes
and is released by the system when a process dies.
"""
import os
import time
from pathlib import Path


class PipelineLock:
    def __init__(self, media_root, wait=30.0):
        self.path = Path(media_root) / '.pipeline.lock'
        self.wait = wait
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.file = open(self.path, 'a+b')
        deadline = time.monotonic() + self.wait
        while True:
            try:
                if os.name == 'nt':
                    import msvcrt
                    self.file.seek(0)
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() >= deadline:
                    self.file.close()
                    self.file = None
                    raise TimeoutError('another media pipeline operation holds the lock; nothing was changed') from None
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            if os.name == 'nt':
                import msvcrt
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        finally:
            self.file.close()
            self.file = None
        return False
