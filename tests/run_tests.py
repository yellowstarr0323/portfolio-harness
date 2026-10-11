#!/usr/bin/env python3
"""하네스 회귀 테스트.

사용법: python3 tests/run_tests.py          전체 (headless Chrome·poppler 필요)
        python3 tests/run_tests.py --fast   make_pdf 제외 (문서 구조만)

검사 대상: 스킬 문서 구조(frontmatter, 진입점, 참조 경로), 면접관 에이전트(agents/portfolio-reviewer.md), make_pdf.py(통과·넘침·깨진 이미지·PNG), upload.py·send_on_done.py(Discord 자동 전송), check_images.py(프로젝트 필수 이미지), scripts/test_env.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CL = ROOT / ".claude"
MAKE_PDF = CL / "skills" / "build" / "scripts" / "make_pdf.py"
results: list[tuple[str, bool, str]] = []


def run(args: list[str], env: dict | None = None, timeout: int = 200) -> tuple[int, str]:
    p = subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, **(env or {})})
    return p.returncode, p.stdout + p.stderr


def check(name: str, code: int, out: str, want: int, has: tuple = (), lacks: tuple = ()) -> None:
    ok = code == want and all(h in out for h in has) and not any(x in out for x in lacks)
    results.append((name, ok, f"code {code} (기대 {want})\n{out.strip()[-400:]}"))


def docs_tests() -> None:
    skills = sorted((CL / "skills").glob("*/SKILL.md"))
    names = {p.parent.name for p in skills}
    results.append(("스킬 4개(start·interview·design·build)", names == {"start", "interview", "design", "build"}, str(names)))
    for p in skills:
        text = p.read_text(encoding="utf-8")
        m = re.match(r"---\nname: (\S+)\ndescription: (.+?)\n---\n", text, re.S)
        results.append((f"{p.parent.name}: frontmatter name이 폴더 이름과 같음", bool(m) and m.group(1) == p.parent.name, ""))
        results.append((f"{p.parent.name}: 원칙 문서 경로가 실제로 있음",
                        "../../../rules/principles.md" in text and (p.parent / "../../../rules/principles.md").resolve().is_file(), ""))
        if p.parent.name != "start":
            # 진입점은 start 하나 — 다른 스킬이 사용자 요청으로 직접 시작하면 이전 기록 확인·레퍼런스 질문이 빠진다
            results.append((f"{p.parent.name}: 사용자 트리거 문구 없음(start가 부름)", "start 스킬이 부른다" in m.group(2), m.group(2)[:80]))
    hooks = json.loads((CL / "settings.json").read_text(encoding="utf-8")).get("hooks", {})
    results.append((".claude/settings.json: Stop 훅이 $CLAUDE_PROJECT_DIR/.claude/hooks/send_on_done.py",
                    "$CLAUDE_PROJECT_DIR/.claude/hooks/send_on_done.py" in json.dumps(hooks.get("Stop", [])), ""))
    results.append(("플러그인 파일 없음(폴더 방식)", not (ROOT / ".claude-plugin").exists(), ""))
    for script in ("make_pdf.py", "measure.js", "upload.py"):
        results.append((f"build/scripts/{script} 있음", (CL / "skills" / "build" / "scripts" / script).is_file(), ""))
    interview = (CL / "skills" / "interview" / "SKILL.md").read_text(encoding="utf-8")
    cats = ["프론트엔드", "백엔드", "DevOps", "앱", "임베디드", "AI", "풀스택", "게임"]
    line = next((l for l in interview.splitlines() if l.startswith("직무 분야:")), "")
    results.append(("interview: 직무 분야 선택지 8개", all(c in line for c in cats), line))
    results.append(("interview: 로고 1장 + 화면 1장 이상 필수, check_images로 확인",
                    "로고 1장 + 프로젝트 화면" in interview and "check_images.py" in interview, ""))
    agent = CL / "agents" / "portfolio-reviewer.md"
    at = agent.read_text(encoding="utf-8") if agent.exists() else ""
    am = re.match(r"---\nname: (\S+)\ndescription: .+?\ntools: (.+?)\n---\n", at, re.S)
    results.append(("agents/portfolio-reviewer.md: frontmatter·읽기 전용 도구", bool(am) and am.group(1) == "portfolio-reviewer"
                    and set(t.strip() for t in am.group(2).split(",")) <= {"Read", "Glob", "Grep"}, am.group(2) if am else "없음"))
    criteria = ["원인을 분석해 해결", "적절한 근거", "여러 대안", "지원 직무", "짧은 시간", "오류나 모순"]
    removed = ["원리와 선택 이유", "직접 수행한 작업"]   # 10-11 사용자 결정으로 뺀 기준
    results.append(("portfolio-reviewer: 평가 기준 6개가 있고 뺀 2개는 없음",
                    all(c in at for c in criteria) and not any(r in at for r in removed) and "/30" in at,
                    str([c for c in criteria if c not in at] + [r for r in removed if r in at])))
    build_md = (CL / "skills" / "build" / "SKILL.md").read_text(encoding="utf-8")
    results.append(("build가 portfolio-reviewer를 PDF 경로만으로 부름",
                    "`portfolio-reviewer`" in build_md and "PDF 절대 경로만" in build_md and "최대 3회" in build_md, ""))
    results.append(("portfolio-reviewer: 지적마다 [수정]/[질문] 종류, 없으면 '없음'", "[수정]" in at and "[질문]" in at and "`없음`" in at, ""))
    loop_rules = ("남은 지적이 0개면 loop를 끝낸다", "거절 목록", "[수정] 지적", "[질문] 지적", "앞 회차 결과, 거절 목록을 넘기지 않는다")
    results.append(("build loop: 최대 3회·지적 0개면 끝·거절 걸러내기·리뷰어에 앞 회차를 안 넘김",
                    all(r in build_md for r in loop_rules), str([r for r in loop_rules if r not in build_md])))
    claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    results.append(("CLAUDE.md가 원칙 문서를 @import하고 start 스킬로 안내", "@rules/principles.md" in claude_md and "start 스킬" in claude_md, ""))
    results.append(("CLAUDE.md에 개발 규칙이 섞이지 않음(사용자 세션에도 로드됨)", "run_tests" not in claude_md and (ROOT / "DEVELOPMENT.md").is_file(), ""))


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


def webhook_server():
    """가짜 Discord 웹훅: /hook → 204, 받은 본문을 모은다. (서버, 기본 주소, 받은 목록)"""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    got: list[bytes] = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            ok = self.path.startswith("/hook")
            if ok:
                got.append(body)
            self.send_response(204 if ok else 404)
            self.end_headers()

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}", got


def send_tests(tmp: Path) -> None:
    """upload.py와 턴 끝 훅 send_on_done.py — 리뷰가 끝난 최종 PDF만, 한 번만, 조용히 보낸다."""
    import time
    up = CL / "skills" / "build" / "scripts" / "upload.py"
    hook = CL / "hooks" / "send_on_done.py"
    srv, base, got = webhook_server()
    cfg = tmp / "upload.json"
    cfg.write_text(json.dumps({"discord_webhook": f"{base}/hook"}), encoding="utf-8")
    work = tmp / "work"
    pf = work / "portfolio"
    (pf / "out").mkdir(parents=True)
    (pf / "review").mkdir()
    (pf / "profile.md").write_text("# 프로필\n- 이름: 김전송 (출처: 사용자)\n", encoding="utf-8")
    pdf = pf / "out" / "portfolio.pdf"
    pdf.write_bytes(b"%PDF-1.4 final")
    env = {"HARNESS_UPLOAD_CONFIG": str(cfg), "CLAUDE_PROJECT_DIR": ""}

    def fire(cwd: Path) -> int:
        p = subprocess.run([sys.executable, str(hook)], input=json.dumps({"hook_event_name": "Stop", "cwd": str(cwd)}),
                           capture_output=True, text=True, timeout=120, env={**os.environ, **env})
        return p.returncode

    code, out = run([str(up), str(pdf), "--config", str(tmp / "없음.json")])
    check("upload 설정 없음 → 건너뜀(0)", code, out, 0, ("설정 없음",), ())
    (pf / "state.md").write_text("- stage: build\n", encoding="utf-8")
    fire(work)
    results.append(("hook stage가 done이 아니면 안 보냄", len(got) == 0, f"보낸 수 {len(got)}"))
    (pf / "state.md").write_text("- stage: done\n- loop: done\n", encoding="utf-8")
    fire(work)
    results.append(("hook 리뷰 파일이 없으면 안 보냄", len(got) == 0, f"보낸 수 {len(got)}"))
    review = pf / "review" / "portfolio-reviewer-1.md"
    review.write_text("# 면접관 평가", encoding="utf-8")
    os.utime(review, (time.time() - 100, time.time() - 100))
    fire(work)
    results.append(("hook 리뷰가 PDF보다 먼저면(리뷰 뒤 PDF를 다시 만듦) 안 보냄", len(got) == 0, f"보낸 수 {len(got)}"))
    os.utime(review, None)
    code = fire(pf / "out")      # 모델이 cd portfolio/out 을 해서 cwd가 하위 폴더인 경우(10-11 E2E)
    sent = len(got) == 1 and "김전송.pdf".encode() in got[0]
    results.append(("hook cwd가 portfolio/ 하위여도 작업 폴더를 찾아 최종 PDF를 보냄(이름.pdf)", code == 0 and sent, f"code {code}, 보낸 수 {len(got)}"))
    fire(work)
    results.append(("hook 같은 PDF는 다시 안 보냄", len(got) == 1, f"보낸 수 {len(got)}"))
    log = (pf / "out" / ".upload.log")
    results.append(("hook 결과는 .upload.log에만 남김", log.exists() and "보냄" in log.read_text(encoding="utf-8"), ""))
    p = subprocess.run([sys.executable, str(hook)], input="JSON 아님", capture_output=True, text=True, timeout=60)
    results.append(("hook 입력이 깨져도 종료 0", p.returncode == 0, f"code {p.returncode}"))
    bad = tmp / "bad.json"
    bad.write_text(json.dumps({"discord_webhook": f"{base}/deleted"}), encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4 changed")
    code, out = run([str(up), str(pdf), "--config", str(bad)])
    check("upload 웹훅 404 → 실패 표시, URL은 출력 안 함", code, out, 1, ("전송 실패", "404"), (base,))
    srv.shutdown()
    srv.server_close()


def image_tests(tmp: Path) -> None:
    """check_images.py — 프로젝트마다 로고 1장 + 화면 1장 이상(필수)."""
    ci = CL / "skills" / "interview" / "scripts" / "check_images.py"
    pf = tmp / "imgpf"
    (pf / "projects").mkdir(parents=True)
    for slug in ("dms", "zipkr"):
        (pf / "projects" / f"{slug}.md").write_text(f"# {slug}", encoding="utf-8")
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 20

    def put(slug: str, name: str, data: bytes = png) -> None:
        (pf / "images" / slug).mkdir(parents=True, exist_ok=True)
        (pf / "images" / slug / name).write_bytes(data)

    code, out = run([str(ci), str(pf)])
    check("check_images 이미지 없음 → 실패", code, out, 1, ("빠짐: dms — 로고 없음, 프로젝트 화면 없음",), ())
    put("dms", "logo.png")
    put("dms", "screen-1.png")
    put("zipkr", "logo.svg")
    code, out = run([str(ci), str(pf)])
    check("check_images 화면이 없는 프로젝트 → 실패", code, out, 1, ("있음: dms — 로고 1, 화면 1", "빠짐: zipkr — 프로젝트 화면 없음"), ())
    put("zipkr", "screen-1.gif", b"")
    code, out = run([str(ci), str(pf)])
    check("check_images 0바이트 화면은 없는 것으로 봄", code, out, 1, ("빠짐: zipkr — 프로젝트 화면 없음",), ())
    put("zipkr", "screen-2.webp")
    put("zipkr", "screen-3.jpg")
    code, out = run([str(ci), str(pf)])
    check("check_images 로고 1 + 화면 1장 이상 → 통과", code, out, 0, ("있음: zipkr — 로고 1, 화면 2", "모두 있음"), ())
    put("dms", "logo.jpg")
    code, out = run([str(ci), str(pf)])
    check("check_images 로고 2개 → 실패(하나만)", code, out, 1, ("로고가 2개",), ())
    code, out = run([str(ci), str(tmp / "없는폴더")])
    check("check_images 없는 폴더 → 사용법 오류", code, out, 2, ("사용법",), ())


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
        send_tests(tmp)
        image_tests(tmp)
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
