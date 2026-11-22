# KNULLI Korean Auto Scraper v0.8.7 Beta 1

**Windows / RG35XX Plus / KNULLI / USB ADB**

> 이 버전은 **Beta / Pre-release**입니다. 자동 테스트는 통과했지만 실제 RG35XX Plus에서 PortMaster 게임 폴더·메타데이터 구조는 추가 검증이 필요합니다.

## 새 기능 — PortMaster 포팅 게임 메타데이터

- `/userdata/roms/ports/`에 설치된 **최상위 `.sh` 게임 실행 스크립트**를 기존 GUI의 게임 목록에서 `PortMaster` 기종으로 표시합니다.
- PortMaster 설치/관리 도구 스크립트는 게임 목록에서 제외하며, 포트 게임의 방대한 데이터 디렉터리를 ROM으로 재귀 탐색하지 않습니다.
- 선택한 게임에 대해 로컬 `port.json`·`gameinfo.xml`을 읽어 **게임명, 설명, 장르, 개발사, 배급사, 출시일** 등을 보완합니다. `gameinfo.xml` 정보가 우선합니다.
- 이미 설치된 `cover.png/.jpg`·`screenshot.png/.jpg`를 새로 복사하지 않고 `ports/gamelist.xml`의 이미지 경로로 연결합니다.
- 게임과 메타데이터에 **명시적으로 같은 실행 스크립트가 연결된 경우에만** 적용하며, 이름을 추측하여 엉뚱한 게임으로 매칭하지 않습니다.
- 기존 사용자의 한글 게임명, 수동 설명 및 이미지 등은 **덮어쓰지 않습니다**. 비어 있는 XML 필드만 작성합니다.
- PortMaster 게임만 선택했다면 Skyscraper/ScreenScraper가 필요 없고, 기기 인터넷도 요구하지 않습니다.

## 파일 안전성

- 포트의 `.sh` 실행 파일, 게임 데이터, 게임 세이브, 설치 파일은 수정/삭제하지 않습니다.
- 삭제된 포트 게임의 정보 정리는 기존 사용자 확인 후 **해당 XML 게임 항목만** 삭제하며 포트 폴더를 제거하지 않습니다.
- 이전에 확정한 정책대로 **스크랩 데이터 XML 백업을 만들지 않습니다**.
- 로컬 메타데이터가 없거나 형식이 달라 매칭할 수 없다면 안전하게 검색 실패로 표시하고 다른 게임 정보를 적용하지 않습니다.

## 설치 및 자동 업데이트

- 이전 `v0.8.6-beta.1` 이상 설치본은 프로그램을 시작할 때 이 공개 베타 릴리즈를 검색하고, 승인 창 없이 검증·자동 설치한 다음 재시작하도록 설계되어 있습니다.
- 수동 설치를 원하면 Windows ZIP을 받아 기존 ZIP 설치 파일이 있는 폴더가 아닌 별도 새 폴더에 풀고 `GUI_실행.pyw`로 시작하세요.
- **Python 3.10 이상과 Tkinter**가 필요합니다. 독립 실행 EXE는 아닙니다.
- 사용자 설정은 Windows 사용자 문서 폴더에 저장되며 릴리즈 업데이트 시 보존됩니다.

## 검증 및 제한

- GitHub Actions에서 Linux 전체 단위/GUI 테스트와 Windows 업데이터 테스트, 릴리즈 ZIP/체크섬 검증 후 배포합니다.
- 추가 PortMaster 테스트에서 한글 `.sh` 경로, 관리 스크립트 제외, XML 필드 우선순위, 사용자 편집 내용 보호, 포트 데이터 무변경, 메타데이터 오류/경로 충돌을 확인합니다.
- **실제 기기에서 PortMaster 메타데이터가 다른 위치에 저장된 경우** 자동 적용되지 않을 수 있습니다. 이 경우 설치된 포트 폴더 구조를 확인해 후속 베타에서 대응합니다.

개발 변경: [PR #4](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/4).
자료 형식: [PortMaster 공식 포트 패키징 문서](https://portmaster.games/contribute/porting/packaging/).

정식 출시 승인이 있기 전까지 모든 릴리즈는 Beta / Pre-release입니다.
