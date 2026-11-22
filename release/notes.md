# KNULLI Korean Auto Scraper v0.8.7 Beta 2

**Windows / RG35XX Plus / KNULLI / USB ADB**

> 이번 버전은 **Beta / Pre-release**입니다. GitHub 자동 테스트는 수행하지만 실제 사용자 RG35XX Plus에서 Atomiswave .7z 인식·스크래핑은 별도 검증이 필요합니다.

## 수정 내용 — Atomiswave .7z 게임 인식

- 이전에는 `.7z` 파일이 허용 목록에 있어도 **`atomiswave` 시스템 폴더 자체가 누락**되어 게임 목록에 나타나지 않았습니다.
- 이제 `/userdata/roms/atomiswave/` 및 그 하위 폴더에 있는 `.7z`, `.zip`, `.chd`, `.bin`, `.lst`, `.dat` 게임을 검색합니다.
- Skyscraper `atomiswave` 플랫폼 / ScreenScraper 시스템 ID `53`을 연결했습니다.
- GUI 기종 열에 **Atomiswave**로 표시합니다.
- 한글 게임/폴더 이름, 대문자 `.7Z` 확장자를 지원합니다.

## 기존 안전 정책 유지

- `.7z` 등 압축 ROM의 파일명이나 원본 내용을 변경하지 않습니다. 사용자 지정 게임명과 기존 메타데이터는 가능한 한 보존합니다.
- 사용자 요청대로 게임 정보 XML 자동 백업을 생성하지 않습니다.
- 사용자 설정과 스크래핑 캐시는 기존 상태를 유지합니다.
- 이전 베타부터 제공되는 시작 시 자동 업데이트 및 자동 재시작 기능이 유지됩니다.

## 설치와 업데이트

- 이미 `v0.8.6-beta.1` 이상의 자동 업데이트 지원 버전을 쓰고 있다면 **다음 실행 때 공개 베타를 조회·적용**하도록 구현되어 있습니다.
- 수동 설치는 이 릴리즈의 Windows ZIP을 다운로드해 압축 해제한 후 `GUI_실행.pyw`로 시작하면 됩니다.
- Windows **Python 3.10 이상 + Tkinter**가 필요합니다. 독립 실행 EXE는 아닙니다.
- KNULLI 기기 인터넷 연결은 불필요하며 PC의 인터넷과 USB ADB를 사용합니다.

## 검증

- 자동 테스트: Atomiswave 파일 인식·한글 중첩 폴더·Skyscraper 플랫폼 매핑, 원본 압축 ROM 보호, 기존 한글 XML 표시명 보존.
- GitHub Actions에서 Windows와 Linux 테스트를 통과한 경우에만 ZIP·SHA-256 확인 파일을 첨부합니다.
- **실제 기기 테스트는 미완료**입니다. 이 수정은 게임 목록/메타데이터 스크래핑용이며 ROM 실행, BIOS 및 에뮬레이터 정상 구동 여부를 보장하지 않습니다.

변경 기록: [Pull Request #5](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/5).
관련 문서: [Skyscraper 지원 플랫폼](https://github.com/muldjord/skyscraper/blob/master/docs/PLATFORMS.md), [Atomiswave ROM 형식](https://wiki.batocera.org/systems:atomiswave).

사용자의 명시적인 정식 출시 승인 전까지 모든 배포는 Beta / Pre-release입니다.
