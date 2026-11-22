# 아키텍처와 테스트

## 구성
- `GUI_실행.pyw`, `GUI_실행.vbs`: Windows GUI 실행
- `gui.py`: Tkinter 화면/목록 선택/비동기 작업 상태·미리보기
- `backend.py`: 로컬 설정, ROM 조회·스크래핑 자원 관리
- `core.py`: ADB 호출·ROM 탐색·파일 크기/경로 인코딩, 기본 유틸리티
- `bundle_engine.py`: 선택 게임 처리, Skyscraper 연동 조정, 안전한 작업 제어
- `legacy_bridge.py`: 구형 Windows용 Skyscraper와의 호환
- `manager.py`: KNULLI `gamelist.xml` 메타데이터, 파일명·표시명·설명 변경
- `learned_titles.py`, `aliases.json`: 한글/영문 검색 후보 사전
- `user_data.py`, `credential_store.py`: 사용자 데이터 보관/Windows 자격 증명
- `setup_platform_tools.py`, `setup_engine.py`: 공식 배포 도구 설치
- `scrape_options.py`, `artwork.xml`: 스크래핑 설정과 출력 이미지 구성
- `tests/`: 버전별 회귀/GUI/경로 인코딩 테스트

## 처리 흐름
Windows GUI → ADB로 `/userdata/roms` 탐색 → KNULLI 시스템 폴더/ROM 식별 → 해시/저장된 영어명 매칭 → Skyscraper/ScreenScraper 검색 → 미디어 다운로드 → ADB 전송 → `gamelist.xml` 안전 검사·병합(영구 백업 없음) → 게임별 상태/미리보기 갱신.

기기 자체의 인터넷 연결은 필요하지 않으며, PC 인터넷만 사용합니다.

## 테스트 명령
```bash
python -m unittest discover -s tests -p 'test_*.py'
```

디스플레이 없는 리눅스:
```bash
xvfb-run -a python -m unittest discover -s tests -p 'test_*.py'
```

**초기 소스 확인:** 2026-11-20 Python 3.13, Xvfb 사용 시 60개 통과. 화면 없는 환경에서 Xvfb 없이 실행하면 Tkinter 테스트 13개가 `couldn't connect to display`로 실패하므로 반드시 GUI용 가상 디스플레이를 사용합니다.

## 데이터·보안
- `문서/KNULLI Auto Scraper Data/`: `settings.json`, `title_map.csv`, `learned_titles.json`, `manual_titles.json` 등. 앱 디렉터리에서 분리.
- ScreenScraper ID/비밀번호는 Windows 자격 증명 관리자에 저장.
- `work/`, `config.json`, 실제 ROM/BIOS, 다운로드된 제3자 바이너리는 GitHub에 커밋하지 않음.
- 공개 저장소이므로 개인정보/기기 로그를 넣지 않음.

## 검증의 구분
- 단위 테스트(모의 ADB/GUI): 기본 논리 검증.
- Windows 실행 테스트: 설치 및 GUI 생성/이벤트 확인.
- 실기기 테스트: RG35XX Plus/KNULLI의 ADB, 이미지/데이터 적용과 실행 결과 확인.
- 외부 연동 테스트: Skyscraper + ScreenScraper의 실제 인증/다운로드 확인.

각 수정의 검증 수준을 HANDOFF/CHANGELOG에 표시할 것.
