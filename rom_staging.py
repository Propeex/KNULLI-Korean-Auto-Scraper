"""Safe temporary ROM input preparation for Skyscraper.

Small games may be copied for checksum lookup. Large games can be queried by
name without transferring their ISO/CSO/PBP/CHD contents over USB ADB.

A Skyscraper invocation always requires a local filename. The temporary stub
is solely a filename carrier for explicit --query romnom searches; it is
NEVER a ROM copy, is not uploaded to the handheld and is removed automatically
with the temporary directory. Never run hash searches on the stub.
"""
from __future__ import annotations

from pathlib import Path
import hashlib

# Large disc games supported in name-only mode. Archive containers can require
# parsing/extraction by specific Skyscraper versions and are intentionally not
# substituted with invalid .zip/.7z files.
NAME_ONLY_EXT = frozenset({'.iso', '.cso', '.pbp', '.chd', '.cdi', '.gdi'})
# Do not put game contents, file hashes or secrets in the input file. A small
# filename/path-derived marker differentiates otherwise identical fake files,
# preventing accidental resource-cache cross-association between two games.
PLACEHOLDER_PREFIX = b'KNULLI NAME-ONLY SEARCH INPUT\n'


def placeholder_for(remote: str) -> bytes:
    label = hashlib.sha256(remote.encode('utf-8')).hexdigest().encode('ascii')
    data = PLACEHOLDER_PREFIX + label + b'\n'
    return data + b'\x00' * (4096 - len(data))


def prepare(adb, remote: str, destination: Path, size: int,
            limit_mb: int = 256) -> bool:
    """Prepare local Skyscraper filename.

    Return True only if this is a synthetic name-only disc file. Never copy
    the actual multi-GB disc to the PC in that case. All other formats retain
    the existing size guard to avoid invalid compressed-file parsing.
    """
    if not isinstance(size, int) or size < 0:
        raise ValueError('ROM 파일 크기를 확인할 수 없습니다.')
    if not isinstance(limit_mb, int) or limit_mb < 1:
        raise ValueError('max_rom_transfer_mb는 1 이상의 정수여야 합니다.')
    if size > limit_mb * 1024 * 1024:
        if destination.suffix.lower() not in NAME_ONLY_EXT:
            raise ValueError('rom_too_large: 이 파일 형식은 이름 검색용 가상 ROM을 지원하지 않습니다.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(placeholder_for(remote))
        return True
    destination.parent.mkdir(parents=True, exist_ok=True)
    adb.pull(remote, destination)
    if destination.stat().st_size != size:
        raise RuntimeError('ADB ROM 복사 크기가 원본과 일치하지 않습니다.')
    return False
