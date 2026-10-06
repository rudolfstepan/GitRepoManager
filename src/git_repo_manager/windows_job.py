"""Keep a Windows Git process tree cancellable even if its launcher exits early."""
from __future__ import annotations
import ctypes
import os


class ProcessJob:
    def __init__(self, process):
        self.handle = None
        if os.name != "nt":
            return
        # A nested job keeps track of Git/SSH children after their parent exits.
        # https://learn.microsoft.com/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, ctypes.c_wchar_p], ctypes.c_void_p),
            "AssignProcessToJobObject": ([ctypes.c_void_p, ctypes.c_void_p], ctypes.c_int),
            "TerminateJobObject": ([ctypes.c_void_p, ctypes.c_uint], ctypes.c_int),
            "CloseHandle": ([ctypes.c_void_p], ctypes.c_int),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.api, name)
            fn.argtypes, fn.restype = args, result
        handle = self.api.CreateJobObjectW(None, None)
        if handle:
            if self.api.AssignProcessToJobObject(handle, int(process._handle)):
                self.handle = handle
            else:
                self.api.CloseHandle(handle)

    def terminate(self) -> bool:
        return bool(self.handle and self.api.TerminateJobObject(self.handle, 1))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None
