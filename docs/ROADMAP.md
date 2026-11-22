# 개발 계획 / Roadmap

## 목표
사용자가 RG35XX Plus/KNULLI에 **한글 ROM만 준비**하면 Windows GUI가 USB ADB로 접근해 ROM 검색·스크래핑·미디어 적용·XML 병합을 관리한다. 하위 폴더와 다양한 게임기도 자동 인식하고, 수동 영문 검색어 입력은 검색 실패시에만 필요하도록 한다.

## P0 — GitHub 이식 및 재개 가능성
- [x] 기준 저장소 확정: Propeex/KNULLI-Korean-Auto-Scraper
- [x] v0.8.4 소스 ZIP 및 테스트 기록 확보
- [x] v0.8.4 원본 소스·테스트 전체를 GitHub에 이식 (검증된 SHA256 소스 스냅샷 추출, 코드 커밋 `4734f7a`)
- [x] GitHub CI에서 복원 후 코드 기준 Python 자동 테스트 **성공** ([실행 결과](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/44666745166))
- [x] README 및 HANDOFF/ROADMAP/DECISIONS/KNOWN_ISSUES/CHANGELOG/ARCHITECTURE/MIGRATION 인수인계 문서 저장
**완료 기준:** 다른 대화에서 URL만 주면 코드/로드맵/마지막 문제를 확인할 수 있다.

## P1 — 사용자가 보고한 문제 검증
- [ ] 실제 기기에서 한글 하위 폴더 PS1 cue 조회 재검증(v0.8.4)
- [ ] 게임 완료 즉시 미리보기/상태 갱신 검증
- [ ] 게임 표시명이 KNULLI에서 한글로 나타나는지 확인
- [ ] 파일명 변경 및 XML·미디어 경로 안전성 확인
**완료 기준:** 실기기 테스트 로그 또는 재현 가능한 실패 보고서를 확보하고 대응한다.

## P1.5 — ROM 삭제 후 남은 자료 자동 감지/승인 정리
- [x] 모든 시스템의 `gamelist.xml`을 조회하여 ROM 실존 여부 확인
- [x] 삭제된 ROM의 XML 항목과 다른 게임이 사용하지 않는 명시적 미디어 경로만 정리 대상으로 선정
- [x] 목록 조회 후 정리할 항목을 미리 보여주고 명시적으로 동의받기
- [x] 실행 전 XML 재확인, 오류·공유 자원 보호 (**v0.8.5-beta.2부터 자동 백업 미생성**)
- [x] GitHub CI 자동 테스트 통과 ([실행](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/45045628986))
- [ ] 실제 RG35XX Plus에서 삭제/공유 자원/한글 폴더 검증
- [x] ROM이 0개인 상태에서도 정상 목록 표시·정리 감지하도록 탐색/GUI 보완 (실기기 검증 필요)
- [ ] CUE/M3U, 별도 폴더 gamelist 등 특수 케이스 검증
**완료 기준:** 사라진 게임의 메타데이터와 단독 자원만 정리되고, 기존 게임·공유 자원은 손상되지 않아야 함.

## P1.6 — ADB 길이 오류 및 스크래핑 백업 폐지 (v0.8.5-beta.2)
- [x] 한글 경로 검사 시 명령 바이트 길이 기준 분할 및 길이 거절 시 재분할
- [x] 응답이 잘리거나 단일 경로 검사조차 실패하면 삭제를 중단
- [x] 게임 스크래핑/편집/동기화/삭제 시 영구 XML 백업 생성 중단
- [x] 연결된 기기의 프로그램 고유 백업과 현재/인접 설치본 내 구버전 백업 정리
- [x] 다른 종류의 파일·사용자 백업·원본 ROM 보호 테스트
- [x] GitHub CI 자동 테스트 통과 (85개)
- [ ] Windows/실제 RG35XX Plus에서 긴 경로·대량 목록·백업 정리 결과 확인
**완료 기준:** 실기기에서 ADB 명령 길이 오류가 재발하지 않고, 프로그램 고유 백업만 제거됨.

## P1.7 — 실행 시 GitHub 최신 베타 자동 업데이트 (v0.8.6-beta.1)

