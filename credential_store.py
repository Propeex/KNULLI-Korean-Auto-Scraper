"""Windows Credential Manager implementation for the ScreenScraper account.

No account password is intentionally written to a text file. On other platforms
credentials are not persisted; callers can still use an in-memory config.
"""
from __future__ import annotations
import ctypes
import json
import os
from ctypes import wintypes

TARGET='KNULLI Auto Scraper / ScreenScraper'


if os.name=='nt':
    class FILETIME(ctypes.Structure):
        _fields_=[('dwLowDateTime',wintypes.DWORD),('dwHighDateTime',wintypes.DWORD)]
    class CREDENTIALW(ctypes.Structure):
        _fields_=[('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),
                  ('Comment',wintypes.LPWSTR),('LastWritten',FILETIME),('CredentialBlobSize',wintypes.DWORD),
                  ('CredentialBlob',ctypes.POINTER(ctypes.c_ubyte)),('Persist',wintypes.DWORD),
                  ('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),
                  ('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]
    advapi=ctypes.WinDLL('Advapi32.dll',use_last_error=True)
    advapi.CredWriteW.argtypes=[ctypes.POINTER(CREDENTIALW),wintypes.DWORD]
    advapi.CredWriteW.restype=wintypes.BOOL
    advapi.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(CREDENTIALW))]
    advapi.CredReadW.restype=wintypes.BOOL
    advapi.CredFree.argtypes=[ctypes.c_void_p]
    advapi.CredFree.restype=None
    advapi.CredDeleteW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD]
    advapi.CredDeleteW.restype=wintypes.BOOL


def write(account:dict):
    user=str(account.get('user') or '').strip(); passwd=str(account.get('password') or '')
    if os.name!='nt':return False
    if not user and not passwd:
        advapi.CredDeleteW(TARGET,1,0)
        return True
    payload=json.dumps({'user':user,'password':passwd},ensure_ascii=False).encode('utf-16-le')
    if len(payload)>2500:raise ValueError('Credential too long')
    raw=(ctypes.c_ubyte*len(payload)).from_buffer_copy(payload)
    cred=CREDENTIALW()
    cred.Type=1  # CRED_TYPE_GENERIC
    cred.TargetName=TARGET
    cred.UserName=user
    cred.CredentialBlobSize=len(payload)
    cred.CredentialBlob=raw
    cred.Persist=2  # CRED_PERSIST_LOCAL_MACHINE: survives app removal
    cred.Comment='ScreenScraper user credentials for KNULLI Auto Scraper'
    if not advapi.CredWriteW(ctypes.byref(cred),0):
        raise OSError(ctypes.get_last_error(),'Windows 자격 증명 저장 실패')
    return True


def read():
    if os.name!='nt':return {}
    p=ctypes.POINTER(CREDENTIALW)()
    if not advapi.CredReadW(TARGET,1,0,ctypes.byref(p)):
        return {}
    try:
        cred=p.contents
        if not cred.CredentialBlob or not cred.CredentialBlobSize:return {}
        value=ctypes.string_at(cred.CredentialBlob,cred.CredentialBlobSize).decode('utf-16-le')
        obj=json.loads(value)
        return {'user':str(obj.get('user','')),'password':str(obj.get('password',''))}
    finally:
        advapi.CredFree(p)
