"""First-launch installer for Google's official Windows Platform Tools.

Downloads only when ADB is missing. Does NOT start/kill/restart ADB.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import os
import shutil
import tempfile
import urllib.request
import zipfile

HERE=Path(__file__).resolve().parent
SOURCE='https://dl.google.com/android/repository/platform-tools-latest-windows.zip'
LICENSE='https://developer.android.com/studio/terms'
MAX_DOWNLOAD=160*1024*1024
MAX_EXTRACT=600*1024*1024


def existing_adb(config=None):
    import core
    configured=(config or {}).get('adb_path','')
    try:
        exe=core.Adb(configured or None).binary
        if exe and Path(exe).is_file():return str(Path(exe).resolve())
    except (RuntimeError,ValueError):pass
    exe=shutil.which('adb')
    return str(Path(exe).resolve()) if exe else None


def setup(progress=None):
    """Install the verified official package when no compatible adb.exe is found."""
    installed=HERE/'platform-tools'/'adb.exe'
    if installed.is_file():return str(installed)
    parent=HERE
    with tempfile.TemporaryDirectory(prefix='knulli_platform_tools_') as td:
        temp=Path(td);archive=temp/'tools.zip'
        req=urllib.request.Request(SOURCE,headers={'User-Agent':'KNULLI-AutoScraper/0.6'})
        size=0
        with urllib.request.urlopen(req,timeout=35) as response,archive.open('wb') as output:
            while True:
                data=response.read(1024*1024)
                if not data:break
                size+=len(data)
                if size>MAX_DOWNLOAD:raise RuntimeError('플랫폼 도구 다운로드 용량 제한 초과')
                output.write(data)
                if progress:progress(f'Platform-Tools 다운로드 중: {size//1024//1024}MB')
        with zipfile.ZipFile(archive) as z:
            total=0;validated=[]
            for info in z.infolist():
                name=PurePosixPath(info.filename.replace('\\','/'))
                if (name.is_absolute() or '..' in name.parts or not name.parts
                        or name.parts[0]!='platform-tools' or ':' in str(name)):
                    raise RuntimeError('비정상적인 Platform-Tools ZIP 경로')
                if info.file_size>MAX_EXTRACT or ((info.external_attr>>16)&0o170000)==0o120000:
                    raise RuntimeError('비정상적인 Platform-Tools ZIP 내용')
                total+=info.file_size
                if total>MAX_EXTRACT:raise RuntimeError('압축 해제 용량 초과')
                validated.append((info,name))
            extract=temp/'unpacked'
            for info,name in validated:
                destination=extract.joinpath(*name.parts)
                if info.is_dir():destination.mkdir(parents=True,exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(info) as source,destination.open('wb') as out:
                        shutil.copyfileobj(source,out)
        folder=extract/'platform-tools'
        if not (folder/'adb.exe').is_file() or not (folder/'AdbWinApi.dll').is_file():
            raise RuntimeError('공식 패키지에 ADB 필수 파일이 없습니다.')
        # Stage all files and move the complete directory into place.
        # A failed earlier download may have left an incomplete directory. Move
        # it aside rather than requiring the user to clean up manually.
        current=HERE/'platform-tools'
        if current.exists():
            old=HERE/'platform-tools-incomplete'
            if old.exists():shutil.rmtree(old)
            current.rename(old)
        shutil.move(str(folder),str(current))
    if progress:progress('Platform-Tools 설치 완료')
    return str(installed)
