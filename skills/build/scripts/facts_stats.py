#!/usr/bin/env python3
"""facts의 재료 점검: 포트폴리오를 만들기에 재료가 충분한지 프로젝트별로 센다.

사용법: facts_stats.py <portfolio/facts>

세는 것 (interview 스킬의 '사실 파일 형식' 기준)
- 작업:       '## 작업' 아래 '### ' 항목 수
- 완결:       상황(또는 발견·문제) + 원인 + 해결 + 결과가 모두 있는 작업 = 트러블슈팅으로 쓸 수 있는 이야기
- 측정:       '측정:' 칸(도구·조건)이 적혀 있고 결과에 수치가 있는 작업. 근거없음/모름/충돌 줄은 세지 않는다
- 기술 선택:  '## 기술 선택' 아래 '### ' 항목 수 / 그중 '대안:' 줄이 있는 것
- 근거없음·모름·충돌 태그 수, 회고 인용 수, 열린 빈칸 수
판정 (심층 프로젝트만)
- 부족: 완결 작업 0개 또는 측정 있는 작업 0개 → build 전에 자료를 더 받을지 사용자에게 묻는다
- 보통: 완결 1개
- 충분: 완결 2개 이상이면서 측정 있는 작업 1개 이상
판정은 형식 기준의 근사치다. 라벨이 다르게 적힌 항목은 놓칠 수 있으니 파일도 직접 본다.
종료 코드: 항상 0 (점검용).
"""
import re
import sys
from pathlib import Path

LABEL = re.compile(r"(?:^\s*-\s*|/\s*)(상황|발견|문제|원인|확인 방법|해결|결과|측정)\s*(?:\([^)]*\))?\s*[:：]")
NUM = re.compile(r"\d")
BAD = re.compile(r"status:\s*(근거없음|모름|충돌)")
H2 = re.compile(r"^##\s+(.*)$")
H3 = re.compile(r"^###\s+(.*)$")


def sections(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    cur = None
    for line in text.splitlines():
        if m := H2.match(line):
            cur = m.group(1).strip()
            out.setdefault(cur, [])
        elif cur is not None:
            out[cur].append(line)
    return out


def items(lines: list[str]) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for line in lines:
        if m := H3.match(line):
            out.append((m.group(1).strip(), []))
        elif out:
            out[-1][1].append(line)
    return out


def task_flags(lines: list[str]) -> dict:
    labels: set[str] = set()
    has_cond = has_num = False
    for line in lines:
        found = {m.group(1) for m in LABEL.finditer(line)}
        labels |= found
        if BAD.search(line):
            continue
        has_cond |= "측정" in found
        has_num |= bool(found & {"결과", "측정"}) and bool(NUM.search(line))
    measured = has_cond and has_num
    problem = bool(labels & {"상황", "발견", "문제"})
    return {
        "complete": problem and {"원인", "해결", "결과"} <= labels,
        "measured": measured,
        "missing": [k for k, ok in (("상황", problem), ("원인", "원인" in labels),
                                    ("해결", "해결" in labels), ("결과", "결과" in labels)) if not ok],
    }


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    return {k.strip(): v.strip() for k, _, v in (l.partition(":") for l in m.group(1).splitlines()) if _}


def main(facts_dir: str) -> int:
    files = sorted(Path(facts_dir).glob("*.md"))
    if not files:
        print("facts 파일이 없다")
        return 0
    rows, notes = [], []
    for f in files:
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text)
        secs = sections(text)
        if fm.get("kind") == "profile" or f.name == "profile.md":
            intro = "\n".join(secs.get("한 줄 소개", []))
            if not intro.strip() or "생략" in intro:
                notes.append(f"{f.name}: 한 줄 소개 없음 → build outline에서 facts로 만든 후보를 제시한다")
            continue
        tasks = items(secs.get("작업", []))
        flags = [(t, task_flags(ls)) for t, ls in tasks]
        choices = items(secs.get("기술 선택", []))
        with_alt = sum(1 for _, ls in choices if any("대안" in l for l in ls))
        complete = sum(1 for _, fl in flags if fl["complete"])
        measured = sum(1 for _, fl in flags if fl["measured"])
        bad = {k: len(re.findall(rf"status:\s*{k}", text)) for k in ("근거없음", "모름", "충돌")}
        retro_lines = secs.get("회고 (원문 유지)", [])
        retro = sum(1 for i, l in enumerate(retro_lines)
                    if l.startswith(">") and (i == 0 or not retro_lines[i - 1].startswith(">")))
        blanks = sum(1 for l in secs.get("빈칸", []) if l.lstrip().startswith("- [ ]"))
        deep = fm.get("depth", "deep") == "deep"
        if not deep:
            verdict = "-"
        elif complete == 0 or measured == 0:
            verdict = "부족"
        elif complete >= 2:
            verdict = "충분"
        else:
            verdict = "보통"
        rows.append((fm.get("project", f.stem), fm.get("depth", "?"), len(tasks), complete, measured,
                     f"{len(choices)}/{with_alt}", f"{bad['근거없음']}/{bad['모름']}/{bad['충돌']}",
                     retro, blanks, verdict))
        for t, fl in flags:
            if not fl["complete"]:
                notes.append(f"{f.name} · {t}: 빠진 칸 {', '.join(fl['missing'])}"
                             + ("" if fl["measured"] else " / 측정 수치 없음"))

    head = ("프로젝트", "깊이", "작업", "완결", "측정", "기술선택/대안", "근거없음/모름/충돌", "회고", "빈칸", "판정")
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print("| " + " | ".join(str(c) for c in r) + " |")
    weak = [r[0] for r in rows if r[-1] == "부족"]
    print()
    if weak:
        print(f"재료 부족: {', '.join(weak)} — 트러블슈팅(상황→원인→해결→결과)이나 측정 수치가 없다.")
    if notes:
        print("세부:")
        for n in notes:
            print(f"- {n}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
