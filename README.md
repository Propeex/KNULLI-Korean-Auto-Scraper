# KNULLI Korean Auto Scraper

Windows에서 USB ADB로 **RG35XX Plus / KNULLI**의 ROM을 직접 탐색하고, 한국어 파일명·표시명을 보존하면서 ScreenScraper 자료를 수집·적용하는 데스크톱 앱입니다.

> **현재 베타 릴리즈:** `v0.8.5-beta.1` (2026-11-23). 기반 소스는 v0.8.4이며, 기존 스크래핑 기능에 삭제된 ROM 관련 자료 정리 기능을 추가했습니다. 자동 테스트는 통과했지만 이 기능의 실제 기기 검증은 아직 필요합니다.

## 최신 Windows 베타 다운로드

[**GitHub Releases — v0.8.5-beta.1**](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.5-beta.1)에서 Windows ZIP과 SHA-256 검사 파일을 받으세요. 이 패키지는 독립 실행 EXE가 아니라 **Python GUI 소스 패키지**이며, Windows에 Python 3.10+가 필요합니다.

배포 규칙: [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md). 사용자가 정식 출시를 승인하기 전에는 모든 버전을 **Pre-release / Beta**로 발행합니다.

## 다른 대화에서 이어서 개발하기

**가장 먼저 [docs/HANDOFF.md](docs/HANDOFF.md)를 읽으세요.** 그 문서는 현재 기준 버전, 목표, 완료한 일, 최신 중단 지점, 확인해야 할 문제, 다음 행동을 기록합니다.

작업 중에는 다음을 함께 갱신합니다.

- [docs/HANDOFF.md](docs/HANDOFF.md) — 최신 상태와 다음 작업
- [docs/ROADMAP.md](docs/ROADMAP.md) — 계획·우선순위·완료 조건
- [docs/DECISIONS.md](docs/DECISIONS.md) — 사용자와 합의한 절대 규칙 및 기술 결정
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — 버전별 이력
- [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) — 제한·미해결 문제
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 구현 구조·테스트·위험

## 실행

1. 기존 USB ADB 연결이 동작하는지 확인합니다. **기기 인터넷은 필요 없고 PC 인터넷만 필요**합니다.
2. Windows에 Python 3.10 이상과 Tkinter를 준비합니다.
3. `GUI_실행.pyw`를 실행합니다. 대체 실행기는 `GUI_실행.vbs`입니다.
4. 앱은 ADB / Windows용 Skyscraper를 찾거나, 없으면 공식 배포 파일을 설치하려고 시도합니다.
5. ROM 목록에서 게임을 선택한 뒤 `작업 시작`을 누릅니다.

공식 개발자 API ID를 요구하지 않는 Skyscraper 기반입니다. 일반 ScreenScraper 계정은 설정에서 입력합니다.

## 중요한 규칙

- 원본 ROM의 실제 파일 내용은 절대로 스크래핑 과정에서 변경하지 않습니다.
- 일반 ROM의 **한글 파일명 및 KNULLI 한글 표시명**을 유지합니다.
- ROM 세트 이름이 중요한 아케이드 ZIP은 실제 이름을 보호하고 **표시명만** 바꿉니다.
- 영문명은 **검색 전용 데이터**이며 KNULLI 표시명을 덮어쓰지 않습니다.
- 기존 `gamelist.xml`·자원은 백업하고, 불확실한 결과는 함부로 적용하지 않습니다.
- KNULLI OS 파일 수정, 강제 EmulationStation 재시작, `adb kill-server`를 하지 않습니다.
- ScreenScraper 계정 비밀번호, 실제 게임 ROM, 설정·캐시·작업 로그를 저장소에 올리지 않습니다.

## 삭제한 ROM의 관련 데이터 정리 (v0.8.5 베타)

ROM을 사용자가 기기에서 삭제한 뒤 프로그램이 다음에 목록을 조회하면, `gamelist.xml`에서 해당 게임을 찾고 기기에서 ROM이 정말 없는지 재확인합니다. 정리할 게임과 자원 수를 미리 보여주고 **동의할 때만** 정리합니다. 원본 `gamelist.xml`은 PC와 기기에 백업하고, 다른 게임이 함께 사용하는 이미지·영상 등은 삭제하지 않습니다. 실제 ROM은 삭제하지 않습니다.

오류나 불분명한 경로는 정리 대상으로 취급하지 않으며, 기기에서 목록을 다시 읽어 확인합니다. 정리 결과는 PC의 `work/last_cleanup.json`에 기록됩니다. 이 기능은 사용자 실기기에서 아직 검증 전입니다.

## 테스트

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Linux 헤드리스 환경에서는 Tk GUI 테스트에 Xvfb가 필요합니다.

```bash
xvfb-run -a python -m unittest discover -s tests -p 'test_*.py'
```

**이식 전 소스 검증:** 2026-11-20, Python 3.13 / Xvfb에서 60개 테스트 통과. Windows + 실기기 + ScreenScraper 연동 테스트는 별도로 수행해야 합니다.

## 출처

최초 이식 소스는 이 대화에서 제작된 `knulli_auto_scraper_adb_v084_unicode_folders.zip`입니다. 원본 ZIP 구조의 파일은 저장소 루트에 배치합니다. 제3자 ADB / Skyscraper 바이너리와 ROM은 포함하지 않습니다.

- KNULLI: https://knulli.org/
- ScreenScraper: https://www.screenscraper.fr/
- Skyscraper: https://github.com/muldjord/skyscraper
- Android Platform-Tools: https://developer.android.com/tools/releases/platform-tools
