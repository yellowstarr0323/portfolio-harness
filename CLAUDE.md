# Product Context

제품 원칙은 `rules/principles.md`, 구체적인 사용자 결정은 `rules/user-decisions.md`가 원본이다. 여기에 다시 쓰지 않는다.

@rules/principles.md

## 하네스 개발 규칙

하네스(스킬·에이전트·스크립트)를 고친 뒤에는 회귀 테스트를 돌린다.

```bash
python3 tests/run_tests.py          # 전체 (headless Chrome·poppler·네트워크 필요, 약 20초)
python3 tests/run_tests.py --fast   # export.py 제외 (몇 초)
```

- 검사 스크립트에 새 검사를 넣거나 고치면 `tests/run_tests.py`에 통과·실패 사례를 하나씩 추가한다.
- `export.py`의 브라우저 측정 코드는 `skills/build/scripts/measure.js`에 있다. 파이썬 문자열 안에 JS를 다시 넣지 않는다(% 와 역슬래시 이스케이프로 여러 번 깨졌다).
- E2E 테스트(처음 쓰는 사람 조건)는 `./scripts/test-start.sh` → 새 세션에서 테스트 → `./scripts/test-end.sh` 순서로 한다. 위키 훅·OMC·전역 CLAUDE.md를 바꾼 것만 되돌린다. 훅·플러그인 설정은 세션 시작 때 읽히므로 start·end 뒤에는 새 세션을 연다.
