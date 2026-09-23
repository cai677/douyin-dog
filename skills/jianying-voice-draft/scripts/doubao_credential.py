"""Windows per-user credential store; never print or serialize the secret."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import os
from pathlib import Path
import runpy
import sys

TARGET = 'Codex/jianying-voice-draft/DoubaoTTS'
ENV = 'DOUBAO_TTS_API_KEY'

class Credential(C.Structure):
    _fields_ = [('Flags', W.DWORD), ('Type', W.DWORD), ('TargetName', W.LPWSTR),
                ('Comment', W.LPWSTR), ('LastWritten', W.FILETIME),
                ('CredentialBlobSize', W.DWORD), ('CredentialBlob', C.POINTER(W.BYTE)),
                ('Persist', W.DWORD), ('AttributeCount', W.DWORD),
                ('Attributes', C.c_void_p), ('TargetAlias', W.LPWSTR), ('UserName', W.LPWSTR)]

def api():
    dll = C.WinDLL('Advapi32.dll', use_last_error=True)
    dll.CredReadW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, C.POINTER(C.POINTER(Credential))]
    dll.CredReadW.restype = W.BOOL
    dll.CredWriteW.argtypes = [C.POINTER(Credential), W.DWORD]
    dll.CredWriteW.restype = W.BOOL
    dll.CredFree.argtypes = [C.c_void_p]
    return dll

def read_key():
    dll = api()
    ptr = C.POINTER(Credential)()
    if not dll.CredReadW(TARGET, 1, 0, C.byref(ptr)):
        code = C.get_last_error()
        raise RuntimeError(f'Credential unavailable (Windows error {code}); local setup required')
    try:
        return C.string_at(ptr.contents.CredentialBlob, ptr.contents.CredentialBlobSize).decode('utf-16-le')
    finally:
        dll.CredFree(ptr)

def store_key(key):
    if not key or not key.strip():
        raise RuntimeError('API key is empty')
    raw = key.strip().encode('utf-16-le')
    blob = (W.BYTE * len(raw)).from_buffer_copy(raw)
    cred = Credential()
    cred.Type = 1
    cred.TargetName = TARGET
    cred.Comment = 'Doubao TTS for local Jianying voice drafts; user-authorized persistence'
    cred.CredentialBlobSize = len(raw)
    cred.CredentialBlob = C.cast(blob, C.POINTER(W.BYTE))
    cred.Persist = 2
    cred.UserName = 'DoubaoTTS'
    try:
        if not api().CredWriteW(C.byref(cred), 0):
            raise RuntimeError(f'Credential write failed (Windows error {C.get_last_error()})')
        if read_key() != key.strip():
            raise RuntimeError('Credential round-trip mismatch')
    finally:
        C.memset(blob, 0, len(raw))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'store-env', 'run'])
    parser.add_argument('script', nargs='?')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'store-env':
        store_key(os.environ.pop(ENV, ''))
        print('Credential saved; read-back verified. No key displayed.')
    elif args.action == 'status':
        if not read_key():
            raise RuntimeError('Stored credential is empty')
        print('Credential available for current Windows user.')
    else:
        if not args.script:
            parser.error('run requires a Python script path')
        script = Path(args.script).resolve(strict=True)
        previous = os.environ.get(ENV)
        os.environ[ENV] = read_key()
        sys.argv = [str(script)] + args.args
        sys.path.insert(0, str(script.parent))
        try:
            runpy.run_path(str(script), run_name='__main__')
        finally:
            if previous is None:
                os.environ.pop(ENV, None)
            else:
                os.environ[ENV] = previous

if __name__ == '__main__':
    main()
