# 최초 GitHub 이식 검증 기록

- 완료일: **2026-11-20** (Asia/Seoul)
- 원본: 이 대화에서 제작된 `knulli_auto_scraper_adb_v084_unicode_folders.zip`
- ZIP SHA-256: `bb33c71e99dbda170e4460970ee4407b4aa0c42b8010c245d8d6e82b820c49ba`
- 소스 압축 스냅샷 SHA-256: `c670d786972d40f229803628a29bd05bbd2d5ef1ac811ac3c8844ff379c26c5c`
- 가져온 코드 커밋: `4734f7a954d0953a6f1306f8a3910039bcc6a634`
- [소스 복원 GitHub Actions 실행](https://github.com/Propeex/KNULLI-Korean-Auto-Scraper/actions/runs/44666598638): **성공**
- 소스 파일: `gui.py`, `backend.py`, `core.py`, `bundle_engine.py`, `manager.py`, `tests/` 등
- 임시 `migration/chunks` 스냅샷은 복원 액션에서 삭제됨.

## 검증 결과 수준

1. 압축·파일 무결성: 소스 스냅샷 해시 확인하고 원본 Python 파일을 리포지터리에 직접 복원.
2. **로컬 자동 테스트:** Python 3.13 + Xvfb에서 테스트 60개 통과(2026-11-20).
3. GitHub CI: 최초 이식 중 코드가 없던 시점의 테스트 실행은 실패. **복원 후 커밋의 테스트 상태를 따로 확인**해야 함.
4. 실제 사용자 Windows / RG35XX Plus 실기기: 이번 GitHub 이식 과정에서 기기에 연결해 재검증하지 않음.
5. 외부 Skyscraper/ScreenScraper 실서버 테스트: 이식 과정에서 재검증하지 않음.

## 주의

- `docs/HANDOFF.md`는 다음 대화에서 개발을 재개하기 위한 **첫 번째 문서**.
- 기능 수정 전에 반드시 이 문서, README, DECISIONS, KNOWN_ISSUES, ROADMAP을 검토.
- 릴리스/테스트/수정마다 문서의 ‘현재 상태’와 ‘다음 작업’을 갱신.
- 실제 계정·비밀번호, ROM·BIOS·개인 설정, 실기기 덤프는 GitHub에 업로드하지 않음.
