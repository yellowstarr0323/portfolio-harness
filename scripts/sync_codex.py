#!/usr/bin/env python3
"""Claude Code 설정을 원본으로 Codex용 파일을 만든다(두 도구가 같은 내용을 쓰게).

사용법: sync_codex.py          만들기(덮어쓰기)
        sync_codex.py --check  만들 내용과 지금 파일이 같은지만 확인(다르면 1) — 회귀 테스트가 쓴다

만드는 것:
- AGENTS.md ← CLAUDE.md. Codex가 `@` import를 펼치는지 확인되지 않아, `@rules/principles.md` 줄을
  "rules/principles.md를 먼저 읽는다"로 바꾼다
- .codex/agents/portfolio-reviewer.toml ← .claude/agents/portfolio-reviewer.md
  (name·description·developer_instructions + sandbox_mode = "read-only")
스킬은 복사하지 않는다: .agents/skills 는 .claude/skills 를 가리키는 심볼릭 링크다.
원본(CLAUDE.md, .claude/agents/*.md)만 고치고 이 스크립트를 돌린다.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def agents_md() -> str:
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    header = "<!-- 이 파일은 scripts/sync_codex.py가 CLAUDE.md에서 만든다. 직접 고치지 말고 CLAUDE.md를 고친 뒤 다시 돌린다. -->\n"
    return header + text.replace("@rules/principles.md", "작업을 시작하기 전에 `rules/principles.md`(제품 원칙)를 먼저 읽는다.")


def reviewer_toml() -> str:
    text = (ROOT / ".claude" / "agents" / "portfolio-reviewer.md").read_text(encoding="utf-8")
    m = re.match(r"---\nname: (.+?)\ndescription: (.+?)\ntools: .+?\n---\n(.*)", text, re.S)
    if not m:
        sys.exit("portfolio-reviewer.md frontmatter를 읽지 못했다")
    name, desc, body = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    # TOML 기본 문자열(json.dumps와 이스케이프 규칙이 같다)로 넣어 따옴표·역슬래시·줄바꿈을 안전하게
    return ("# 이 파일은 scripts/sync_codex.py가 .claude/agents/portfolio-reviewer.md에서 만든다. 직접 고치지 않는다.\n"
            f"name = {json.dumps(name, ensure_ascii=False)}\n"
            f"description = {json.dumps(desc, ensure_ascii=False)}\n"
            'sandbox_mode = "read-only"\n'
            f"developer_instructions = {json.dumps(body, ensure_ascii=False)}\n")


TARGETS = {
    ROOT / "AGENTS.md": agents_md,
    ROOT / ".codex" / "agents" / "portfolio-reviewer.toml": reviewer_toml,
}


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale = []
    for path, make in TARGETS.items():
        want = make()
        have = path.read_text(encoding="utf-8") if path.exists() else None
        if have == want:
            continue
        if check:
            stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(want, encoding="utf-8")
            print(f"만듦: {path.relative_to(ROOT)}")
    if check:
        print("Codex 파일: 원본과 같음" if not stale else f"Codex 파일이 원본과 다름: {', '.join(stale)} — python3 scripts/sync_codex.py")
        return 1 if stale else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
