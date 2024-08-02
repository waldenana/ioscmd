import subprocess
import sys
import threading
import time
from socket import socket


def _wait_until_quit(proc, stop_event: threading.Event) -> float:
    """
    return running seconds
    """
    start = time.time()
    elapsed = lambda: time.time() - start
    while not stop_event.is_set() and proc.poll() is None:
        time.sleep(.1)
    return elapsed()


def _get_available_port():
    with socket() as s:
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
    return port


class RelayService:
    _DEFAULT_TIMEOUT = 90  # http request timeout

    def __init__(self, udid, remote_port):
        self._proc = None
        self._udid = udid
        self._remote_port = remote_port

    def start(self):
        available = _get_available_port()
        cmds = [
            sys.executable, '-m', 'tidevice', '-u', self._udid, 'relay',
            str(available), str(self._remote_port),
        ]
        proc = subprocess.Popen(cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._proc = proc
        return available

    def stop(self):
        if self._proc:
            self._proc.terminate()
