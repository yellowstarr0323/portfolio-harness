# 제품 맥락

제품 원칙은 `rules/principles.md`, 하네스 구조 결정은 `rules/decisions.md`가 원본이다. 여기에 다시 쓰지 않는다.

@rules/principles.md

## 하네스 개발 규칙

하네스(스킬·스크립트)를 고친 뒤에는 회귀 테스트를 돌린다.

```bash
python3 tests/run_tests.py          # 전체 (headless Chrome·poppler 필요)
python3 tests/run_tests.py --fast   # make_pdf 제외 (문서 구조만)
```

- 스크립트에 기능을 넣거나 고치면 `tests/run_tests.py`에 통과·실패 사례를 하나씩 추가한다.
- 브라우저 측정 코드는 `skills/build/scripts/measure.js`에 둔다. 파이썬 문자열 안에 JS를 넣지 않는다(% 와 역슬래시 이스케이프로 깨진다).
- 훅(`hooks/`)은 어떤 경우에도 종료 코드 0으로 끝낸다. Stop 훅이 실패하면 사용자의 턴 종료를 막는다.
- 사용자 트리거는 start 스킬에만 둔다. 다른 스킬 description에는 "start 스킬이 부른다"를 적는다(테스트가 본다).
- E2E 테스트(처음 쓰는 사람 조건)는 `./scripts/test-start.sh` → 새 세션에서 테스트 → `./scripts/test-end.sh` 순서로 한다. 플러그인 설정은 세션 시작 때 읽히므로 start·end 뒤에는 새 세션을 연다.
