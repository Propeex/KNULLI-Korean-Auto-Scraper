#!/usr/bin/env python3
"""One-time third-party setup. Download only from original author's fixed GitHub release.

The Windows Skyscraper archive is an older unsupported upstream build.
No archive download is executed until the user runs the setup script.
"""
from pathlib import Path, PurePosixPath
import sys
import tempfile
import urllib.request
import zipfile
import shutil

HERE=Path(__file__).resolve().parent
SOURCE='https://github.com/muldjord/skyscraper/releases/download/3.6.12/Skyscraper_3.6.12_unsupported_win_version.zip'
MAX_COMPRESSED=150*1024*1024
MAX_UNPACKED=500*1024*1024

def unzip_safely(archive, destination):
    with zipfile.ZipFile(archive) as z:
        safe=[];total=0
        for info in z.infolist():
            name=info.filename.replace('\\','/')
            p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or ':' in p.parts[0] or not p.parts:
                raise RuntimeError('Unsafe path in third-party ZIP')
            if info.file_size>MAX_UNPACKED:
                raise RuntimeError('Unexpectedly large ZIP member')
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError('ZIP symlink not accepted')
            total+=info.file_size
            if total>MAX_UNPACKED:raise RuntimeError('ZIP content size exceeds limit')
            safe.append(info)
        for info in safe:
            p=destination.joinpath(*PurePosixPath(info.filename.replace('\\','/')).parts)
            if info.is_dir():p.mkdir(parents=True,exist_ok=True)
            else:
                p.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as source, p.open('wb') as output:
                    shutil.copyfileobj(source,output)

def setup(progress=None):
    """Automatically reuse/install original-author Windows archive once, no prompts.

    This outdated Windows build is unsupported by upstream; errors are surfaced in UI.
    """
    target=HERE/'skyscraper'
    found=list(target.rglob('Skyscraper.exe'))+list(target.rglob('skyscraper.exe')) if target.exists() else []
    if found:return str(found[0])
    if progress:progress('Skyscraper 엔진 자동 설치 중 (공식 제작자 배포본)')
    with tempfile.TemporaryDirectory(prefix='knulli_engine_') as td:
        archive=Path(td)/'engine.zip';size=0
        req=urllib.request.Request(SOURCE,headers={'User-Agent':'KNULLI-AutoScraper/0.7'})
        with urllib.request.urlopen(req,timeout=45) as response, archive.open('wb') as f:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                size+=len(chunk)
                if size>MAX_COMPRESSED:raise RuntimeError('Skyscraper ZIP 크기 제한 초과')
                f.write(chunk)
                if progress:progress('Skyscraper 다운로드 '+str(size//1048576)+'MB')
        staging=Path(td)/'extracted'
        unzip_safely(archive,staging)
        tested=list(staging.rglob('Skyscraper.exe'))+list(staging.rglob('skyscraper.exe'))
        if not tested or any(x.stat().st_size==0 for x in tested):
            raise RuntimeError('Skyscraper 압축 파일에 정상 실행 파일이 없습니다.')
        if target.exists():
            incomplete=HERE/'skyscraper-incomplete'
            if incomplete.exists():shutil.rmtree(incomplete)
            target.rename(incomplete)
        shutil.move(str(staging),str(target))
    found=list(target.rglob('Skyscraper.exe'))+list(target.rglob('skyscraper.exe'))
    if not found:raise RuntimeError('Skyscraper.exe가 압축 파일에 없습니다.')
    if progress:progress('Skyscraper 엔진 설치 완료')
    return str(found[0])

def main():
    try:
        print('Engine:',setup(print))
        return 0
    except Exception as exc:
        print('SETUP ERROR:',str(exc),file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
