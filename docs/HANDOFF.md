# 개발 인수인계 / 다음 대화의 시작점

> **이 문서를 가장 먼저 읽으세요.** GitHub 저장소가 프로젝트의 단일 기준(source of truth)입니다. 대화의 기억이나 이전 ZIP 링크보다 저장소의 코드·문서·커밋을 우선합니다.

## 기준 상태
- 작성일: 2026-11-20 (Asia/Seoul)
- 프로젝트: KNULLI Korean Auto Scraper
- 저장소: https://github.com/Propeex/KNULLI-Korean-Auto-Scraper
- **현재 최신 공개 베타: [`v0.8.8-beta.1`](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.8-beta.1) (PS1 멀티디스크 M3U 지원).** 이전 베타: `v0.8.7-beta.3`. 최초 이식 소스 기준: `v0.8.4`.
- 대상: Windows PC, RG35XX Plus (KNULLI), USB ADB
- 스크래핑: Windows에서 Skyscraper / ScreenScraper 사용. PC 인터넷만 필요, 기기 인터넷 불필요.
- **GitHub 최초 이식 완료:** 2026-11-20, 원본 v0.8.4 소스를 코드 변경 없이 복원한 커밋 `4734f7a954d0953a6f1306f8a3910039bcc6a634`. 원본 압축 스냅샷 SHA256 검증 및 GitHub Actions 복원 성공. 상세 기록: [MIGRATION.md](MIGRATION.md). 실기기 테스트는 사용자 환경에서 별도 확인해야 함.

## 프로젝트 핵심 목적
한글 ROM을 기기에 준비한 사용자에게 ROM 파일명을 변경하거나, 이미지·XML을 수동 복사/병합하라고 요구하지 않는다. PC GUI에서 ROM 선택 → 자동 영문 매칭 → 스크래핑 → 미디어 전송 → XML 병합을 처리한다.

## 현재 구현되어 있다고 기록된 주요 기능
- USB ADB를 통한 /userdata/roms 탐색, 한글·특수문자 포함 파일명, 하위 폴더 한글 경로 대응
- 검정·회색 다크 GUI. 4열 **선택 / 기종 / 게임명 / 상태** 목록
- 마우스 단일 클릭으로 상세 조회, 더블클릭 또는 Space로 체크
- 전체 선택, 데이터 없는 게임 선택(**모든 의미 있는 데이터가 하나도 없는 경우만**), 실패 항목 선택, 작업 시작
- 일반 ROM 파일명 편집(확장자 고정), 위험한 ZIP은 gamelist.xml 표시명만 수정
- 검색용 영어 게임명 자동 저장, 설명 수동 편집, 이미지 미리보기
- 성공 후 KNULLI gamelist.xml의 한글 표시명 동기화; v0.8.5-beta.2부터 영구 XML 백업 미생성
- 계정 정보는 Windows 자격 증명 관리자, 검색 사전은 사용자 문서 폴더에 보관
- Skyscraper 기반 검색/적용. 별도 개발자 API ID는 요구하지 않음
- 완료된 게임은 전체 작업 종료 전에 미리보기 조회 가능(편집은 작업 중 잠금)
- ADB/Skyscraper 자동 검색·설치 시도

## 마지막 확인된 문제와 수정
- v0.8.3에서 한글 하위 폴더 `psx/한글 폴더/Silent Hill (K).cue`의 경로가 `????`로 깨져 `remote file size unavailable` 발생.
- v0.8.4에서 기기 경로를 바이트/NUL 구분 + 영숫자 인코딩으로 PC에 전달, 파일 크기 조회의 인코딩 개선.
- **단위 테스트는 통과했지만 이 v0.8.4 수정의 실기기 성공 피드백은 아직 받지 못함.**

## 구현·배포 완료 — PS1 멀티디스크 자동 통합 및 M3U 생성 (v0.8.8-beta.1, 2026-11-23)

