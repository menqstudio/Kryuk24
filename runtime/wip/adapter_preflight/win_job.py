"""Run a command inside a Windows Job Object so that the whole process tree can be ended (v3).

The target never runs outside the job: a small gate stub is started first, assigned to the job,
and only then released to start the real command, so every descendant is born inside the job.
The job is created with KILL_ON_JOB_CLOSE and without BREAKAWAY_OK.

v2: a cleaned environment is mandatory, the output limit is enforced while the command runs,
and cleanup also happens when starting, assigning, releasing or terminating fails.

v3: an error in the thread that reads the output or feeds the input is never swallowed.
It ends the run and comes back as JobIOError, so the caller cannot mistake it for success.

Standard library only (ctypes). Windows only.
"""
import ctypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
from pathlib import Path

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JobObjectBasicAccountingInformation = 1
JobObjectBasicProcessIdList = 3
JobObjectExtendedLimitInformation = 9
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
TARGET_START_FAILED_EXIT = 96
GATE_TIMEOUT_EXIT = 97

# Names a child may receive. Anything else must be named explicitly by the caller in `extra_env_names`.
BASE_ENV_NAMES = frozenset({'SYSTEMROOT', 'WINDIR', 'PYTHONIOENCODING', 'PYTHONUTF8'})
# Never passed, whatever the caller says.
SECRET_NAME = re.compile(r'TOKEN|SECRET|PASSW|CREDENTIAL|API_?KEY|AUTHORI[SZ]ATION|COOKIE|SESSION_?KEY|PRIVATE_?KEY', re.I)


class OutputLimit(ValueError):
    def __init__(self, result):
        super().__init__('output too large')
        self.result = result


class JobIOError(RuntimeError):
    """The output could not be read or the input could not be delivered. The run is a failure."""

    def __init__(self, result):
        super().__init__('adapter input/output failed: ' + ', '.join(result['io_errors']))
        self.result = result


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ('ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
                                                  'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', wintypes.LARGE_INTEGER), ('PerJobUserTimeLimit', wintypes.LARGE_INTEGER),
                ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD), ('SchedulingClass', wintypes.DWORD)]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION), ('IoInfo', IO_COUNTERS),
                ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]


class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [('TotalUserTime', wintypes.LARGE_INTEGER), ('TotalKernelTime', wintypes.LARGE_INTEGER),
                ('ThisPeriodTotalUserTime', wintypes.LARGE_INTEGER), ('ThisPeriodTotalKernelTime', wintypes.LARGE_INTEGER),
                ('TotalPageFaultCount', wintypes.DWORD), ('TotalProcesses', wintypes.DWORD),
                ('ActiveProcesses', wintypes.DWORD), ('TotalTerminatedProcesses', wintypes.DWORD)]


k32.CreateJobObjectW.restype = wintypes.HANDLE
k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
k32.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
k32.CloseHandle.argtypes = [wintypes.HANDLE]
k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4


def _check(ok, what):
    if not ok:
        raise OSError(ctypes.get_last_error(), what)


def _created(handle):
    """Creation time of the process behind a handle, as Windows keeps it (100 ns units), or None."""
    ft = [wintypes.FILETIME() for _ in range(4)]
    if not k32.GetProcessTimes(handle, *[ctypes.byref(f) for f in ft]):
        return None
    return (ft[0].dwHighDateTime << 32) | ft[0].dwLowDateTime


