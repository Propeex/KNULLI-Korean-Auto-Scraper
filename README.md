# KNULLI Korean Auto Scraper

Windows에서 USB ADB로 **RG35XX Plus / KNULLI**의 ROM을 직접 탐색하고, 한국어 파일명·표시명을 보존하면서 ScreenScraper 자료를 수집·적용하는 데스크톱 앱입니다.

> **현재 공개 베타:** [`v0.8.7-beta.1`](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.1) (2026-11-23). 이전 베타는 `v0.8.6-beta.1`입니다. 기반 소스는 v0.8.4이며, 기존 스크래핑 기능에 삭제된 ROM 관련 자료 정리 기능을 추가했습니다. 자동 테스트는 통과했지만 이 기능의 실제 기기 검증은 아직 필요합니다.

## 최신 Windows 베타 다운로드

[**GitHub Releases — v0.8.7-beta.1**](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.1)에서 Windows ZIP과 SHA-256 검사 파일을 받으세요. 이 패키지는 독립 실행 EXE가 아니라 **Python GUI 소스 패키지**이며, Windows에 Python 3.10+가 필요합니다.

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
4. 앱은 ADB를 확인하며 필요 시 설치를 시도합니다. **일반 ROM 스크래핑을 선택한 경우에만** Windows용 Skyscraper를 확인·설치합니다. PortMaster-only 작업은 Skyscraper가 필요 없습니다.
5. ROM 목록에서 게임을 선택한 뒤 `작업 시작`을 누릅니다.

공식 개발자 API ID를 요구하지 않는 Skyscraper 기반입니다. 일반 ScreenScraper 계정은 설정에서 입력합니다.

## 중요한 규칙

- 원본 ROM의 실제 파일 내용은 절대로 스크래핑 과정에서 변경하지 않습니다.
- 일반 ROM의 **한글 파일명 및 KNULLI 한글 표시명**을 유지합니다.
- ROM 세트 이름이 중요한 아케이드 ZIP은 실제 이름을 보호하고 **표시명만** 바꿉니다.
- 영문명은 **검색 전용 데이터**이며 KNULLI 표시명을 덮어쓰지 않습니다.
- 기존 `gamelist.xml`과 자원은 유효성·변경 여부를 재검증하고 함부로 덮어쓰지 않습니다. **새 XML 백업은 생성하지 않습니다.**
- KNULLI OS 파일 수정, 강제 EmulationStation 재시작, `adb kill-server`를 하지 않습니다.
- ScreenScraper 계정 비밀번호, 실제 게임 ROM, 설정·캐시·작업 로그를 저장소에 올리지 않습니다.

## 삭제한 ROM의 관련 데이터 정리 (v0.8.5 베타)

ROM을 사용자가 기기에서 삭제한 뒤 프로그램이 다음에 목록을 조회하면, `gamelist.xml`에서 해당 게임을 찾고 기기에서 ROM이 정말 없는지 재확인합니다. 정리할 게임과 자원 수를 미리 보여주고 **동의할 때만** 정리합니다. **XML 백업은 생성하지 않으며**, 다른 게임이 함께 사용하는 이미지·영상 등은 삭제하지 않습니다. 실제 ROM은 삭제하지 않습니다.

오류나 불분명한 경로는 정리 대상으로 취급하지 않으며, 기기에서 목록을 다시 읽어 확인합니다. 정리 결과는 PC의 `work/last_cleanup.json`에 기록됩니다. 이 기능은 사용자 실기기에서 아직 검증 전입니다.

## 자동 스크래핑 백업 정리 및 ADB 검사 제한 수정 (v0.8.5-beta.2)

사용자 요청에 따라 스크래핑과 이름·설명·XML 동기화, 삭제된 게임 정리 과정에서 **새로운 gamelist.xml 백업을 만들지 않습니다.** 앱 연결 시 이전 버전에서 생성한 `gamelist.xml.knulli-autoscraper-<timestamp>.bak` 파일을 기기 시스템 폴더에서 정리합니다. PC에서는 현재 설치 폴더 및 **같은 상위 폴더에 있는 검증된 이전 설치본**의 `work/xml_backups/<system>_<timestamp>.xml`만 삭제합니다. 다른 위치에 보관한 구버전 프로그램의 백업은 임의 검색하지 않습니다. ROM 원본·이미지/동영상·현재 XML·사용자 설정·개인 백업은 대상에서 제외됩니다.

