# KNULLI Korean Auto Scraper v0.8.5 Beta 1

**Windows / RG35XX Plus / KNULLI / USB ADB**

> 이 버전은 **베타(Pre-release)**입니다. GitHub 자동 테스트는 통과했지만 Windows와 실제 RG35XX Plus 기기에서 삭제된 ROM 자료 정리 기능을 완전히 검증하지 못했습니다.

## 이번 릴리즈의 변경 사항

- 삭제된 ROM을 기기에서 재조회하고, `gamelist.xml`에 남은 게임 정보 감지
- 삭제 후보 게임과 이미지·영상·매뉴얼 수를 표시한 후 **사용자 승인**이 있어야 정리
- 다른 게임 또는 다른 기종에서 **공유하는 미디어 파일은 삭제하지 않음**
- 기존 `gamelist.xml`을 PC와 기기에 백업하고, 작업 직전 데이터 변경·ROM 재등장 여부를 재검증
- 한글 하위 폴더를 포함한 ROM 경로 대응
- ROM을 전부 삭제하여 게임 목록이 비어도 XML 정리 후보를 확인할 수 있게 보완
- 상세 정리 보고서는 PC 프로그램 폴더의 `work/last_cleanup.json`에 저장

## 중요한 주의사항

- **정리 기능은 선택한 뒤 실제 파일을 삭제할 수 있습니다.** 삭제된 이미지·영상 파일 자체는 별도 백업하지 않습니다. 테스트용 게임으로 먼저 확인하세요.
- XML이 참조하지 않는 미디어나 소유권을 확인할 수 없는 파일은 보호를 위해 자동 삭제하지 않습니다.
- KNULLI 기기 인터넷은 불필요하며 **Windows PC 인터넷 + USB ADB 연결**이 필요합니다.
- 외부 화면 스크래핑 엔진 및 원본 ROM 파일은 ZIP에 포함되어 있지 않습니다.

## 설치와 실행

1. 아래 **Windows ZIP**을 받아 새 폴더에 압축 해제합니다.
2. Windows에 Python **3.10 이상**과 Tkinter가 있어야 합니다. **독립 실행 EXE가 아닌 Python GUI 앱**입니다.
3. RG35XX Plus의 기존 USB ADB 연결을 유지한 채 `GUI_실행.pyw`를 실행합니다.
4. 프로그램은 ADB/Skyscraper가 없으면 자동 설치를 시도합니다.
5. 처음에는 중요한 ROM 없이 정리 동작을 확인하는 것을 권장합니다.

기존 사용자 설정과 영문명 대응표는 별도 사용자 데이터 위치에 저장됩니다.

## 검증

GitHub Actions에서 Python 유닛/GUI 테스트(Xvfb) 후 Windows 배포 ZIP 무결성을 검사하고 배포합니다. **Windows 실기기 연동은 별도로 검증이 필요합니다.**

관련 개발 변경: [Pull Request #1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/1)

향후 정식판 여부는 사용자 승인으로만 결정하며, 이 릴리즈는 Beta 1입니다.
