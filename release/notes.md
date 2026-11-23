# KNULLI Korean Auto Scraper v0.8.8 Beta 1

**Windows / RG35XX Plus / KNULLI / USB ADB**

> **Beta / Pre-release**입니다. Windows/Linux 자동 테스트는 통과했지만 실제 RG35XX Plus에서의 PS1 디스크 교체와 게임 목록 표시 결과는 실기기 확인이 필요합니다.

## 신규 기능 — PS1 멀티디스크 자동 인식 및 M3U 생성

- 드래곤 퀘스트 7처럼 `(Disc 1)`과 `(Disc 2)`가 같은 폴더에 있는 게임은 **하나의 게임 항목**으로 표시합니다. `Disk`, `CD`, `디스크` 표기도 인식합니다.
- 디스크 번호가 1부터 연속하고 중복되지 않을 때만 자동 그룹으로 처리합니다. 구분이 모호하거나 디스크가 누락되면 추측하지 않습니다.
- 기존의 유효한 `.m3u`가 있다면 재생목록 하나를 대표 게임으로 조회하고, 그 안에 참조된 개별 디스크는 중복으로 표시하지 않습니다.
- `.m3u`가 아직 없는 게임은 상단 **[멀티디스크 묶기]** 버튼을 누른 다음 확인하면 실제 KNULLI 기기에 작은 M3U 파일을 생성합니다. **조회만 할 때는 파일을 생성하지 않습니다.**
- 새로운 M3U는 기존 디스크 파일의 **상대 경로를 순서대로** 포함하며 기존 같은 이름의 파일을 덮어쓰지 않습니다.
- 기존 Disc 1에 등록된 **게임명·한글 설명·이미지 경로** 등 메타데이터를 새 M3U용 `gamelist.xml` 항목에 복사합니다. 기존 Disc 1 XML 항목은 삭제하지 않습니다.
- M3U 게임 스크래핑은 디스크 전체 해시 대신 **게임명 검색**으로 실행해 한 게임에 한 번 적용합니다.

## 파일 보존

- 원본 `.chd`/`.cue`/`.iso` 등의 디스크, 게임 세이브, 메모리카드는 수정·이동·삭제하지 않습니다.
- `.m3u`가 이미 있으면 덮어쓰지 않습니다. 새 파일을 만들기 전 디스크들이 실제로 존재하는지 재확인합니다.
- 이전 사용자 요청대로 `gamelist.xml`의 영구 백업을 만들지 않습니다.
- 설치 폴더의 사용자 설정과 기존 자동 업데이트 기능은 유지합니다.

## 기기에서 중복 디스크를 숨기는 방법

KNULLI 메인 메뉴에서 다음을 확인하세요.

1. **START → SYSTEM SETTINGS → FRONTEND DEVELOPER OPTIONS**
2. **Ignore Multi-File Disk Content (CUE/GDI/CCD/M3U)** 켜기
3. **GAME SETTINGS → UPDATE GAMELISTS** 실행

공식 설명: [KNULLI Multi-Disc Games](https://knulli.org/configure/multi-disc-games/).

## 지원 범위

- `roms/psx`와 그 게임별 하위 폴더의 `.m3u` 및 Disc 1..N 세트를 지원합니다.
- 서로 다른 폴더에 흩어진 디스크는 **기존 M3U가 안전한 상대 경로로 연결한 경우에만** 자동 통합 표시합니다. 이런 경우 M3U를 신규 자동 생성하지는 않습니다.
- 유효하지 않거나 파일을 찾을 수 없는 M3U는 실제 디스크를 잘못 숨기지 않습니다.
- 실기기에서 KNULLI 화면 표시와 디스크 교체는 추가 확인이 필요합니다.

## 설치 및 업데이트

- 기존 `v0.8.6-beta.1` 이상 사용자는 다음 프로그램 실행 시 새 베타를 자동 확인·적용·재시작하도록 되어 있습니다.
- 수동 설치: 아래 Windows ZIP 압축 해제 후 `GUI_실행.pyw` 실행.
- **Python 3.10 이상 + Tkinter**가 필요하며 독립 실행 EXE는 아닙니다.
- ROM·BIOS 파일은 배포에 포함되지 않습니다.

## 검증

Windows/Linux 회귀 테스트에서 기존 M3U 읽기, 한글 Disc 1·2 자동 그룹, 여러 디스크 순서, 잘못된 M3U 안전 처리, 신규 파일 작성 및 기존 XML/세이브 보존을 확인했습니다. GitHub Actions 릴리즈 ZIP·SHA256 검사 이후 게시합니다.

개발 기록: [PR #7](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/7).
사용자의 명시적인 정식 출시 승인이 있기 전까지 모든 버전은 Beta / Pre-release입니다.
