# 개발 인수인계 / 다음 대화의 시작점

> **이 문서를 가장 먼저 읽으세요.** GitHub 저장소가 프로젝트의 단일 기준(source of truth)입니다. 대화의 기억이나 이전 ZIP 링크보다 저장소의 코드·문서·커밋을 우선합니다.

## 기준 상태
- 작성일: 2026-11-20 (Asia/Seoul)
- 프로젝트: KNULLI Korean Auto Scraper
- 저장소: https://github.com/Propeex/KNULLI-Korean-Auto-Scraper
- 최초 소스 기준: **v0.8.4 베타** (`knulli_auto_scraper_adb_v084_unicode_folders.zip`)
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
- 성공 후 KNULLI gamelist.xml의 한글 표시명 동기화, 기존 XML 백업
- 계정 정보는 Windows 자격 증명 관리자, 검색 사전은 사용자 문서 폴더에 보관
- Skyscraper 기반 검색/적용. 별도 개발자 API ID는 요구하지 않음
- 완료된 게임은 전체 작업 종료 전에 미리보기 조회 가능(편집은 작업 중 잠금)
- ADB/Skyscraper 자동 검색·설치 시도

## 마지막 확인된 문제와 수정
- v0.8.3에서 한글 하위 폴더 `psx/한글 폴더/Silent Hill (K).cue`의 경로가 `????`로 깨져 `remote file size unavailable` 발생.
- v0.8.4에서 기기 경로를 바이트/NUL 구분 + 영숫자 인코딩으로 PC에 전달, 파일 크기 조회의 인코딩 개선.
- **단위 테스트는 통과했지만 이 v0.8.4 수정의 실기기 성공 피드백은 아직 받지 못함.**

## 현재 중단 지점
**GitHub 최초 이식 완료(v0.8.4).** GUI/스크래퍼 Python 소스와 60개 테스트, README, 개발 계획/결정/알려진 문제 문서가 `main`에 업로드됨. 다음 작업은 **최신 코드 기준 CI 테스트 상태 확인**, Windows/실기기 기능 검증, 마지막 한글 하위 폴더 문제 재시험. 이식은 새로운 기능 추가가 아닌 기존 상태 기준선 확립.

## 이어서 할 일 (우선순위)
1. [완료] 원본 v0.8.4의 모든 소스 파일을 저장소 루트에 복원. 압축 스냅샷 SHA256 확인. 
2. [진행/확인 필요] GitHub CI에서 **복원 후 코드** 기준 단위 테스트 통과 확인. 이식 중 임시 코드 없는 커밋에서 발생한 실패와 구분할 것. Windows GUI 및 ADB 사용의 실제 제약 문서화.
3. 사용자 실기기에서 v0.8.4 한글 하위 폴더 오류 재시험 결과 수집. 실패하면 기기 로그/last_report.json 기반 원인 수정.
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
- 저장/변경 전 기존 `gamelist.xml` 백업과 오류 발생 시 원본 보존.