- [x] GUI 실행 전 GitHub 릴리즈 목록에서 **공개 베타** 중 최신 버전 검색
- [x] 현재 설치 버전보다 높은 태그만 선택하고 정식 릴리즈는 사용자 승인 전 제외
- [x] ZIP 다운로드·SHA-256/checksum/API digest 대조, ZIP 경로 및 버전 검증
- [x] 사용자의 승인 없이 앱 종료 후 별도 프로세스로 코드 교체·재시작
- [x] 설정/스크랩 캐시/기기 데이터 보존, 실패 시 코드 롤백 및 기존 앱 재시작
- [x] 동시 실행 업데이트 잠금, 네트워크 장애 시 기존 앱 실행
- [x] Windows/Linux 자동 업데이트 테스트 및 [GitHub 베타 릴리즈 v0.8.6-beta.1](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.6-beta.1) 발행 완료
- [ ] 실제 Windows Pythonw 환경에서 다운로드→프로세스 종료→교체→재시작 검증
- [ ] 향후 첫 자동 업그레이드(베타.2 이상) 실사용 확인
**참고:** 베타.2 사용자는 이 기능을 받기 위해 베타.1을 처음 한 번 수동 설치해야 함.

## P1.8 — PortMaster 포팅 게임 지원 (v0.8.7-beta.1)

- [x] KNULLI `roms/ports` 최상위 게임 `.sh` 탐색, 관리/설치 스크립트 및 포트 데이터 재귀 스캔 제외
- [x] 게임 폴더의 `gameinfo.xml`, `port.json`, cover/screenshot 조회; 명시적 런처 경로 일치 시에만 메타데이터 사용
- [x] 기존 XML의 사용자 게임명·설명·이미지 보존, 누락 항목만 채우기
- [x] Skyscraper 없이 포트만 스크래핑, 사용자 승인된 XML만 변경
- [x] 사라진 런처의 XML 게임 항목만 제거 후보; 데이터/세이브 폴더 보호
- [ ] Windows/RG35XX Plus 실제 PortMaster 포트별 설치 경로 재검증
- [ ] 명시적 port.json/gameinfo.xml이 없는 포트의 보조 매칭은 추후 안전성 검토
- [x] GitHub Windows/Linux 테스트 통과 및 [v0.8.7-beta.1 Pre-release](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/releases/tag/v0.8.7-beta.1) 발행 완료

## P1.9 — Atomiswave .7z 인식 누락 수정 (v0.8.7-beta.2)

- [x] `atomiswave`을 KNULLI 게임 검색 대상 시스템에 등록
- [x] Skyscraper `atomiswave` 플랫폼 및 GUI 기종 표시 연결
- [x] `.7z` 포함 Atomiswave 지원 ROM 확장자와 한글 경로 검증
- [x] 압축 ROM 파일명 변경 방지, 기존 한글 게임명 보존 테스트
- [ ] GitHub CI 최종 통과 및 `v0.8.7-beta.2` 베타 릴리즈 확인
- [ ] 사용자 실제 RG35XX Plus에서 Atomiswave .7z 조회·스크래핑 확인

## P2 — 다운로드 범위와 검색 정확도
- [ ] 타이틀 화면(sstitle) 다운로드 가능한 공식/허용 경로 검증
- [ ] KNULLI 스크래퍼 선택지와 실제 Windows 엔진 옵션 대응표 정리
- [ ] 한국어 ↔ 영어 게임명 사전 자동 누적과 수동 수정 UX 개선
- [ ] 일부 ROM/게임기 추가 및 `.cue`/`.bin` 참조 보호 점검
**완료 기준:** 지원하는 자원은 실제 파일·XML·GUI에서 확인 가능하며 미지원 항목은 명확히 표시.

## P3 — 성능과 신뢰성
- [ ] ADB 데이터 조회 일괄화 및 캐시 무효화 개선
- [ ] 대형 ROM 전송 최소화(해시/메타데이터 우선)
- [ ] 작업 취소·재시도·중간 복구 정책 정리
- [ ] CI Windows GUI smoke 및 설치 테스트 추가
**완료 기준:** 처리량과 실패율을 측정 가능하게 기록, ROM/기존 XML 손상 없음.

## 보류 / 하지 않는 일
- Pad2Key 다운로드: 사용자가 PortMaster를 사용하며 우선순위 제외
- ROM 원본 내용 변경 및 위험한 아케이드 ROM 세트 이름 변경
- 기기 자체 인터넷 연결 구현; PC 인터넷 + ADB면 충분
- KNULLI OS 패치, ADB 서버 강제 재시작

> 이 계획은 완료 표시를 실제 코드·테스트·실기기 검증으로만 갱신한다.