def created_iso(ticks):
    return (datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=ticks // 10)).isoformat()


def pid_state(pid, born=None):
    """'gone', 'alive' or 'unknown'. With `born` (creation times seen for this pid inside the job) a live process
    created at another time is 'gone': Windows gave the pid of an ended job process to something else. A live process
    whose creation time cannot be read is 'unknown': it cannot be told apart from the job's, so it is never 'gone'."""
    handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return 'gone'
    try:
        code = wintypes.DWORD()
        if not (k32.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value == STILL_ACTIVE):
            return 'gone'
        if not born:
            return 'alive'
        when = _created(handle)
        if when is None:
            return 'unknown'
        return 'alive' if when in born else 'gone'
    finally:
        k32.CloseHandle(handle)


def pid_alive(pid, born=None):
    """Is the process alive? 'unknown' counts as alive: an unreadable creation time never says "no leftover"."""
    return pid_state(pid, born) != 'gone'


def clean_env(env, extra_env_names=()):
    """Validate the environment a child will get. There is no default: the caller must pass it."""
    if not isinstance(env, dict):
        raise ValueError('explicit environment required; the parent environment is never inherited')
    allowed = BASE_ENV_NAMES | {str(n).upper() for n in extra_env_names}
    out = {}
    for name, value in env.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise ValueError('environment must map text to text')
        if SECRET_NAME.search(name):
            raise ValueError('secret-like environment name refused: ' + name)
        if name.upper() not in allowed:
            raise ValueError('environment name outside the allow-list: ' + name)
        out[name] = value
    if 'SYSTEMROOT' not in {n.upper() for n in out}:
        raise ValueError('SystemRoot is required to start a process on Windows')
    return out


class Job:
    def __init__(self):
        self.handle = k32.CreateJobObjectW(None, None)
        _check(self.handle, 'CreateJobObject')
        try:
            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            _check(k32.SetInformationJobObject(self.handle, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)),
                   'SetInformationJobObject')
        except BaseException:
            self.close()
            raise

    def assign(self, process_handle):
        _check(k32.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process_handle))), 'AssignProcessToJobObject')
        inside = wintypes.BOOL()
        _check(k32.IsProcessInJob(wintypes.HANDLE(int(process_handle)), self.handle, ctypes.byref(inside)), 'IsProcessInJob')
        if not inside.value:
            raise OSError('process is not in the job')

    def active(self):
        info = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
        _check(k32.QueryInformationJobObject(self.handle, JobObjectBasicAccountingInformation, ctypes.byref(info), ctypes.sizeof(info), None),
               'QueryInformationJobObject')
        return info.ActiveProcesses

    def pids(self):
        class LIST(ctypes.Structure):
            _fields_ = [('NumberOfAssignedProcesses', wintypes.DWORD), ('NumberOfProcessIdsInList', wintypes.DWORD),
                        ('ProcessIdList', ctypes.c_size_t * 1024)]
        info = LIST()
        _check(k32.QueryInformationJobObject(self.handle, JobObjectBasicProcessIdList, ctypes.byref(info), ctypes.sizeof(info), None),
               'QueryInformationJobObject list')
        return [int(info.ProcessIdList[i]) for i in range(info.NumberOfProcessIdsInList)]

    def born(self, pid):
        """Creation time of `pid`, taken through a handle that Windows confirms is a process of THIS job; else None.
        The confirmation matters: between the list and the handle the pid may already belong to another process."""
        handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            inside = wintypes.BOOL()
            if not k32.IsProcessInJob(handle, self.handle, ctypes.byref(inside)) or not inside.value:
                return None
            return _created(handle)
        finally:
            k32.CloseHandle(handle)

    def terminate(self, wait=5.0):
        """End every process in the job. Returns the number still active after `wait` seconds (0 = clean)."""
        _check(k32.TerminateJobObject(self.handle, 1), 'TerminateJobObject')
        deadline = time.monotonic() + wait
        while self.active() and time.monotonic() < deadline:
            time.sleep(0.05)
        return self.active()

    def close(self):
        if self.handle:
            k32.CloseHandle(self.handle)
            self.handle = None


def _read_block(stream):
    """One block of the command's output. Separate so that tests can make it fail."""
    return stream.read1(4096)


def _write_all(stream, data):
    """Deliver the whole input and close it. Separate so that tests can make it fail."""
    stream.write(data)
    stream.close()


def _release(gate):
    """Let the stub start the real command. Separate so that tests can make it fail."""
    Path(gate).write_bytes(b'1')


def _note(job, seen, born):
    """Add what is in the job now: pids to `seen`, and to `born` every creation time seen for a pid."""
    for pid in job.pids():
        seen.add(pid)
        when = job.born(pid)
        if when:
            born.setdefault(pid, set()).add(when)


def _cleanup(job, process, seen, wait=5.0, born=None):
    """End everything, whatever already failed. Returns (survivors, how, unidentified).

    `unidentified`: pids still alive whose creation time could not be read, so they may or may not be the job's.
    They are counted in `survivors` too: a caller that reads only that number never sees "no leftover"."""
    how = 'job'
    remaining = None
    born = {} if born is None else born
    try:
        _note(job, seen, born)
    except OSError:
        pass
    try:
        remaining = job.terminate(wait)
    except OSError:
        how = 'fallback'
    # Closing the last handle ends the job's processes too (KILL_ON_JOB_CLOSE); also covers a failed terminate.
    job.close()
    if process is not None:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            pass
        seen.add(process.pid)
    deadline = time.monotonic() + wait
    state = {p: pid_state(p, born.get(p)) for p in seen}
    while any(s != 'gone' for s in state.values()) and time.monotonic() < deadline:
        time.sleep(0.05)
        state = {p: pid_state(p, born.get(p)) for p, s in state.items() if s != 'gone'}
    unidentified = sorted(p for p, s in state.items() if s == 'unknown')
    sure = sum(1 for s in state.values() if s == 'alive')
    return max(sure, remaining or 0) + len(unidentified), how, unidentified


