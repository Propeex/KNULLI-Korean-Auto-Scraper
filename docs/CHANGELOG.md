# 변경 이력

## v0.8.5-beta.2 — ADB 명령 길이 오류 및 스크래핑 백업 폐지 (2026-11-23)
- 실제 사용자 오류: `삭제된 게임 검사 실패: ADB shell failed: error: shell command too long`.
- 삭제된 게임을 검사할 때 한글 경로를 한 번만 영숫자로 인코딩하고, 기기 셸 명령 길이 예산에 맞춰 잘라서 검사. 그래도 명령 길이 때문에 실패하면 다시 분할; 단일 경로나 응답 오류는 안전을 위해 검사 중단.
- 사용자 요청에 따라 스크래핑, 이름/설명 변경, 자동 한글 표시명 동기화 및 삭제된 게임 자료 정리에서 **새로운 XML 백업 파일 생성 중단**.
- 최초 기기 연결 후 과거 버전이 만든 `gamelist.xml.knulli-autoscraper-<timestamp>.bak`만 삭제. 로컬에서는 현재 폴더 및 같은 상위 폴더에 있는 검증된 이전 설치본의 `work/xml_backups/<system>_<timestamp>.xml`만 삭제.
- ROM 원본, 현재 `gamelist.xml`, 이미지·영상, 사용자 개인 백업, 설정 및 자격 증명은 정리 대상에서 제외.
- 비정상 경로/ADB 응답/권한 오류가 있으면 삭제된 게임으로 잘못 판단하지 않음.
- [PR #2](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/2), GitHub 자동 테스트 85개 통과 ([실행](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45048905011)). 실기기 재검증은 아직.
- 주의: 자동 XML 백업이 없어 예상치 못한 쓰기 실패 시 복구가 더 어려울 수 있음.
- **GitHub 사전 출시 완료:** [v0.8.5-beta.2](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.5-beta.2), Windows ZIP(72,525 bytes), SHA256 파일 포함. [GitHub Actions 릴리즈 테스트 및 게시 성공](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45049288546). 실제 기기 재시험은 미완료.


## v0.8.5-beta.1 — 첫 GitHub 사전 출시 (2026-11-23)
- 사용자가 기기에서 ROM을 삭제한 후 GUI 목록을 조회하면 사라진 게임의 gamelist.xml 항목을 검사.
- ROM 실존 여부를 ADB로 직접 재확인하고, 정리할 XML 항목과 단독 소유 미디어 수를 미리 보여줌.
- 사용자 승인 이후 XML 백업·게임 항목 제거·다른 게임이 참조하지 않는 명시적 미디어 파일 제거.
- 의심스러운 경로, 시스템 범위 밖 자원, 공유 미디어, 잘못된 XML, 조회 중 다시 생성된 ROM은 보호.
- 작업 결과를 work/last_cleanup.json에 기록. Linux + 가상 디스플레이의 GitHub CI 테스트 통과; **실제 기기 검증 전**.
- ROM이 없는 시스템에서도 정리할 수 있게 빈 ROM 목록 처리를 보완.
- [PR #1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/pull/1) 통해 main에 병합.
- **GitHub Release 발행:** [v0.8.5-beta.1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.5-beta.1), Windows ZIP + SHA-256 checksum 파일. [릴리즈 검증 GitHub Actions](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45046433924) 성공. 베타(Pre-release) 상태 확인.


## v0.8.4 — GitHub 최초 이식 기준(2026-11-20)
- 한글 하위 폴더 경로의 ADB 탐색/파일 크기 조회 인코딩 보완.
- 문제 사례: `psx/한글 게임 폴더/Silent Hill (K).cue` → 경로 `????`, 파일 크기 확인 불가.
- 가상 환경 테스트 60개 통과; 실기기 결과는 미확인.
- **이 GitHub 이식은 v0.8.4 기준 코드 보존 작업이며 기능 수정/업그레이드가 아님.**

## v0.8.3
- 현재 선택 행 음영/마커 개선.
- 영어 `gamelist.xml <name>`을 한글 파일명 기준으로 동기화.
- Neo Geo 등 보호된 ZIP은 사용자 표시명 유지.

## v0.8.2
- 무채색 다크 GUI, 교차 행 음영 제거.
- 목록 상태 열 추가(선택/기종/게임명/상태).
- 영문 게임명 자동 저장.

## v0.8.1
- 다크 모드·선택 행 강조, 게임 정보 및 설정 화면 스크롤 개선.

## v0.8.0
- 간결한 단일 상세 화면.
- 사용자 데이터 앱 폴더 외부 보관.
- 완료된 게임 중간 결과 조회, 번역 기능 제거.

## v0.7.x
- 자동 ADB/Skyscraper 설치 시도, 파일명/표시명 편집, KNULLI 스크래핑 설정 조정.
- ROM 게임명 한글↔영문 사전 자동 기록.

## v0.6
- ROM 파일명 변경·연동된 gamelist.xml/이미지 경로 관리.
- 다양한 미디어·메타데이터 선택과 조회.

## v0.5
- 체크박스 GUI, 기존 자원 미리보기, 재스크래핑, 영문 검색어 수정.
- Skyscraper `artwork.xml` 구성 오류 대응.

## v0.4 이하
- ScreenScraper 직접 API 인증 대신 Skyscraper 엔진 사용.
- USB ADB 직접 접근·ROM 탐색·XML 백업/병합.
- `exec-out` 오류를 우회하는 ROM 탐색.
