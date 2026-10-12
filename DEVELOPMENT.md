# 하네스 개발 규칙

제품 원칙은 `rules/principles.md`, 하네스 구조 결정은 `rules/decisions.md`가 원본이다. 여기에 다시 쓰지 않는다.

## 구조
- `.claude/skills/` — start(진입점, 기존 포트폴리오 리뷰 포함) · interview · design · build
- `.claude/agents/portfolio-reviewer.md` — PDF만 보고 면접관 관점으로 평가
- `CLAUDE.md` — 사용자 세션에도 로드된다. 사용자용 내용만 둔다(개발 규칙은 이 파일에)
- Codex 지원: `AGENTS.md`(진입), `.agents/skills`(→ `.claude/skills` 심볼릭 링크), `.codex/agents/portfolio-reviewer.toml`

## 규칙
- **원본은 Claude Code 쪽이다.** `CLAUDE.md`나 `.claude/agents/portfolio-reviewer.md`를 고쳤으면 `python3 scripts/sync_codex.py`로 `AGENTS.md`·`.codex/agents/portfolio-reviewer.toml`을 다시 만든다. 다르면 테스트가 실패한다. 스킬은 심볼릭 링크라 따로 할 일이 없다.
- 스킬·에이전트 문서에 한 도구에만 있는 도구 이름을 단독으로 쓰지 않는다(예: "AskUserQuestion으로" 대신 "선택지로 — 도구가 없으면 글로").
하네스(스킬·에이전트·스크립트)를 고친 뒤에는 회귀 테스트를 돌린다.

```bash
python3 tests/run_tests.py          # 전체 (headless Chrome·poppler 필요)
python3 tests/run_tests.py --fast   # make_pdf 제외
```

- 스크립트에 기능을 넣거나 고치면 `tests/run_tests.py`에 통과·실패 사례를 하나씩 추가한다.
- 브라우저 측정 코드는 `.claude/skills/build/scripts/measure.js`에 둔다. 파이썬 문자열 안에 JS를 넣지 않는다(% 와 역슬래시 이스케이프로 깨진다).
- 사용자 트리거는 start 스킬에만 둔다. 다른 스킬 description에는 "start 스킬이 부른다"를 적는다(테스트가 본다).
- 이 폴더에서 개발 세션을 열면 하네스 스킬도 같이 켜진다. 루트에 `portfolio/`를 남겨 두면 "이어서" 흐름이 섞이니, 개발 중 시험 결과물은 다른 폴더에서 만든다.
- E2E 테스트(처음 쓰는 사람 조건)는 `./scripts/test-start.sh` → 출력된 명령(새 clone 폴더에서 `claude`)으로 새 세션 → `./scripts/test-end.sh` 순서로 한다. clone은 커밋된 내용만 가져가므로 테스트 전에 커밋한다.
