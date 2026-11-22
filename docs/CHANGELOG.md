# 변경 이력

## v0.8.7-beta.3 — PSP 대용량 디스크 `rom_too_large` 수정 (2026-11-23)

- 사용자 보고: PSP ISO/CSO가 256MiB 이상일 때 게임을 스크래핑하지 않고 `rom_too_large` 처리됨.
- **원인:** GUI `bundle_engine._process_selected`가 게임 원본 파일을 기기에서 PC로 통째로 가져오도록 구현됐고, 기본 제한 `max_rom_transfer_mb=256`으로 시작 전 작업 차단.
- **수정:** 제한을 초과하는 `.iso`/`.cso`/`.pbp`/`.chd`/`.cdi`/`.gdi`는 실제 디스크를 복사하지 않고 경로마다 다른 작은 임시 파일명 운반체를 생성해 **Skyscraper의 `--query romnom=...` 이름 검색만 실행**. 작은 ROM은 기존 해시 조회 방식 유지.
- Skyscraper는 `--query`일 때 자동 파일 해시 검색을 사용하지 않는다고 문서화. **검색 이름과 검색 결과 게임명 유사도 검증은 반드시 유지**하고, 영문 후보가 없으면 안전하게 중단.
- 공유 `rom_staging.py`를 도입해 GUI·구형 backend·CLI legacy 코드의 대용량 디스크 처리 동일화. 다른 형식(큰 ZIP/7z 등)은 가짜 압축파일로 잘못 처리하지 않도록 기존 제한 유지.
- 2GiB를 가상으로 보고하는 PSP ROM에서 실제 ADB 파일 복사가 전혀 호출되지 않음을 자동 테스트로 검증, 한글명/XML 원본과 기존 ROM 보존.
- [PR #6](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/6). 실제 Windows Skyscraper/사용자 RG35XX Plus에서의 통합 검증은 아직 필요.


## v0.8.7-beta.2 — Atomiswave .7z 게임 인식 누락 수정 (2026-11-23)

- 사용자 보고: `/userdata/roms/atomiswave`의 `.7z` 게임이 앱 목록에 나타나지 않음.
- 원인: `core.ROM_EXT`에 `.7z`는 이미 포함되어 있었으나 `core.SYSTEM_IDS`에 `atomiswave` 시스템이 빠져 있었음.
- ScreenScraper 시스템 ID `53` 및 Skyscraper `atomiswave` 플랫폼 연결, GUI에 `Atomiswave` 기종 표시.
- 확장자 `.7z`, `.zip`, `.chd`, `.bin`와 전용 `.lst`, `.dat` 지원. 한글 중첩 폴더와 대문자 확장자 인식.
- 원본 압축 ROM의 이름/내용을 변경하지 않으며, 한글 표시명 보존 및 스크랩 데이터 XML 자동 백업 금지 정책 유지.
- [PR #5](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/5) main 병합 완료. [GitHub Windows/Linux 배포 CI](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45058337387) 성공. **[v0.8.7-beta.2 Pre-release](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.2) 발행 및 ZIP 90,550 bytes / .sha256 첨부 확인.** 사용자 실기기 검증 미완료.


## v0.8.7-beta.1 — PortMaster 게임 스크래핑 (2026-11-23)

- KNULLI `/userdata/roms/ports` 최상위 `.sh` 포팅 게임을 **PortMaster** 기종으로 탐색. 관리 도구/설치 스크립트 및 게임 데이터 폴더 재귀 탐색은 제외.
- 설치된 PortMaster의 `gameinfo.xml`/`port.json`에서 제목·설명·장르·개발사·출시일 등을 오프라인 조회, `cover`/`screenshot` 이미지는 기존 기기 경로로 연결.
- 정확한 실행 파일 매칭이 확인된 경우에만 `ports/gamelist.xml`에 **비어 있는 메타데이터를 보충**. 한글 사용자 이름·설명·이미지와 기존 포트 게임 실행 파일을 보호.
- PortMaster-only 작업은 Skyscraper 또는 포트 ROM 복사 없이 실행. USB ADB만 사용.
- 사용자가 승인한 삭제된 포트 게임 정리는 XML 항목만 다루며 포트 데이터·세이브 폴더는 삭제하지 않음.
- **XML 스크랩 데이터 백업은 생성하지 않음.** 기존 사용자 요청 유지.
- [PR #4](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/4) main 병합, [v0.8.7-beta.1 Pre-release](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.1) 발행 완료. [Windows+Linux GitHub Actions 검증](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45056648631) 통과. Windows ZIP(89,599 bytes) 및 SHA-256 첨부 확인. **실제 RG35XX Plus에서 다양한 PortMaster 포맷의 동작은 재검증 필요.**


## v0.8.6-beta.1 — 실행 시 베타 자동 업데이트/재시작 (2026-11-23)
- GitHub 공개 릴리즈를 조회해 현재 설치 버전보다 높은 최신 **베타**를 자동 검색. 안정판은 정식 출시 승인 전까지 제외.
- 새로운 베타가 있으면 별도 확인 없이 ZIP과 checksum을 다운로드하고 SHA256/API digest, 파일 경로, 패키지 버전을 검증.
- 원래 GUI 프로세스 종료 후 별도 updater가 프로그램 코드만 교체, 자동 재시작. 교체 실패 시 코드 롤백 및 기존 앱 재시작을 시도.
- 최신 사용자 설정·스크랩 데이터·ROM·KNULLI XML 보존. 사용자 수정 aliases.json/artwork.xml 덮어쓰기 방지.
- 네트워크 장애 시 기존 앱으로 계속 실행, 동시 업데이트 잠금, 작업 로그 저장.
- 업데이터가 없는 이전 v0.8.5-beta.2는 **이번 릴리즈를 처음 한 번 수동 설치**해야 함. 이후 자동 업데이트 작동.
- [PR #3](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/3) main 병합. [릴리즈 GitHub Actions](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45052031828)에서 Linux 전체 회귀·Windows 업데이터 테스트/실제 Windows 프로세스 대기·ZIP/체크섬 검증 모두 통과. **실제 사용자 PC에서 자동 업그레이드 성공은 아직 검증 전**.
- **GitHub 사전 출시 완료:** [v0.8.6-beta.1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.6-beta.1), Windows ZIP(82,651 bytes) + SHA-256 확인 파일.


## v0.8.5-beta.2 — ADB 명령 길이 오류 및 스크래핑 백업 폐지 (2026-11-23)
- 실제 사용자 오류: `삭제된 게임 검사 실패: ADB shell failed: error: shell command too long`.
- 삭제된 게임을 검사할 때 한글 경로를 한 번만 영숫자로 인코딩하고, 기기 셸 명령 길이 예산에 맞춰 잘라서 검사. 그래도 명령 길이 때문에 실패하면 다시 분할; 단일 경로나 응답 오류는 안전을 위해 검사 중단.
- 사용자 요청에 따라 스크래핑, 이름/설명 변경, 자동 한글 표시명 동기화 및 삭제된 게임 자료 정리에서 **새로운 XML 백업 파일 생성 중단**.
- 최초 기기 연결 후 과거 버전이 만든 `gamelist.xml.knulli-autoscraper-<timestamp>.bak`만 삭제. 로컬에서는 현재 폴더 및 같은 상위 폴더에 있는 검증된 이전 설치본의 `work/xml_backups/<system>_<timestamp>.xml`만 삭제.
- ROM 원본, 현재 `gamelist.xml`, 이미지·영상, 사용자 개인 백업, 설정 및 자격 증명은 정리 대상에서 제외.
- 비정상 경로/ADB 응답/권한 오류가 있으면 삭제된 게임으로 잘못 판단하지 않음.
- [PR #2](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/2), GitHub 자동 테스트 85개 통과 ([실행](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45048905011)). 실기기 재검증은 아직.
- 주의: 자동 XML 백업이 없어 예상치 못한 쓰기 실패 시 복구가 더 어려울 수 있음.
- **GitHub 사전 출시 완료:** [v0.8.5-beta.2](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.5-beta.2), Windows ZIP(72,525 bytes), SHA256 파일 포함. [GitHub Actions 릴리즈 테스트 및 게시 성공](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45049288546). 실제 기기 재시험은 미완료.


## v0.8.5-beta.1 — 첫 GitHub 사전 출시 (2026-11-23)
- 사용자가 기기에서 ROM을 삭제한 후 GUI 목록을 조회하면 사라진 게임의 gamelist.xml 항목을 검사.
- ROM 실존 여부를 ADB로 직접 재확인하고, 정리할 XML 항목과 단독 소유 미디어 수를 미리 보여줌.
- 사용자 승인 이후 XML 백업·게임 항목 제거·다른 게임이 참조하지 않는 명시적 미디어 파일 제거.
- 의심스러운 경로, 시스템 범위 밖 자원, 공유 미디어, 잘못된 XML, 조회 중 다시 생성된 ROM은 보호.
- 작업 결과를 work/last_cleanup.json에 기록. Linux + 가상 디스플레이의 GitHub CI 테스트 통과; **실제 기기 검증 전**.
- ROM이 없는 시스템에서도 정리할 수 있게 빈 ROM 목록 처리를 보완.
- [PR #1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/1) 통해 main에 병합.
- **GitHub Release 발행:** [v0.8.5-beta.1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.5-beta.1), Windows ZIP + SHA-256 checksum 파일. [릴리즈 검증 GitHub Actions](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45046433924) 성공. 베타(Pre-release) 상태 확인.


## v0.8.4 — GitHub 최초 이식 기준(2026-11-20)
- 한글 하위 폴더 경로의 ADB 탐색/파일 크기 조회 인코딩 보완.
- 문제 사례: `psx/한글 게임 폴더/Silent Hill (K).cue` → 경로 `????`, 파일 크기 확인 불가.
- 가상 환경 테스트 60개 통과; 실기기 결과는 미확인.
- **이 GitHub 이식은 v0.8.4 기준 코드 보존 작업이며 기능 수정/업그레이드가 아님.**

## v0.8.3
- 현재 선택 행 음영/마커 개선.
- 영어 `gamelist.xml <name>`을 한글 파일명 기준으로 동기화.
- Neo Geo 등 보호된 ZIP은 사용자 표시명 유지.

## v0.8.2
- 무채색 다크 GUI, 교차 행 음영 제거.
- 목록 상태 열 추가(선택/기종/게임명/상태).
- 영문 게임명 자동 저장.

## v0.8.1
- 다크 모드·선택 행 강조, 게임 정보 및 설정 화면 스크롤 개선.

## v0.8.0
- 간결한 단일 상세 화면.
- 사용자 데이터 앱 폴더 외부 보관.
- 완료된 게임 중간 결과 조회, 번역 기능 제거.

## v0.7.x
- 자동 ADB/Skyscraper 설치 시도, 파일명/표시명 편집, KNULLI 스크래핑 설정 조정.
- ROM 게임명 한글↔영문 사전 자동 기록.

## v0.6
- ROM 파일명 변경·연동된 gamelist.xml/이미지 경로 관리.
- 다양한 미디어·메타데이터 선택과 조회.

## v0.5
- 체크박스 GUI, 기존 자원 미리보기, 재스크래핑, 영문 검색어 수정.
- Skyscraper `artwork.xml` 구성 오류 대응.

## v0.4 이하
- ScreenScraper 직접 API 인증 대신 Skyscraper 엔진 사용.
- USB ADB 직접 접근·ROM 탐색·XML 백업/병합.
- `exec-out` 오류를 우회하는 ROM 탐색.