- **요청:** 드래곤 퀘스트 7 PS1 디스크 2개가 목록에 따로 보이는 문제를 해결하고 스크래핑 한 번으로 처리. 작업 완료 시 새 GitHub Beta Release 발행 및 이 인수인계 문서 갱신.
- **기준 문서:** [KNULLI Multi-Disc Games](https://knulli.org/configure/multi-disc-games/). KNULLI는 M3U가 가리키는 디스크를 프론트엔드 옵션으로 숨김.
- **구현:** `core.ROM_EXT`에 PS1 `.m3u`/`.ccd` 추가, `multidisc.py`(Disc/Disk/CD/디스크 1..N 정확한 인식, M3U 상대경로 읽기/검증, 스캔 중 논리적 그룹 통합 및 승인 후 M3U 생성), `backend.catalogue` 그룹 항목 표시, `gui.py` [멀티디스크 묶기] 버튼, `bundle_engine.py`/레거시 backend의 M3U 게임명 검색 강제.
- **동작:** 기존 유효한 M3U는 대표 게임으로 사용하고 그 안에 참조된 개별 디스크 행을 숨김. M3U 없는 경우 같은 폴더의 정확한 Disc 1..N 세트만 임시로 한 게임 행으로 묶음. M3U 실제 생성은 사용자 버튼 및 명시적 확인 후 진행.
- **안전:** 디스크 원본/세이브/메모리카드/기존 M3U 파일을 변경·삭제·덮어쓰지 않음. 원격 M3U 파일 생성 전 원본 디스크 존재 재검증, 셸 noclobber 처리. Disc 1 XML 메타데이터(사용자 게임명·설명·미디어) 복사 시 기존 항목 보존, XML 영구 백업 미생성.
- **범위:** M3U 안의 안전한 상대경로는 하위 폴더로 연결 가능. 새 M3U 자동 생성은 같은 폴더의 명확한 디스크 세트에 한정. 이상한/누락 파일 M3U는 추측하지 않고 기존 디스크를 표시.
- **테스트:** `tests/test_v088_multidisc.py` Windows/Linux 유닛, Linux 실제 POSIX 셸 시뮬레이션에서 한글 M3U 생성, 디스크·세이브·기존 XML 보존 확인. Windows 릴리즈 게이트에 추가.
- **구현 및 main 병합 완료:** [PR #7](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/7) (squash commit `d173927b120493bb7e85dce4cf5776e9b4b35d19`), 개발 브랜치 `feature/psx-multidisc-m3u-v088`.
- **릴리즈 완료 및 검증 (2026-11-23):** [v0.8.8-beta.1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.8-beta.1) 공개, `prerelease=true`. Windows ZIP 100,707 bytes, SHA256 `b29bb275d079ddb2c0606ffc7844363418df4efa285fef23699d845d9dc236f3`, `.sha256` 첨부 파일 확인. [GitHub Actions](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45147929620) Windows + Linux 전체 테스트, 패키징·체크섬·릴리즈 검사 모두 성공.
- **현재 중단 지점 / 다음 작업:** 사용자 RG35XX Plus에서 `.m3u` 신규 생성 후 KNULLI의 `Ignore Multi-File Disk Content` 설정 및 게임 목록 갱신, 실제 Disc 1 실행·Disc 2 전환과 기존 세이브 호환성 확인. 사용자 PC에서 멀티디스크 게임명 검색·이미지 메타데이터 적용도 검증. 특정 파일명 규칙·폴더 구조가 매칭되지 않으면 로그/목록 사례를 수집해 다음 Beta에서 수정.
- **정책:** 정식판 승인 전 베타만 출시, 성공적으로 끝난 모든 작업은 릴리즈 필수, GitHub 문서에 다음 대화의 개발 중단 지점까지 기록.

## 수정·배포 완료 — PSP 대용량 디스크 `rom_too_large` (v0.8.7-beta.3, 2026-11-23)

- **사용자 문제:** PSP 게임 ISO 등이 256MB를 초과해 `rom_too_large`로 표시됨. 이미지·텍스트 스크래핑에 원본 수 GB 디스크를 PC로 복사할 필요가 없다고 지적.
- **확인된 원인:** GUI의 `bundle_engine.py`와 구형 `backend.py`/`legacy_bridge.py`가 모든 ROM을 먼저 PC로 복사하므로 `max_rom_transfer_mb=256`을 넘으면 검색 전에 차단.
- **대응:** 신규 `rom_staging.py`로 공통 입력 준비. 전송 제한 이하 게임은 기존 원본 복사·해시 검색. 제한 초과 디스크 형식(`.iso`, `.cso`, `.pbp`, `.chd`, `.cdi`, `.gdi`)은 원본을 읽지 않고 **4KiB짜리 임시 파일명 운반체**로만 Skyscraper 호출. 출처 ROM의 원격 경로별 SHA-256 라벨로 운반체를 구분(원본 내용 해시 아님), 캐시 혼동 방지.
- **검색 안전성:** 대용량 디스크는 `--query romnom=영문 검색명`만 사용해 가짜 파일의 체크섬 조회를 차단. 기존 반환 게임 제목 ↔ 검색어 유사도 검사를 유지. 검색어가 없거나 일치하지 않으면 적용하지 않음. Skyscraper 문서에 `--query` 시 자동 해시 검색 미수행 명시.
- **범위:** ZIP/7z 등 큰 압축파일은 유효하지 않은 가짜 아카이브가 파서에 사용될 수 있어 우회하지 않고 기존 제한 유지. PSP ISO/CSO/PBP/CHD에 집중. 원본 ROM·기기 설정·사용자 한글 이름 보호. XML 영구 백업 미생성 정책 유지.
- **수정 경로:** `bundle_engine.py`(현재 GUI), `backend.py`(레거시 직접 스크래핑), `legacy_bridge.py`(레거시 CLI), `rom_staging.py`(신규), `tests/test_v087_beta3_large_psp.py`(자동 검증), Windows GitHub CI 게이트.
- **자동 테스트:** PSP 2GiB 가상 `stat_size`로 실제 ROM `adb.pull` 호출 0회 보장, `--query` 강제, 작은 ROM 기존 복사, 큰 ZIP/7z 차단, XML/한글명 보존, 코드 캐시 고유성 회귀 테스트.
- **구현 및 main 병합 완료:** [PR #6](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/6), merge SHA `0ce7bac6d1f8ceef2d79198f9a038e6dee84405b`, 개발 브랜치 `fix/large-psp-rom-name-only-v087-beta3`.
- **릴리즈 완료 (2026-11-23):** [v0.8.7-beta.3 Pre-release](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.3) 발행. [GitHub Actions Windows+Linux 릴리즈 실행](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45059639699) Windows 전용 및 Linux 전체 테스트, ZIP 빌드·체크섬, 공개 Pre-release와 첨부파일 확인 전 단계 성공. Windows ZIP 93,758 bytes, SHA256 `8de6fc11e49f569fac20fa4dc32a16e269a9c3a3b3bafcb353958bfff29eecfd`. **다음 작업:** 실제 사용자 Windows Skyscraper에서 PSP .iso/.cso 이름 검색 결과, 원본 ROM 미전송, 영어 검색어 매칭과 이미지 적용 확인. 큰 ZIP/7z는 의도적으로 기존 제한을 유지함.
- **정책:** 모든 작업 성공 후 GitHub Beta Pre-release까지 발행. 이 HANDOFF의 현재 공개 릴리즈/중단 지점을 최신화. 사용자 정식 승인 전 Stable 금지.

## 수정·배포 완료 — Atomiswave .7z 게임 미인식 (v0.8.7-beta.2, 2026-11-23)

- **현장 보고:** 기기의 Atomiswave `.7z` 게임이 Windows 스크래퍼 목록에 나타나지 않음.
- **코드에서 확인한 원인:** `core.ROM_EXT`는 `.7z`를 이미 포함했지만 `core.SYSTEM_IDS`에 `atomiswave`가 빠져 있어 게임을 탐색 결과에서 제외했음. `legacy_bridge.PLATFORMS`에도 Skyscraper 매핑이 없어 스크래핑이 불가했음.
- **수정:** `core.py`에 `atomiswave:53` 등록(ScreenScraper ID), `.lst`/`.dat`는 Atomiswave 기종에만 허용. `legacy_bridge.PLATFORMS`에 `atomiswave` 매핑. `gui.py`에 기종명 `Atomiswave`. `.7z/.zip/.chd/.bin`은 기존 일반 확장자 경로로 인식.
- **보호:** `.7z` 압축 ROM의 파일명 변경 금지, 게임 원본 내용 무수정, 기존 한글 이름 유지, XML 자동 백업 생성 금지. KNULLI 게임 실행 문제와 스크래핑 인식 문제는 별개.
- **회귀 테스트:** `tests/test_v087_beta2_atomiswave.py`. 인식, 한글 하위 폴더와 대문자 확장자, Skyscraper `atomiswave` 플랫폼 전달, XML 한글명 보존, 압축 롬 파일명 변경 거부, 다른 기종의 `.dat/.lst` 미인식. Linux POSIX 실셸 시뮬레이션 포함. Windows 테스트 게이트 추가.
- **문서 확인:** Skyscraper 공식 플랫폼 목록과 Batocera/REG Linux Atomiswave 파일 형식으로 대응 방식 확인.
- **구현 및 main 병합 완료:** [PR #5](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/5) (merge SHA `161cad5bf192853eebde30ea63882e6009dec2f3`); 개발 브랜치: `fix/atomiswave-7z-v087-beta2`.
- **베타 릴리즈 및 검증 완료:** [v0.8.7-beta.2 Pre-release](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.2), [GitHub Actions Windows+Linux 테스트 및 배포](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45058337387) 성공. ZIP `KNULLI-Korean-Auto-Scraper-v0.8.7-beta.2-Windows.zip` 90,550 bytes, SHA256 `f6351b7a3d58c567ae3f1b6ff6d8fa72d319beea1cf30b33552312ffb1085649`; `.sha256` 첨부 검증. `prerelease=true` 확인. **다음 작업:** 실제 Windows/RG35XX Plus에서 Atomiswave `.7z` 목록 표시와 Skyscraper 미디어 적용 성공 확인. 기기에서 ROM 게임 실행 가능 여부는 본 스크래퍼 검증 범위 밖.
- **릴리즈 정책:** 사용자 정식 출시 승인 전까지 무조건 Beta; 작업 완료 시 GitHub Release 발행하고 이 HANDOFF 문서 갱신. 이전 `v0.8.6-beta.1`부터 자동 업데이트 기능 탑재.

## 현재 추가 기능 — 삭제된 ROM 연관 데이터 정리 (v0.8.5 베타)
- `main` 통합 완료: PR [#1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/1), 커밋 `f3f8187bd52e740ae362528e329a3552e1b89221`.
- 구현: `orphan_cleanup.py`, GUI 목록 조회 시 누락된 ROM의 XML 자료 확인, 다른 게임이 참조하지 않는 미디어만 후보로 선정, 사용자 확인 후 정리.
- 삭제 전 **XML을 다시 확인하고 ROM이 재등장했는지 검증**. 사용자 요청에 따라 자동 XML 백업 미생성.
- 단독 이미지/영상/매뉴얼 파일은 삭제될 수 있으므로 확인 대화상자를 제공. 미디어와 XML 모두 자동 백업하지 않음.
- ROM 0개 상태도 코드 보완했으나 실기기 확인은 아직 없음. 특수 시스템/파일명·중복 XML 등의 모든 케이스는 미검증.
- **GitHub CI 자동 테스트 통과:** [테스트 실행](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45045628986). **실제 RG35XX Plus 검증 전**, 이미지 삭제는 되돌리기 어렵기 때문에 정리 전 GUI 확인 필수.

## 구현·배포 완료 — 실행 시 자동 베타 업데이트 (v0.8.6-beta.1)

- **사용자 요청:** 프로그램을 실행할 때 최신 GitHub 릴리즈를 자동 검색하고, 새 베타가 있으면 **확인 없이 자동 설치·재시작**.
- `GUI_실행.pyw` 실행 전 `auto_update.try_launch_update()` 호출. `GUI_실행.vbs`는 .pyw 실행, 직접 `python gui.py` 실행도 `__main__`에서 업데이트 검사 수행.
- `app_version.py`의 `VERSION_TAG`와 GitHub Releases API의 공개 베타를 숫자 버전 비교. 정식(Stable)/Draft/태그 오류 제외.
- 릴리즈 Windows ZIP, SHA256 첨부파일, GitHub Release API digest를 검증하고 ZIP 내용/경로/버전도 검사.
- `auto_update_helper.py`를 사용자 데이터 내 임시 폴더에 복사하여 별도 프로세스로 실행. 원래 GUI 프로세스 종료를 대기한 후 앱 파일만 교체하고 재시작. 코드 교체 실패 시 이전 앱 파일 복구 시도. 잠금으로 동시 업데이트 방지.
- `Documents/KNULLI Auto Scraper Data`와 `work` 폴더, ROM, 현재 기기 데이터는 수정하지 않으며 사용자가 수정한 `aliases.json`/`artwork.xml`은 덮어쓰지 않음. 이 과정에서 만드는 일시적인 프로그램 코드 롤백 복사본은 스크래핑 백업이 아니며 정상 완료 시 제거.
- 업데이트 확인/다운로드 실패 시 GUI는 기존 버전으로 실행, 로그는 사용자 데이터 폴더의 `auto_update.log`.
- **초기 배포 한계:** 기존 v0.8.5-beta.2에는 업데이터가 없으므로 v0.8.6-beta.1은 처음 한 번 수동 설치해야 함. 이후부터 실행 시 자동 베타 업데이트.
- [PR #3](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/3) main 병합 완료 (커밋 `6543db6376f54d7fe01da448a3aea5ceb2bcef7d`). [최종 Windows+Linux 릴리즈 검증](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45052031828) 통과. Windows 실제 사용자 프로그램 갱신 과정 미검증.
- **릴리즈 완료 (2026-11-23):** [v0.8.6-beta.1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.6-beta.1) 공개, `prerelease=true`, Windows ZIP(82,651바이트) 및 SHA-256 첨부파일 확인. [GitHub Actions](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45052031828) Windows 업데이터 테스트, Linux 전체 테스트, ZIP 검증, 릴리즈 등록 전 단계 성공.
- **현재 중단 지점 / 다음 작업:** Windows 사용자 PC에서 v0.8.6-beta.1 최초 수동 설치 확인. 후속 베타 릴리즈가 발행되면 업데이트→프로그램 종료→교체→자동 재시작을 실기기에서 검증. 설치 권한/네트워크 오류는 사용자 문서 폴더의 `auto_update.log`로 조사.

## 구현·배포 완료 — PortMaster 게임 스크래핑 (v0.8.7-beta.1)

- 사용자 요청: PortMaster 포팅 게임을 기존 Windows GUI에서 선택하고 정보·이미지를 스크래핑. 테스트와 릴리즈까지 진행.
- **소스:** `core.py` (ports 기종·루트 .sh만 탐색), `portmaster.py` (port.json/gameinfo.xml/cover/screenshot 읽기, 정확한 런처 매칭, XML 누락 필드만 보완), `bundle_engine.py` (Skyscraper 우회), `gui.py` (기종 표기 및 엔진 설치 지연), `orphan_cleanup.py` (실행 파일/폴더 보호).
- **안전:** PortMaster `.sh` 변경 금지, 게임 데이터/세이브 폴더 수정·삭제 금지, 기존 사용자 게임명/설명/이미지 보존, XML 자동 백업 미생성.
- 공식 포트 패키지의 `port.json`과 `gameinfo.xml`을 USB ADB로 읽으며 기기 인터넷이 불필요함. 매칭 근거가 없거나 실행 경로가 모순되면 추측하지 않음.
- `tests/test_v087_portmaster.py`에 한글 .sh, PortMaster 도구 제외, 경로 검증, 기존 정보 보존, 오프라인 gamelist.xml 적용, 중복/오류 케이스 검증.
- [PR #4](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/4) main 병합 완료(커밋 `b4eca62ec58a55be5784546b16927caecc32f18a`). [PortMaster 패키징 문서](https://portmaster.games/contribute/porting/packaging/).
- **릴리즈 완료 (2026-11-23):** [v0.8.7-beta.1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.1) 공개, `prerelease=true`, Windows ZIP 89,599 bytes 및 `.sha256` 첨부 확인. [최종 GitHub Actions](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45056648631)에서 Windows 업데이터·PortMaster 테스트, Linux 회귀 테스트, ZIP 검증, 릴리즈 게시 전 단계 성공.
- **현재 중단 지점 / 다음 작업:** 실제 RG35XX Plus에 설치된 PortMaster 게임의 `port.json`/`gameinfo.xml` 위치를 확인하고 한글·영어 게임명/이미지/설명 적용 및 기존 메타데이터 보존을 실기기에서 재시험. v0.8.6-beta.1 이후 설치본의 자동 업데이트/재시작도 실제 Windows PC에서 확인. 부족한 구조는 후속 베타 릴리즈로 수정.
- 이미 `v0.8.6-beta.1`을 설치한 사용자는 새 베타가 발행되면 다음 실행 시 자동 업데이트를 시도함. 사용자 승인 전 안정(Stable) 버전 불가.

## 릴리즈 운영 규칙 (2026-11-23)
- 사용자는 **작업이 성공적으로 종료될 때마다 GitHub Release 발행**을 요구함. 개발은 릴리즈까지 끝나야 완료임.
- 사용자가 정식 출시를 명시적으로 승인하기 전에는 `vMAJOR.MINOR.PATCH-beta.N` 형식의 **Pre-release**만 가능. 번호는 개발 담당자가 관리.
- 현재 최신 베타: [`v0.8.8-beta.1`](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.8-beta.1). 이전 베타: `v0.8.7-beta.3`. 초기 베타: `v0.8.5-beta.1`.
- 릴리즈는 테스트→배포 ZIP/체크섬 생성→GitHub 사전출시 상태/첨부파일 확인까지 완료해야 성공.
- 절차: [RELEASE_PROCESS.md](RELEASE_PROCESS.md), GitHub Actions `.github/workflows/publish-beta.yml`, 트리거 `release/request.json`.
- **첫 GitHub Beta Release 발행 확인 완료 (2026-11-23):** [v0.8.5-beta.1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.5-beta.1). `prerelease=true`, ZIP(68,614 bytes), `.sha256` 두 첨부 자산 확인. [배포 GitHub Actions](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45046433924)의 테스트·ZIP 빌드·검증·게시·첨부파일 확인 전 단계 성공.
- **릴리즈 확인 완료 (2026-11-23):** [v0.8.5-beta.2](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.5-beta.2) 공개. `prerelease=true` 확인, Windows ZIP(72,525바이트)과 SHA256 파일 모두 첨부됨. [GitHub Actions 배포 실행](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45049288546) 테스트·패키징·검증·릴리즈 게시 성공. **다음 작업은 실기기에서 셸 길이 오류와 이전 앱 백업 정리 결과 확인**. 사용자 승인 전 정식 릴리즈 금지.

## v0.8.7-beta.1 출시 검증 (2026-11-23)

- **릴리즈:** https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.1
- **소스 PR:** https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/4 (병합 완료)
- **GitHub Actions:** https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45056648631 — Windows + PortMaster 테스트, Linux 전체 테스트, 패키징, 체크섬, Pre-release 확인 모두 성공
- **Windows ZIP:** `KNULLI-Korean-Auto-Scraper-v0.8.7-beta.1-Windows.zip` (89,599 bytes)
- **ZIP SHA256:** `c0459a97f9bc6fd5d9cdfef9286c64ee68d01ac3004392d60630ea7334821bef`
- **Beta 상태:** 공개 `prerelease=true`, 정식 출시 승인 없음
- **다음 실기기 검증:** PortMaster 폴더/메타데이터 위치 편차, KNULLI 게임 목록 갱신, 직접 수정한 한글 이름·설명 보존, 전용 런처만 사라졌을 때 XML 정리, 다음 시작 시 자동 업데이트·재시작
- **안전 규칙 유지:** 원본 `.sh`/포트 데이터/세이브 파일 무수정, 기존 메타데이터 보존, 새 XML 스크랩 백업 미생성, 성공한 개발 작업은 새 베타 릴리즈와 인수인계 문서 동시 관리

## 최종 베타 릴리즈 검증 근거

- v0.8.6-beta.1 태그: `bde1d8ad8fb2595dbd9021321c33b967ce6cc3d6`
- ZIP: `KNULLI-Korean-Auto-Scraper-v0.8.6-beta.1-Windows.zip`, 82,651 bytes, SHA256 `f2b3e87f8e8e60414a6e2762e4808a4dde42564d7bf54bec6379770ef79c86e5`
- [릴리즈](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.6-beta.1)에서 Pre-release 및 ZIP/.sha256 첨부 확인
- [릴리즈 GitHub Actions](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45052031828) 성공
- **업데이트 동작은 Windows 테스트 러너에서 검증했지만 실제 사용자 Windows 설치본의 자동 업데이트는 아직 미확인**. v0.8.5-beta.2 사용자는 최초 한 번 수동 설치가 필요.
- 향후 기능 개발 성공 시 `app_version.VERSION_TAG`와 `release/request.json`을 일치시켜 새로운 `beta.N` 릴리즈를 자동 발행. 정식 출시 승인 전까지 stable 배포 금지.

## 현재 중단 지점
**최신 배포 완료: `v0.8.8-beta.1`**. PS1 멀티디스크 자동 통합, 기존/신규 M3U, 게임 정보 보존 및 동의 후 M3U 작성 구현. [릴리즈](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.8-beta.1), [Windows + Linux CI](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45147929620) 검증 성공. **다음 작업:** 실제 RG35XX Plus에서 2장 이상의 게임 파일로 M3U 작성, 게임 목록 중복 숨김, 디스크 교체, 게임 실행·세이브 호환성, 스크래핑 메타데이터 적용을 검증. 기기에 있는 ROM·세이브 파일을 변경하거나 삭제하지 않는 정책 및 XML 영구 백업 미생성 정책 유지. 실제 기기 성공 여부는 아직 미확인.

## 이어서 할 일 (우선순위)
1. [완료] 원본 v0.8.4의 모든 소스 파일을 저장소 루트에 복원. 압축 스냅샷 SHA256 확인. 
2. [완료] GitHub CI에서 **복원 후 코드** 기준 단위 테스트 성공. 초기 이식 중 코드 없는 커밋의 실패와 구분할 것. [성공 실행](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/44666745166). Windows GUI 및 ADB 사용의 실제 제약 문서화는 다음 작업.
3. 사용자 실기기에서 v0.8.5 정리 기능을 소량 시험하고, v0.8.4 한글 하위 폴더 오류 재시험 결과 수집. 실패하면 기기 로그/last_report.json 기반 원인 수정.
4. 타이틀 화면(ssTitle) 미지원 문제 검토. 현재 Windows Skyscraper 3.6.12 수집 경로에서 지원/검증되지 않음.
5. 속도·안정성 개선. 게임별 GUI 갱신, 큰 ROM 전송 최소화, 검색 결과 캐시. 스크래핑 API 한도 준수.
6. 사용자에게 정리된 리포트/릴리스 전달.

## 새로운 대화에서 작업할 때 필수 순서
1. GitHub `README.md` → `docs/HANDOFF.md` → `docs/DECISIONS.md` → `docs/KNOWN_ISSUES.md` 확인.
2. `main` 최신 코드를 먼저 읽고, 사용자 요청만으로 이전 대화 버전을 추정하지 말 것.
3. 코드 수정은 테스트·검증을 수행하고, 임의로 이전 정상 기능 제거하지 말 것.
4. 작업마다 이 문서의 현재 상태/중단 지점/다음 할 일과 CHANGELOG·ROADMAP을 같은 변경 묶음에서 갱신.
5. 실제 GitHub 커밋/PR 링크와 테스트 결과를 보고하고, 실기기 미검증은 명시.

## 안전 및 보안
- ROM/BIOS, ScreenScraper 비밀번호, `config.json`, `work/`, 실기기 덤프/로그를 GitHub에 올리지 말 것.
- KNULLI OS 내부 변경, EmulationStation 강제 재시작, `adb kill-server` 금지.
- v0.8.5-beta.2부터 자동 XML 백업 생성 금지(사용자 명시 요청). 변경 전 동시 수정 검사 및 원본 ROM 보호는 유지. 앱 전용 옛 백업만 삭제.


## v0.8.5-beta.2 개발 기록 (2026-11-23)
- 사용자 실기기 오류: `삭제된 게임 검사 실패: ADB shell failed: error: shell command too long`.
- 원인: 한글 경로를 인코딩한 상태에서 12개씩 묶어 ADB 셸 명령 한계를 초과. `orphan_cleanup._path_states`를 바이트 길이 예산 기반 분할과 길이 오류 재분할로 변경, 한 번 인코딩한 경로를 셸 변수로 재사용. 검사 오류는 ROM 부재로 간주하지 않음.
- 사용자는 **프로그램이 만든 스크래핑 데이터(XML) 백업의 신규 생성 금지 및 기존 것 삭제**를 명확히 요청함. ROM 원본·이미지·영상·현재 XML·설정·사용자 개인 백업은 보존.
- `manager.py`, `backend.py`, `bundle_engine.py`, `orphan_cleanup.py` 백업 작성 코드를 제거. 기존 rename_journal은 데이터 백업이 아닌 작업 상태 기록이므로 유지.
- 신규 `backup_cleanup.py`: 연결된 기기에서 `gamelist.xml.knulli-autoscraper-<timestamp>.bak`만 삭제. PC에서는 현재 설치 및 검증된 같은 상위 폴더의 이전 설치본 `work/xml_backups/<system>_<timestamp>.xml`만 삭제. 임의 전체 디스크 검색 금지.
- [PR #2](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/2) main 병합 완료. [최종 릴리즈 CI](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45049288546) 성공, 85개 테스트 통과.
- **실기기 검증 전**이며 자동 백업이 없어서 예기치 못한 XML 손상 시 사용자 복구 선택지가 적음.
- **완료 상태:** v0.8.5-beta.2 배포 확인. 다음 대화에서는 GitHub에서 main/HANDOFF 확인 후 실기기 피드백을 근거로 개선을 진행하고, 성공 시 새 베타 릴리즈까지 발행할 것.
