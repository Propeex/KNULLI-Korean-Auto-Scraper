# 개발 인수인계 / 다음 대화의 시작점

> **이 문서를 가장 먼저 읽으세요.** GitHub 저장소가 프로젝트의 단일 기준(source of truth)입니다. 대화의 기억이나 이전 ZIP 링크보다 저장소의 코드·문서·커밋을 우선합니다.

## 기준 상태
- 작성일: 2026-11-20 (Asia/Seoul)
- 프로젝트: KNULLI Korean Auto Scraper
- 저장소: https://github.com/Propeex/KNULLI-Korean-Auto-Scraper
- **개발 중인 다음 버전: `v0.8.5-beta.2` (Beta/Pre-release).** 기존 공개 버전은 `v0.8.5-beta.1`.  최초 이식 소스 기준: **v0.8.4 베타** (`knulli_auto_scraper_adb_v084_unicode_folders.zip`)
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

## 현재 추가 기능 — 삭제된 ROM 연관 데이터 정리 (v0.8.5 베타)
- `main` 통합 완료: PR [#1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/1), 커밋 `f3f8187bd52e740ae362528e329a3552e1b89221`.
- 구현: `orphan_cleanup.py`, GUI 목록 조회 시 누락된 ROM의 XML 자료 확인, 다른 게임이 참조하지 않는 미디어만 후보로 선정, 사용자 확인 후 정리.
- 삭제 전 **XML을 다시 확인하고 ROM이 재등장했는지 검증**. 사용자 요청에 따라 자동 XML 백업 미생성.
- 단독 이미지/영상/매뉴얼 파일은 삭제될 수 있으므로 확인 대화상자를 제공. 미디어와 XML 모두 자동 백업하지 않음.
- ROM 0개 상태도 코드 보완했으나 실기기 확인은 아직 없음. 특수 시스템/파일명·중복 XML 등의 모든 케이스는 미검증.
- **GitHub CI 자동 테스트 통과:** [테스트 실행](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45045628986). **실제 RG35XX Plus 검증 전**, 이미지 삭제는 되돌리기 어렵기 때문에 정리 전 GUI 확인 필수.

## 릴리즈 운영 규칙 (2026-11-23)
- 사용자는 **작업이 성공적으로 종료될 때마다 GitHub Release 발행**을 요구함. 개발은 릴리즈까지 끝나야 완료임.
- 사용자가 정식 출시를 명시적으로 승인하기 전에는 `vMAJOR.MINOR.PATCH-beta.N` 형식의 **Pre-release**만 가능. 번호는 개발 담당자가 관리.
- 현재 최초 베타: `v0.8.5-beta.1`, [릴리즈 페이지](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.5-beta.1).
- 릴리즈는 테스트→배포 ZIP/체크섬 생성→GitHub 사전출시 상태/첨부파일 확인까지 완료해야 성공.
- 절차: [RELEASE_PROCESS.md](RELEASE_PROCESS.md), GitHub Actions `.github/workflows/publish-beta.yml`, 트리거 `release/request.json`.
- **첫 GitHub Beta Release 발행 확인 완료 (2026-11-23):** [v0.8.5-beta.1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.5-beta.1). `prerelease=true`, ZIP(68,614 bytes), `.sha256` 두 첨부 자산 확인. [배포 GitHub Actions](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45046433924)의 테스트·ZIP 빌드·검증·게시·첨부파일 확인 전 단계 성공.
- **현재 중단 지점:** v0.8.5-beta.2 수정 PR #2의 CI/병합 및 GitHub Beta Release 발행을 완료해야 함. 실기기에서는 셸 길이 오류와 이전 백업 삭제 결과를 재검증해야 함. 사용자 명시 승인 전까지 모든 후속 릴리즈는 Beta/Pre-release.

## 현재 중단 지점
**v0.8.5 베타를 main에 통합 완료.** v0.8.4를 기반으로 삭제된 ROM의 XML·단독 미디어 정리 기능을 추가. 기존 GUI/스크래퍼와 인수인계 문서는 유지. **최신 코드 기준 GitHub Actions CI 성공**: [Python tests run](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/44666745166). 다음 작업은 v0.8.5 정리 기능의 Windows/실기기 안전성 검증, 마지막 한글 하위 폴더 문제 재시험. 이식은 v0.8.4를 기준선으로 만들었으며, 후속 v0.8.5 기능은 PR #1에서 추가함.

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
- [PR #2](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/2), [테스트 성공 기록](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45048905011), 85개 테스트 통과. 단, 변경 후 문서 최종 업데이트 시 CI 재확인 필요.
- **실기기 검증 전**이며 자동 백업이 없어서 예기치 못한 XML 손상 시 사용자 복구 선택지가 적음.
- 이 문서는 다음 대화에서 기준점으로 사용하며, 최종 릴리즈가 성공하면 이 단락의 공개 버전/중단 상태를 최신으로 바꿀 것.