def run_in_job(argv, stdin=b'', timeout=300, env=None, cwd=None, max_output=32768, extra_env_names=(), stderr_path=None):
    """Run argv inside a fresh job with a cleaned environment. Never leaves a process of the job running.

    Returns: returncode (None on timeout), stdout, timed_out, survivors, unidentified (pids counted in survivors only
    because their creation time could not be read: not proven to be the job's, not proven otherwise), peak_pids,
    peak_created (for each pid the creation times Windows confirmed inside the job; a pid alone is reused at once),
    cleanup ('job' or 'fallback'), io_errors (always [] in a returned success).
    Raises OutputLimit (with .result) as soon as the command writes more than max_output bytes.
    Raises JobIOError (with .result) when reading the output or delivering the input failed.
    stderr_path: file that receives the command's stderr (trial diagnostics); default is to discard it.
    """
    if not isinstance(argv, list) or not argv or any(not isinstance(a, str) for a in argv) or not Path(argv[0]).is_absolute():
        raise ValueError('absolute executable argv required')
    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise ValueError('timeout 1..600 seconds')
    if type(max_output) is not int or not 1 <= max_output <= 1048576:
        raise ValueError('max_output 1..1048576 bytes')
    env = clean_env(env, extra_env_names)

    private = None
    seen = set()
    born = {}
    process = None
    chunks = []
    overflow = threading.Event()
    io_failed = threading.Event()
    io_errors = []
    threads = []
    timed_out = False
    survivors, how, unidentified = 0, 'job', []
    job = Job()
    errors = None
    try:
        errors = open(stderr_path, 'wb') if stderr_path else None
        private = tempfile.mkdtemp(prefix='bro-job-')
        gate = Path(private) / 'go'
        stub = [sys.executable, '-I', str(Path(__file__).resolve()), '--stub', str(gate)] + argv
        process = subprocess.Popen(stub, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors or subprocess.DEVNULL,
                                   cwd=cwd, env=env, close_fds=True)
        job.assign(process._handle)
        _release(gate)

        def read():
            total = 0
            try:
                while True:
                    block = _read_block(process.stdout)
                    if not block:
                        return
                    total += len(block)
                    if total > max_output:
                        overflow.set()
                        return
                    chunks.append(block)
            except BaseException as error:
                io_errors.append('output reader: ' + type(error).__name__)
                io_failed.set()

        def write():
            try:
                _write_all(process.stdin, stdin)
            except BaseException as error:
                io_errors.append('input writer: ' + type(error).__name__)
                io_failed.set()

        threads = [threading.Thread(target=read, daemon=True), threading.Thread(target=write, daemon=True)]
        for t in threads:
            t.start()
        deadline = time.monotonic() + timeout
        while True:
            try:
                _note(job, seen, born)
            except OSError:
                pass
            if overflow.is_set() or io_failed.is_set() or process.poll() is not None:
                break
            if time.monotonic() >= deadline:
                timed_out = True
                break
            time.sleep(0.05)
    finally:
        survivors, how, unidentified = _cleanup(job, process, seen, born=born)
        for t in threads:
            t.join(timeout=5)
            if t.is_alive():
                io_errors.append('input/output thread did not finish')
        for stream in (getattr(process, 'stdin', None), getattr(process, 'stdout', None)):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        if errors is not None:
            errors.close()
        if private:
            shutil.rmtree(private, ignore_errors=True)

    result = {'returncode': None if (timed_out or overflow.is_set()) else process.returncode, 'stdout': b''.join(chunks),
              'timed_out': timed_out, 'survivors': survivors, 'unidentified': unidentified, 'peak_pids': sorted(seen), 'cleanup': how,
              'peak_created': {str(pid): sorted(created_iso(t) for t in times) for pid, times in sorted(born.items())},
              'io_errors': list(io_errors)}
    if overflow.is_set():
        result['stdout'] = b''
        raise OutputLimit(result)
    if io_errors and not timed_out:
        # Whatever the exit code was, the output or the input is not trustworthy.
        result['stdout'] = b''
        result['returncode'] = None
        raise JobIOError(result)
    return result


def _stub(gate, argv):
    deadline = time.monotonic() + 10
    while not os.path.exists(gate):
        if time.monotonic() > deadline:
            return GATE_TIMEOUT_EXIT
        time.sleep(0.01)
    try:
        return subprocess.call(argv)
    except OSError:
        return TARGET_START_FAILED_EXIT


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == '--stub':
        sys.exit(_stub(sys.argv[2], sys.argv[3:]))
    sys.exit('library module; used by the adapter wrapper')