한글 경로 검사에 사용되는 ADB 셸 명령은 길이에 따라 나눠 실행합니다. 길이 오류가 지속되거나 결과가 불완전하면 게임이 삭제된 것으로 잘못 판단하지 않고 정리를 중단합니다.

**주의:** 백업이 생성되지 않으므로 예기치 못한 USB 연결 끊김/기기 오류 시 복구 선택지가 줄어듭니다. 중요한 기기 데이터는 사용자가 별도로 관리해야 합니다.

## 시작 시 자동 업데이트 (v0.8.6-beta.1)

Windows에서 `GUI_실행.pyw` 또는 `GUI_실행.vbs`를 실행하면 앱 시작 전에 GitHub의 **공개 베타(Pre-release) 목록**을 확인합니다. 현재 버전보다 높은 베타가 있으면 별도 확인 창 없이 Windows ZIP을 다운로드하여 SHA-256과 패키지 내부 파일을 검사합니다. 이후 기존 앱을 종료하고 별도 도우미로 프로그램 파일을 교체한 뒤 **새 버전을 자동 재실행**합니다. 인터넷이 없거나 업데이트 검사에 실패하면 기존 버전으로 실행합니다.

**최초 1회 설치:** 이전 `v0.8.5-beta.2`에는 자동 업데이트 기능이 없으므로, 이 `v0.8.6-beta.1`은 릴리즈 ZIP을 직접 설치해야 합니다. 이후 새 베타부터 자동 업데이트됩니다. 사용자 승인 전까지 안정(Stable) 릴리즈로 자동 전환하지 않습니다.

사용자 설정(`Documents/KNULLI Auto Scraper Data`), 스크래핑 데이터, ROM, 기기의 XML과 기존 사용자가 수정한 `aliases.json`·`artwork.xml`은 업데이트 도중 변경하지 않습니다. 일시적 코드 롤백 파일은 스크랩 데이터 백업이 아닙니다. 실패 내역은 사용자 데이터 폴더의 `auto_update.log`에 기록합니다. 업데이트 실패 후에는 기존 앱을 실행하도록 설계했습니다. Windows 실기기 업데이트 동작은 별도 확인이 필요합니다.

## PortMaster 포팅 게임 지원 (v0.8.7-beta.1)

KNULLI의 `/userdata/roms/ports/` 최상위 `.sh` 게임 실행 스크립트도 기종 **PortMaster**로 표시합니다. `PortMaster.sh` 및 설치·관리용 스크립트는 제외하고, 게임 데이터 폴더를 재귀적으로 훑지 않습니다. 원하는 포트 게임을 체크하여 **작업 시작**하면, 포트 폴더의 `port.json`과 `gameinfo.xml` (게임명·설명·장르·제작사·출시일 등), 기존 `cover.png/.jpg`·`screenshot.png/.jpg`를 조회해 KNULLI의 `ports/gamelist.xml`에서 **비어 있는 항목만** 채웁니다. 정보 우선순위는 `gameinfo.xml` → `port.json`; 명시적 실행 파일 매칭이 없는 게임은 추측하지 않습니다.

이 작업은 **ScreenScraper/Skyscraper 및 포트 게임 파일 복사가 필요 없고**, 기기 자체 인터넷도 필요 없습니다. 이미 사용자가 지정한 표시명·설명·이미지는 덮어쓰지 않으며, `.sh` 실행 스크립트, 포트 본체, 게임 데이터·세이브 파일은 수정하지 않습니다. 예전부터 요청하신 규칙대로 XML 백업도 만들지 않습니다. 삭제된 포트 게임은 기존 사용자 확인 절차에서 **사라진 런처의 XML 게임 항목만** 정리하고 포트 폴더/세이브는 삭제하지 않습니다.

**제한:** PortMaster가 인식되는 게임이라도 로컬 `port.json`/`gameinfo.xml`가 없거나 런처와 연결되지 않으면 자동으로 제목을 추측하지 않습니다. 직접 넣은 사용자 제작 `.sh` 포트도 마찬가지입니다. 실제 RG35XX Plus의 다양한 포트 설치 방식은 실기기 검증 전입니다. [PortMaster 공식 포트 패키징 문서](https://portmaster.games/contribute/porting/packaging/).

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
