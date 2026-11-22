# 릴리즈 운영 규칙

> **사용자 확정 요청 (2026-11-23):** 개발 작업이 성공적으로 완료되면 매번 GitHub Release를 발행한다. 사용자가 정식 출시를 명시적으로 승인하기 전까지 모든 릴리즈는 **Beta / Pre-release**다. 버전 번호 결정과 배포는 개발 담당자가 수행한다.

## 버전 규칙

- **현재 최신 공개 베타:** [`v0.8.7-beta.1`](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.1) (이전: `v0.8.6-beta.1`).
- 표준 형식: `vMAJOR.MINOR.PATCH-beta.N`. 예: `v0.8.5-beta.2`, `v0.8.6-beta.1`
- 같은 기능 버전에서 버그 수정/재빌드는 `beta.N`을 증가.
- 새 기능/호환성 변경은 보통 PATCH 번호를 증가시킨 뒤 `beta.1`부터 시작.
- 사용자 명시 승인 없이 **`v1.0.0` / 안정(Stable) 릴리즈를 만들지 않는다.** 제품의 이전 버전은 여전히 베타로 유지.
- 모든 GitHub Release는 `prerelease=true`로 발행하며, 최신 안정 버전 마크는 붙이지 않는다.
- 이미 발행한 태그는 덮어쓰거나 재사용하지 않는다. 추가 수정 시 다음 베타 번호를 사용한다.

## 매 작업 완료 시 필수 절차

1. GitHub `main` 기준으로 개발·테스트·문서 업데이트를 끝낸다.
2. `README.md`, `docs/HANDOFF.md`, `docs/CHANGELOG.md`, `docs/KNOWN_ISSUES.md`에 변경 사항, 이유, 검증, 중단 지점/다음 할 일을 남긴다.
3. GUI 프로그램 표시 버전과 `release/request.json`의 태그, `release/notes.md` 내용을 일치시킨다.
4. **최종 단계에서** `release/request.json`의 버전 값 변경을 `main`에 커밋한다. 이 파일의 변경이 `.github/workflows/publish-beta.yml`를 실행한다.
5. GitHub Actions는 Linux Xvfb 테스트를 통과해야만 `scripts/package_release.py`로 Windows ZIP을 묶고 SHA-256을 검사한다.
6. GitHub Release를 Git 태그 `v...-beta.N`에 게시한다. ZIP, `.sha256` 파일과 릴리즈 노트를 첨부한다.
7. 릴리즈의 **Pre-release 여부, ZIP 다운로드 자산, 테스트 성공 여부**를 직접 확인한 뒤 사용자에게 정확한 Release 링크를 안내한다.
8. 실제 Windows + RG35XX Plus에서 테스트하지 못한 기능은 문서와 릴리즈 노트에 미검증이라고 명시한다. GitHub CI 성공을 실기기 성공으로 과장하지 않는다.

## 자동 업데이트와 릴리즈 호환성

- `v0.8.6-beta.1`부터 앱 시작 시 GitHub의 공개 베타 릴리즈 목록을 검색하고 최신 베타 ZIP을 자동 설치·재시작합니다. 사용자 확인이 필요하지 않습니다.
- 업데이트 대상 베타는 **기존보다 높은 버전**만 허용하며, 사용자가 승인하지 않은 안정판을 자동 설치하지 않습니다.
- 모든 새로운 릴리즈 ZIP은 `app_version.py`, `auto_update.py`, `auto_update_helper.py`, `GUI_실행.pyw`를 포함해야 합니다.
- 릴리즈 빌드는 `app_version.VERSION_TAG`와 `release/request.json` 버전이 일치하는지 검증합니다.
- 기존 `v0.8.5-beta.2` 설치에는 자동 업데이트 기능이 없으므로 `v0.8.6-beta.1`만 최초 수동 설치가 필요합니다.
- 향후 사용자 승인 없이 자동 업데이트는 계속 작동하되 모든 태그는 베타 정책을 따라야 합니다.

## 배포 내용

Windows ZIP에는 `GUI_실행.pyw`, `GUI_실행.vbs`, Python 앱 모듈, `artwork.xml`, `aliases.json`, 예제 설정, 실행 안내를 포함한다. 테스트 코드·ROM·BIOS·실제 설정·계정 비밀번호·ADB/Skyscraper 제3자 바이너리는 포함하지 않는다.

이 배포는 Python 소스 기반 GUI 앱 ZIP이다. 독립 실행 EXE가 **아니며**, Windows에 Python 3.10+ 및 Tkinter가 필요하다. 프로그램에서 ADB/Skyscraper를 자동 검색·설치 시도한다.

## 오류가 날 경우

- 테스트/빌드/릴리즈가 실패하면 **완료·출시 성공이라고 말하지 않는다**.
- `release/request.json` 버전 번호를 재사용해 릴리즈를 뒤늦게 덮어쓰지 않는다. 배포 여부 확인 후 안전하게 재시도한다.
- `main` 코드 자체가 테스트를 통과하더라도 릴리즈 자산 검증이 실패하면 발행을 완료로 간주하지 않는다.
- `docs/HANDOFF.md`의 현재 릴리즈 태그, 마지막 중단 지점, 다음 확인 항목을 갱신한다.
