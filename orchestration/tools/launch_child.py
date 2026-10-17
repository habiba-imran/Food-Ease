"""Private stdin-controlled child; no network shutdown endpoint or shell."""

from __future__ import annotations

import _thread
import argparse
import ctypes
import importlib
import os
import select
import signal
import sys
import threading
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m",
        "--module",
        required=True,
        choices=[
            "foodease_website.main",
            "foodease_session.main",
            "uvicorn",
            "foodease_agent.worker",
        ],
    )
    args, remainder = parser.parse_known_args()

    def shutdown():
        # Native SDK imports inspect stdin. Wait for pipe data without holding
        # Python buffer / Windows CRT descriptor locks. PeekNamedPipe also works
        # for the website's Python 3.11, which has no Windows os.set_blocking.
        descriptor = sys.stdin.fileno()
        if os.name == "nt":
            import msvcrt
            from ctypes import wintypes

            handle = msvcrt.get_osfhandle(descriptor)
            peek = ctypes.WinDLL("kernel32", use_last_error=True).PeekNamedPipe
            peek.argtypes = [
                wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPDWORD,
            ]
            peek.restype = wintypes.BOOL
        pending = b""
        while len(pending) <= 64:
            size = 64
            if os.name == "nt":
                available = wintypes.DWORD()
                if not peek(handle, None, 0, None, ctypes.byref(available), None):
                    return  # Parent closed the private pipe.
                if not available.value:
                    time.sleep(0.05)
                    continue
                size = min(size, available.value)
            elif not select.select([descriptor], [], [], 0.05)[0]:
                continue
            chunk = os.read(descriptor, size)
            if not chunk:
                return
            pending += chunk
            if b"\n" in pending:
                if pending.split(b"\n", 1)[0].strip() == b"stop":
                    _thread.interrupt_main(signal.SIGINT)
                return

    threading.Thread(target=shutdown, daemon=True).start()
    sys.argv = [args.module, *remainder]
    importlib.import_module(args.module).main()


if __name__ == "__main__":
    main()
