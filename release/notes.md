# KNULLI Korean Auto Scraper v0.8.5 Beta 2

**Windows / RG35XX Plus / KNULLI / USB ADB**

> **베타(Pre-release)**입니다. 자동 테스트는 통과했지만 실제 사용자 기기에서 이번 수정의 최종 검증은 아직 필요합니다.

## 해결된 문제

- **`삭제된 게임 검사 실패: ADB shell failed: error: shell command too long`**: 한글 ROM 경로를 인코딩해 여러 게임을 검사할 때 ADB 명령이 너무 길어지는 문제를 수정했습니다.
- 검사할 명령을 크기에 따라 나누고, 그래도 길이 오류가 발생하면 다시 분할합니다.
- 경로 하나조차 확인하지 못하거나 응답이 잘리면 해당 ROM을 삭제된 것으로 간주하지 않고 **자료 정리 중단**을 선택합니다.

## 백업 정책 변경 — 사용자 요청

- 이제 스크래핑, 한글 표시명 동기화, 이름·설명 수정, ROM 이름 변경, 삭제된 게임 자료 정리에서 **새로운 `gamelist.xml` 백업을 만들지 않습니다.**
- 최초 기기 연결 시 과거 이 프로그램이 생성한 `gamelist.xml.knulli-autoscraper-<시간>.bak` 파일을 기기의 ROM 기종 폴더에서 찾아 정리합니다.
- Windows PC에서는 현재 설치 폴더와 **같은 상위 폴더의 확인된 이전 설치본**에 있는 `work/xml_backups/<기종>_<시간>.xml` 파일을 정리합니다.
- **삭제하지 않는 것:** 원본 ROM, 현재 `gamelist.xml` 본파일, 사용 중인 이미지·영상·매뉴얼, 사용자 설정/계정, 직접 만든 다른 이름의 백업.
- 다른 위치에 있는 기존 설치본은 안전을 위해 컴퓨터 전체를 임의 검색하지 않습니다.

**주의:** 자동 XML 백업을 만들지 않으므로 USB 연결 중단이나 예기치 않은 XML 쓰기 오류 시 복구가 어려울 수 있습니다. 사용자가 소중한 데이터는 별도로 보관하시기 바랍니다.

## 기존 기능

- 한글 ROM과 하위 폴더의 USB ADB 탐색
- 게임 정보·이미지·영상 등의 PC 스크래핑 적용
- 게임 파일을 직접 삭제한 뒤 남은 `gamelist.xml` 정보 및 공유되지 않는 미디어 정리
- 삭제된 게임 관련 파일의 정리는 별도 확인 창에서 승인해야 실행
- 회색·검정 다크 GUI, 선택/기종/게임명/상태 목록, 영어 검색명 자동 저장

## 설치

1. 이 릴리즈의 Windows ZIP을 내려받아 별도 폴더에 압축 해제하세요.
2. **Python 3.10 이상과 Tkinter가 필요**합니다. 독립 실행 EXE가 아닌 Python GUI 패키지입니다.
3. 기존 USB ADB 연결을 유지한 채 `GUI_실행.pyw`를 실행하세요. 기기 자체 인터넷 연결은 불필요합니다.

## 테스트

- GitHub Actions Python 회귀/GUI 테스트 **85개 통과** ([검증 기록](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45048905011)).
- POSIX 로컬 셸을 이용해 한글 경로 존재 검사, 길이 제한 재분할, 앱 생성 XML 백업 정리 범위 확인.
- **실제 Windows/RG35XX Plus에서의 최종 검증은 미완료.**

관련 변경: [PR #2](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/2).

정식 출시는 사용자의 승인 전까지 하지 않으며, 이 릴리즈는 Beta 2입니다.
