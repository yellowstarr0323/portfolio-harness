#!/usr/bin/env python3
"""하네스 회귀 테스트.

사용법: python3 tests/run_tests.py          전체 (headless Chrome·poppler 필요)
        python3 tests/run_tests.py --fast   make_pdf 제외 (문서 구조만)

검사 대상: 스킬 문서 구조(frontmatter, 진입점, 참조 경로), 면접관 에이전트(agents/portfolio-reviewer.md), make_pdf.py(통과·넘침·깨진 이미지·PNG), scripts/test_env.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAKE_PDF = ROOT / "skills" / "build" / "scripts" / "make_pdf.py"
results: list[tuple[str, bool, str]] = []


def run(args: list[str], env: dict | None = None, timeout: int = 200) -> tuple[int, str]:
    p = subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, **(env or {})})
    return p.returncode, p.stdout + p.stderr


def check(name: str, code: int, out: str, want: int, has: tuple = (), lacks: tuple = ()) -> None:
    ok = code == want and all(h in out for h in has) and not any(x in out for x in lacks)
    results.append((name, ok, f"code {code} (기대 {want})\n{out.strip()[-400:]}"))


def docs_tests() -> None:
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    names = {p.parent.name for p in skills}
    results.append(("스킬 4개(start·interview·design·build)", names == {"start", "interview", "design", "build"}, str(names)))
    for p in skills:
        text = p.read_text(encoding="utf-8")
        m = re.match(r"---\nname: (\S+)\ndescription: (.+?)\n---\n", text, re.S)
        results.append((f"{p.parent.name}: frontmatter name이 폴더 이름과 같음", bool(m) and m.group(1) == p.parent.name, ""))
        results.append((f"{p.parent.name}: 원칙 문서 경로가 실제로 있음",
                        "../../rules/principles.md" in text and (p.parent / "../../rules/principles.md").resolve().is_file(), ""))
        if p.parent.name != "start":
            # 진입점은 start 하나 — 다른 스킬이 사용자 요청으로 직접 시작하면 이전 기록 확인·레퍼런스 질문이 빠진다
            results.append((f"{p.parent.name}: 사용자 트리거 문구 없음(start가 부름)", "start 스킬이 부른다" in m.group(2), m.group(2)[:80]))
    for script in ("make_pdf.py", "measure.js"):
        results.append((f"build/scripts/{script} 있음", (ROOT / "skills" / "build" / "scripts" / script).is_file(), ""))
    agent = ROOT / "agents" / "portfolio-reviewer.md"
    at = agent.read_text(encoding="utf-8") if agent.exists() else ""
    am = re.match(r"---\nname: (\S+)\ndescription: .+?\ntools: (.+?)\n---\n", at, re.S)
    results.append(("agents/portfolio-reviewer.md: frontmatter·읽기 전용 도구", bool(am) and am.group(1) == "portfolio-reviewer"
                    and set(t.strip() for t in am.group(2).split(",")) <= {"Read", "Glob", "Grep"}, am.group(2) if am else "없음"))
    criteria = ["원인을 분석해 해결", "적절한 근거", "여러 대안", "지원 직무", "짧은 시간", "오류나 모순"]
    removed = ["원리와 선택 이유", "직접 수행한 작업"]   # 10-11 사용자 결정으로 뺀 기준
    results.append(("portfolio-reviewer: 평가 기준 6개가 있고 뺀 2개는 없음",
                    all(c in at for c in criteria) and not any(r in at for r in removed) and "/30" in at,
                    str([c for c in criteria if c not in at] + [r for r in removed if r in at])))
    build_md = (ROOT / "skills" / "build" / "SKILL.md").read_text(encoding="utf-8")
    results.append(("build가 portfolio-harness:portfolio-reviewer를 PDF 경로만으로 부름",
                    "portfolio-harness:portfolio-reviewer" in build_md and "PDF 절대 경로만" in build_md and "최대 3회" in build_md, ""))
    results.append(("portfolio-reviewer: 지적마다 [수정]/[질문] 종류, 없으면 '없음'", "[수정]" in at and "[질문]" in at and "`없음`" in at, ""))
    loop_rules = ("남은 지적이 0개면 loop를 끝낸다", "거절 목록", "[수정] 지적", "[질문] 지적", "앞 회차 결과, 거절 목록을 넘기지 않는다")
    results.append(("build loop: 최대 3회·지적 0개면 끝·거절 걸러내기·리뷰어에 앞 회차를 안 넘김",
                    all(r in build_md for r in loop_rules), str([r for r in loop_rules if r not in build_md])))
    claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    results.append(("CLAUDE.md가 원칙 문서를 @import", "@rules/principles.md" in claude_md, ""))


def page(body: str) -> str:
    return ('<!doctype html><html><head><meta charset="utf-8"><style>@page{size:A4;margin:0}body{margin:0}'
            '.sheet{width:210mm;height:297mm;overflow:hidden;padding:20mm;box-sizing:border-box;page-break-after:always}'
            f'</style></head><body>{body}</body></html>')


def make_pdf_tests(tmp: Path) -> None:
    cases = [
        ("make_pdf 두 쪽 → PDF 2쪽 통과", '<section class="sheet"><h1>홍길동</h1></section><section class="sheet"><p>2쪽</p></section>',
         0, ("통과", "(2쪽)"), ("넘침",)),
        ("make_pdf 쪽 넘침 → 실패, PDF 안 만듦", '<section class="sheet"><div style="height:400mm">긴 내용</div></section>',
         1, ("넘침: 1쪽", "PDF를 만들지 않았다"), ()),
        ("make_pdf 깨진 이미지 → 실패", '<section class="sheet"><img src="nope.png"></section>',
         1, ("이미지 깨짐: nope.png",), ()),
        ("make_pdf sheet 없음 → 실패", "<div>내용</div>", 1, ('class="sheet"',), ()),
    ]
    for i, (name, body, want, has, lacks) in enumerate(cases):
        html, pdf = tmp / f"case{i}.html", tmp / f"case{i}.pdf"
        html.write_text(page(body), encoding="utf-8")
        code, out = run([str(MAKE_PDF), str(html), str(pdf)])
        check(name, code, out, want, has, lacks)
        if want == 1:
            results.append((f"{name}: PDF 파일이 없음", not pdf.exists(), ""))
    html, png = tmp / "preview.html", tmp / "preview.png"
    html.write_text(page('<section class="sheet">1쪽</section><section class="sheet">2쪽</section>'), encoding="utf-8")
    code, out = run([str(MAKE_PDF), str(html), "--png", str(png)])
    height = int.from_bytes(png.read_bytes()[20:24], "big") if png.exists() else 0
    results.append(("make_pdf --png 시안 미리보기가 두 쪽 높이로 찍힘", code == 0 and height > 2000, f"code {code}, 높이 {height}\n{out}"))
    code, out = run([str(MAKE_PDF), str(tmp / "없음.html"), str(tmp / "x.pdf")])
    check("make_pdf 없는 파일 → 사용법 오류", code, out, 2, ("사용법",), ())


def test_env_tests(tmp: Path) -> None:
    """scripts/test_env.py — 백업·되돌리기가 바꾼 것만 다루는지(가짜 ~/.claude로)."""
    claude = tmp / "fake-claude"
    claude.mkdir()
    settings = {"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "cat my-wiki/index.md"}]},
                                               {"hooks": [{"type": "command", "command": "echo keep"}]}]},
                "enabledPlugins": {"oh-my-claudecode@omc": True}}
    (claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    (claude / "CLAUDE.md").write_text("전역 지시", encoding="utf-8")
    env = {"HARNESS_TEST_CLAUDE_DIR": str(claude)}
    code, out = run([str(ROOT / "scripts" / "test_env.py"), "start"], env=env)
    d = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    off = (code == 0 and len(d["hooks"]["UserPromptSubmit"]) == 1 and d["enabledPlugins"]["oh-my-claudecode@omc"] is False
           and not (claude / "CLAUDE.md").exists())
    results.append(("test_env start: 위키 훅·OMC·전역 CLAUDE.md만 끔", off, out[-300:]))
    code, out = run([str(ROOT / "scripts" / "test_env.py"), "end"], env=env)
    d = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    back = (code == 0 and d == settings and (claude / "CLAUDE.md").read_text(encoding="utf-8") == "전역 지시")
    results.append(("test_env end: 원래대로 되돌림", back, out[-300:]))


def main() -> int:
    fast = "--fast" in sys.argv
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        docs_tests()
        test_env_tests(tmp)
        if not fast:
            make_pdf_tests(tmp)
    fails = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if not ok and detail:
            print("      " + detail.replace("\n", "\n      "))
    print(f"\n{len(results) - len(fails)}/{len(results)} 통과" + ("  (--fast: make_pdf 테스트 건너뜀)" if fast else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
