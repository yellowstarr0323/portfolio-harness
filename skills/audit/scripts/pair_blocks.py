#!/usr/bin/env python3
"""감사용 대조표 생성: HTML의 data-fact 블록마다 해당 facts 섹션을 나란히 놓는다.

사용법: pair_blocks.py <portfolio/out/index.html> <portfolio/facts> > portfolio/audit/pairs.md

출력 섹션
- PAIR n        : 블록 본문 + data-fact가 가리키는 facts 섹션 원문
                  data-fact에 근거가 여럿이면 쉼표로 구분한다: data-fact="dms.md#기술 선택, dms.md#작업"
                  data-role="headline"(쪽 헤드라인·한 줄 소개)인 블록은 제목에 [헤드라인]을 붙인다
- BROKEN        : data-fact가 가리키는 파일·섹션이 없음 (여럿 중 하나라도 없으면 BROKEN)
- UNATTRIBUTED  : data-fact 밖에 있는 20자 이상 문장 (근거 미표시)
- RETRO         : 회고 블록과 facts 회고 원문의 차이 (difflib)
"""
import difflib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SKIP_TAGS = {"title", "script", "style", "template", "noscript"}
HEADINGS = {f"h{i}" for i in range(1, 7)}
MIN_UNATTRIBUTED = 20


class Blocks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None, bool]] = []  # (tag, fact, skip)
        self.blocks: list[dict] = []          # {fact, role, text}
        self.open: list[dict] = []            # 열린 data-fact 블록
        self.loose: list[str] = []            # data-fact 밖 텍스트

    def _skipping(self) -> bool:
        return any(s for _, _, s in self.stack)

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        a = dict(attrs)
        skip = tag in SKIP_TAGS or "data-nocheck" in a
        fact = a.get("data-fact")
        self.stack.append((tag, fact, skip))
        if fact and not self._skipping():
            blk = {"fact": fact, "role": a.get("data-role"), "text": []}
            self.blocks.append(blk)
            self.open.append(blk)

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        _, fact, _ = self.stack.pop()
        if fact and self.open and self.open[-1]["fact"] == fact:
            self.open.pop()

    def handle_data(self, data):
        if not data.strip() or self._skipping():
            return
        if self.open:
            for blk in self.open:           # 중첩 블록이면 바깥 블록에도 포함
                blk["text"].append(data)    # 인라인 태그 경계에서 공백이 생기지 않게 원문 그대로
        elif not any(t in HEADINGS for t, _, _ in self.stack):
            self.loose.append(data.strip())


def facts_section(facts_dir: Path, ref: str) -> str | None:
    file, _, heading = ref.partition("#")
    path = facts_dir / file
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    if not heading:
        return "\n".join(lines)
    for i, line in enumerate(lines):
        m = re.match(r"^(#+)\s+(.*)$", line)
        if m and m.group(2).strip() == heading.strip():
            level, out = len(m.group(1)), [line]
            for nxt in lines[i + 1:]:
                n = re.match(r"^(#+)\s", nxt)
                if n and len(n.group(1)) <= level:
                    break
                out.append(nxt)
            return "\n".join(out)
    return None


REF_SPLIT = re.compile(r",\s*(?=[^,#]+\.md(?:#|$))")


def split_refs(fact: str) -> list[str]:
    """'a.md#x, b.md#y' → ['a.md#x', 'b.md#y']. 제목 안의 쉼표는 다음 조각이 '<파일>.md'로 시작할 때만 구분자로 본다."""
    return [r.strip() for r in REF_SPLIT.split(fact) if r.strip()]


def quoted(section: str) -> str:
    return "\n".join(l.lstrip("> ").rstrip() for l in section.splitlines() if l.startswith(">"))


def main(html_path: str, facts_dir: str) -> int:
    parser = Blocks()
    parser.feed(Path(html_path).read_text(encoding="utf-8"))
    facts = Path(facts_dir)
    broken = 0

    for i, blk in enumerate(parser.blocks, 1):
        text = re.sub(r"\s+", " ", "".join(blk["text"])).strip()
        refs = split_refs(blk["fact"])
        sections = {r: facts_section(facts, r) for r in refs}
        missing = [r for r, sec in sections.items() if sec is None]
        if missing:
            broken += 1
            print(f"## BROKEN {i} — data-fact=\"{blk['fact']}\" (없는 근거: {', '.join(missing)})\n\n본문: {text}\n")
            continue
        section = "\n\n".join(f"<!-- {r} -->\n{sec}" if len(refs) > 1 else sec for r, sec in sections.items())
        tag = " [헤드라인]" if blk["role"] == "headline" else ""
        print(f"## PAIR {i}{tag} — {blk['fact']}\n\n### 본문\n{text}\n\n### facts\n```\n{section}\n```\n")
        if "회고" in blk["fact"]:
            src = quoted(section)
            diff = list(difflib.unified_diff(src.split(), text.split(), "facts", "html", lineterm="", n=3))
            if diff:
                print(f"## RETRO {i} — 원문과 다름 (단어 단위)\n```diff\n" + "\n".join(diff[2:]) + "\n```\n")

    loose = [t for t in parser.loose if len(t) >= MIN_UNATTRIBUTED]
    for t in loose:
        print(f"## UNATTRIBUTED\n{t}\n")

    print(f"<!-- 블록 {len(parser.blocks)} / 깨진 참조 {broken} / 근거 미표시 {len(loose)} -->")
    return 1 if broken else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
