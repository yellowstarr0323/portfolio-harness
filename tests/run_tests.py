#!/usr/bin/env python3
"""하네스 검사 스크립트 회귀 테스트.

사용법: python3 tests/run_tests.py [--fast]

검사 대상: rules/ 단일 원본 구조, facts_lint, facts_stats, check_numbers, pair_blocks(audit), log_answers 훅·근거 원문 대조, env_check, image_info, layout_check, link_check, upload, export.py, scripts/test_env.py
  --fast  headless Chrome이 필요한 export.py 테스트를 건너뛴다 (나머지는 몇 초)

테스트용 HTML·기록·이미지를 임시 폴더에 만들고, 각 스크립트의 종료 코드와 출력 문구를 확인한다.
새 검사를 넣거나 고치면 여기에 통과·실패 사례를 하나씩 추가한다 — export.py가 같은 원인으로
네 번 깨진 뒤에 만든 장치다.

export.py 테스트는 Chrome·poppler가 있어야 하고, Pretendard를 CDN에서 받으므로 네트워크가 필요하다.
종료 코드: 모두 통과 0, 하나라도 실패 1.
"""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "build" / "scripts"
THEME = ROOT / "skills" / "design" / "theme"
MAKE_THEME = ROOT / "skills" / "design" / "scripts" / "make_theme.py"

results: list[tuple[str, bool, str]] = []


# ---------- 공용 도구 ----------

def run(args: list[str], cwd: Path | None = None, timeout: int = 300, env: dict | None = None) -> tuple[int, str]:
    import os
    p = subprocess.run([sys.executable, "-I", *args], capture_output=True, text=True, cwd=cwd, timeout=timeout,
                       env={**os.environ, **(env or {})})
    return p.returncode, p.stdout + p.stderr


def check(name: str, code: int, out: str, exit_code: int | None = None,
          has: tuple[str, ...] = (), lacks: tuple[str, ...] = ()) -> None:
    problems = []
    if exit_code is not None and code != exit_code:
        problems.append(f"종료 코드 {code} (기대 {exit_code})")
    problems += [f"출력에 없음: {h!r}" for h in has if h not in out]
    problems += [f"출력에 있으면 안 됨: {l!r}" for l in lacks if l in out]
    results.append((name, not problems, "; ".join(problems) or "ok"))
    if problems:
        tail = "\n".join(out.strip().splitlines()[-15:])
        results[-1] = (name, False, "; ".join(problems) + "\n      ── 출력 끝부분 ──\n      " + tail.replace("\n", "\n      "))


def png(path: Path, w: int, h: int) -> None:
    raw = b"".join(b"\x00" + b"\xcc" * w * 3 for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))  # noqa: E731
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 40"><rect width="120" height="40" fill="#0369a1"/></svg>'


# ---------- export.py 픽스처 ----------

PAGE_CSS = """
body{margin:0;background:#fff;color:var(--text);font-family:var(--font-body);font-size:var(--fs-body);line-height:1.55}
.sheet{width:210mm;height:297mm;padding:48px;box-sizing:border-box;overflow:hidden;position:relative;break-after:page;background:#fff}
.sheet:last-child{break-after:auto}
h1{font-size:var(--fs-page-title);margin:0} h2{font-size:var(--fs-section);margin:16px 0 8px}
p{margin:0 0 6px} ul{margin:0 0 6px}
.head-row{display:flex;align-items:baseline;gap:12px}
.head-row img{height:30px}
.head-row .period{margin-left:auto;font-size:var(--fs-meta);color:var(--muted)}
.pn{position:absolute;right:48px;bottom:24px;font-size:var(--fs-caption);color:var(--muted)}
.hdr{font-size:var(--fs-meta);color:var(--muted)}
"""


def link_server():
    """링크 접속 확인용 로컬 서버: /ok → 200, 그 밖 → 404. (서버, 기본 주소)"""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _reply(self, body: bool):
            code = 200 if self.path.startswith("/ok") else 404
            self.send_response(code); self.send_header("Content-Type", "text/html"); self.end_headers()  # noqa: E702
            if body:
                self.wfile.write(b"ok" if code == 200 else b"missing")

        def do_HEAD(self):
            self._reply(False)

        def do_GET(self):
            self._reply(True)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


def filler(n: int) -> str:
    return "".join(f"<p>상세 설명 문장 {i}번째 줄로 쪽을 채우는 본문이다.</p>" for i in range(n))


SHAPES_HTML = (
    '<section data-role="project-detail" data-layout="timeline"><h2 data-role="section-title">태그 스케줄러 버그</h2>'
    '<ol class="timeline" data-role="timeline"><li><span class="tl-when">46일간</span><p class="tl-title">같은 에러 반복</p><p>서버 로그에서 발견했다.</p></li>'
    '<li><span class="tl-when">원인</span><p class="tl-title">CAST 타입 미등록</p><p>문자열 타입으로 바꿨다.</p></li></ol></section>'
    '<section data-role="project-detail" data-layout="flow-compare"><h2 data-role="section-title">새벽자습 신청</h2>'
    '<div class="flow-compare" data-role="flow-compare"><div class="flow-col" data-side="before"><p class="flow-label">기존</p>'
    '<ol class="flow-steps"><li>담당선생님 구두 승인</li><li>부장선생님 구두 승인</li></ol></div>'
    '<div class="flow-col" data-side="after"><p class="flow-label">바뀐 뒤</p><ol class="flow-steps"><li>앱에서 신청</li><li>명단 자동 반영</li></ol></div></div></section>'
    '<section data-role="project-detail" data-layout="process-flow"><h2 data-role="section-title">규정 챗봇</h2>'
    '<ol class="process-flow" data-role="process-flow"><li><span class="pf-no" data-nocheck>1</span><p class="pf-title">업로드</p><p class="pf-desc">규정 파일</p></li>'
    '<li><span class="pf-no" data-nocheck>2</span><p class="pf-title">임베딩</p><p class="pf-desc">헤딩 단위</p></li>'
    '<li><span class="pf-no" data-nocheck>3</span><p class="pf-title">검색</p><p class="pf-desc">같은 학교만</p></li></ol></section>'
    '<section data-role="project-detail" data-layout="decision"><h2 data-role="section-title">벡터 저장소 선택</h2>'
    '<div class="decision-card" data-role="decision-card"><p class="dc-choice">PostgreSQL + pgvector</p><p>한 DB에서 관리한다.</p>'
    '<p class="dc-alt"><span class="dc-tag">대안</span>MySQL과 Redis 이중 쓰기</p></div></section>'
)


def portfolio_html(*, period_below=False, retro_first=False, pair_split=False, sparse_first=False,
                   running_header=False, arrow_top=False, small_font=False, plain_ba=False,
                   hidden_tall=False, intro_arrow=False, lowres=False, diagram_pair="",
                   no_layout=False, shapes=False, links="", link_base="", ruled_wrapper=False) -> str:
    period = '<span class="period" data-role="project-meta">2026.03 ~ 운영 중</span>'
    if period_below:
        head_row = '<div class="head-row"><img data-kind="logo" src="assets/logo.svg" alt=""><h1 data-role="page-title">DMS</h1></div>' \
                   '<p data-role="project-meta">2026.03 ~ 운영 중</p>'
    else:
        head_row = f'<div class="head-row"><img data-kind="logo" src="assets/logo.svg" alt=""><h1 data-role="page-title">DMS</h1>{period}</div>'
    top = '<div class="hdr">Project · DMS</div>' if running_header else ""
    top += '<span class="arrow">→</span>' if arrow_top else ""
    measure = lambda which: (f'<figure><img data-kind="measure" data-pair="dms-perf" src="assets/{which}.png" alt="">'
                             f'<figcaption>개선 {"전" if which == "before" else "후"}</figcaption></figure>')
    pair_both = f'<div class="measure-pair" data-role="measure-pair">{measure("before")}{measure("after")}</div>'
    detail = ('<section data-role="project-detail"' + ('' if no_layout else ' data-layout="problem-solving"') + '>'
              '<h2 data-role="section-title">상벌점 조회 성능 개선</h2>'
              '<dl class="steps" data-role="steps"><dt>원인</dt><dd>상관 서브쿼리가 학생마다 다시 실행됐다.</dd>'
              '<dt>해결</dt><dd>서브쿼리를 없애고 최신 이력을 코드에서 골랐다.</dd></dl>'
              + ('' if pair_split else pair_both)
              + (f'<div class="measure-pair" data-role="measure-pair">{measure("after")}</div>' if pair_split else '')
              + filler(3) + '</section>')
    retro = '<section data-role="project-retro"><h2 data-role="section-title">전체 회고</h2><p>측정 조건을 먼저 정해야 한다는 걸 배웠다.</p></section>'
    layout = ' data-layout="profile"' if intro_arrow else ''
    sheet1 = (f'<section class="sheet"{layout}>{top}'
              + ('<p data-role="headline">로컬 부하 테스트에서 학생 목록 조회는 1,225ms → 241ms로 줄였습니다.</p>' if intro_arrow else '')
              + f'<header data-project="dms">{head_row}'
              '<p data-role="project-summary">학생과 교사가 쓰는 기숙사 관리 서비스</p>'
              '<p data-role="project-team">팀 5명 · 본인: 백엔드</p>'
              '<p data-role="project-tech">Kotlin, Spring Boot, PostgreSQL</p></header>'
              + ({"good": f'<p><a href="{link_base}/ok">GitHub 저장소</a> · <a href="mailto:hong@example.com">hong@example.com</a></p>',
                  "plain": '<p>github.com/hong-gildong</p>',
                  "dead": f'<p><a href="{link_base}/gone">배포 주소</a></p>'}.get(links, ""))
              + '<img data-kind="screen" data-project="dms" src="assets/screen.png" alt="" style="width:300px">'
              '<ul data-role="project-features"><li>새벽자습 신청</li><li>상벌점 조회</li></ul>'
              '<section data-role="project-highlights">'
              '<p class="ba" data-role="before-after"><span class="before">1,225ms</span><span class="arrow">→</span><span class="after">241ms</span></p>'
              '<p class="ba-cond" data-role="measure-cond">Gatling, 요청 10개 평균</p>'
              + ('<p>1,000ms → 100ms</p>' if plain_ba else '')
              + ('<p style="font-size:7pt">아주 작은 글자</p>' if small_font else '')
              + ('<img src="assets/tiny.png" alt="" style="width:300px">' if lowres else '')
              + (f'<div class="measure-pair" data-role="measure-pair">{measure("before")}</div>' if pair_split else '')
              + '</section>'
              + ('' if sparse_first else filler(14))
              + ('<div style="border-top:1px solid #000;height:600px"></div>' if ruled_wrapper else '')
              + ('<div data-print-hidden style="height:2000px">빈 자리</div>' if hidden_tall else '')
              + '<div class="pn" data-role="page-number">1 / 2</div></section>')
    diag = lambda f, cap, pair: (f'<figure><img data-kind="diagram"{pair} src="assets/{f}" alt=""><figcaption>{cap}</figcaption></figure>')
    if diagram_pair:                                       # 전·후 구조도: 원본 비율이 다른 두 장
        pair = '' if diagram_pair == "unmarked" else ' data-pair="dms-arch"'
        style = ' style="--pair-ratio: 733 / 960"' if diagram_pair == "ratio" else ''
        wrap = ('<div>{}{}</div>' if diagram_pair == "unmarked" else f'<div class="measure-pair" data-role="measure-pair"{style}>{{}}{{}}</div>')
        detail += wrap.format(diag("tall.png", "전환 전 — 서버 3개", pair), diag("after.png", "전환 후 — 서버 1개", pair))
    sheet3 = ""
    if shapes:                                             # 새 이야기 모양 부품(D-DES-13)이 실측·텍스트 대조를 통과하는지
        sheet3 = (f'<section class="sheet">{SHAPES_HTML}{retro}<div class="pn" data-role="page-number">3 / 3</div></section>')
        body2 = detail + filler(12)
    else:
        body2 = (retro + detail) if retro_first else (detail + retro)
    sheet2 = f'<section class="sheet">{top}{body2}<div class="pn" data-role="page-number">2 / 2</div></section>'
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>테스트</title>'
            '<link rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="components.css"><link rel="stylesheet" href="style.css">'
            f'<style>{PAGE_CSS}</style></head><body>{sheet1}{sheet2}{sheet3}</body></html>')


def export_tests(tmp: Path) -> None:
    lsrv, lbase = link_server()
    out = tmp / "out"
    (out / "assets").mkdir(parents=True)
    for f in ("tokens.css", "components.css"):
        (out / f).write_text((THEME / f).read_text(encoding="utf-8"), encoding="utf-8")
    (out / "style.css").write_text("", encoding="utf-8")
    (out / "assets" / "logo.svg").write_text(SVG)
    png(out / "assets" / "screen.png", 800, 450)
    png(out / "assets" / "before.png", 1600, 900)
    png(out / "assets" / "after.png", 1600, 900)
    png(out / "assets" / "tiny.png", 100, 50)
    png(out / "assets" / "tall.png", 733, 960)
    cases = [
        ("export 정상: 첫머리·순서·짝·여백 통과 (SVG 로고는 흐림 경고 없음)", {}, 0, ("프로젝트 첫머리: 1개 모두", "넘침 없음", "통과:"), ("측정 화면 실패", "실패: 여백", "흐릿함")),
        ("export 작은 래스터 이미지는 흐림 경고 유지", {"lowres": True}, None, ("흐릿함 경고: assets/tiny.png",), ("logo.svg 원본",)),
        ("export 1쪽 자기소개 문장 속 a → b는 경고 안 함 (오탐 회귀)", {"intro_arrow": True}, None, (), ("공통 모양",)),
        ("export 1쪽 자기소개 + 본문 a → b는 경고 유지", {"intro_arrow": True, "plain_ba": True}, None, ("1,000ms → 100ms",), ("1,225ms → 241ms\"가 공통",)),
        ("export 전·후 구조도 크기가 다름 → 실패", {"diagram_pair": "plain"}, 1, ("dms-arch", "크기가 다름"), ()),
        ("export 전·후 구조도 --pair-ratio로 같은 틀 → 통과", {"diagram_pair": "ratio"}, 0, ("통과:",), ("크기가 다름",)),
        ("export 전·후 캡션 이미지에 짝 표시 없음 → 경고", {"diagram_pair": "unmarked"}, None, ("data-pair 없이",), ()),
        ("export 기간이 이름 아래 → 실패", {"period_below": True}, 1, ("다음 글이 한 줄 설명이 아니라",), ()),
        ("export 회고가 세부 설명 앞 → 실패", {"retro_first": True}, 1, ("순서 어긋남",), ()),
        ("export 측정 화면 짝이 다른 쪽 → 실패", {"pair_split": True}, 1, ("갈림",), ()),
        ("export 마지막 아닌 쪽 여백 50% 초과 → 실패", {"sparse_first": True}, 1, ("실패: 여백",), ()),
        ("export 위 선만 있는 빈 래퍼는 채움으로 안 셈 → 여전히 실패 (채움 부풀림 회귀)", {"sparse_first": True, "ruled_wrapper": True}, 1, ("실패: 여백",), ()),
        ("export 반복 머리글 → 경고", {"running_header": True}, None, ("반복됨",), ()),
        ("export 화살표 기호는 머리글 아님 (오탐 회귀)", {"arrow_top": True}, 0, (), ("반복됨",)),
        ("export 8pt 미만 글자 → 실패", {"small_font": True}, 1, ("작은 글자",), ()),
        ("export before→after 공통 모양 아님 → 경고", {"plain_ba": True}, None, ("공통 모양",), ()),
        ("export 인쇄 숨김 요소는 넘침에 안 셈 (회귀)", {"hidden_tall": True}, 0, ("넘침 없음",), ("넘침  sheet",)),
        ("export 링크: 누르면 열리는 링크 → PDF 링크·접속 확인 통과 (D-DES-14)", {"links": "good", "link_base": lbase}, 0, ("PDF 링크: 2개 모두", "접속 확인: 1/1개 열림", "통과:"), ("링크 검사: 실패",)),
        ("export 링크: 주소를 글자로만 씀 → 실패", {"links": "plain"}, 1, ("주소가 링크가 아니다", "github.com/hong-gildong"), ()),
        ("export 링크: 열리지 않는 주소(404) → 실패", {"links": "dead", "link_base": lbase}, 1, ("링크가 열리지 않는다", "404"), ()),
        ("export 세부 설명에 이야기 모양 키 없음 → 사전 검증 실패", {"no_layout": True}, 1, ("data-layout이 없다", "사전 검증 실패"), ("넘침 없음",)),
        ("export 이야기 모양 부품(타임라인·흐름·단계·결정) 렌더·텍스트 대조 통과", {"shapes": True}, 0, ("레이아웃 검사: 통과", "텍스트 대조: 일치", "통과:"), ("작은 글자", "넘침  sheet")),
    ]
    # export.py가 사전 검증 실패 시 PDF를 만들지 않는지: out/ 옆에 facts/를 둔 포트폴리오 구조로 확인
    port = tmp / "pf"
    facts, images = make_facts(tmp, "pf", PROJECT.replace("- logo.svg | 로고 | DMS 로고 `[src: interview]`\n", ""))
    pout = port / "out"
    pout.mkdir()
    for f in ("tokens.css", "components.css"):
        (pout / f).write_text((THEME / f).read_text(encoding="utf-8"), encoding="utf-8")
    (pout / "index.html").write_text(portfolio_html(), encoding="utf-8")
    c, o = run([str(SCRIPTS / "export.py"), str(pout / "index.html"), "a4", str(pout / "x.pdf")])
    check("export 사전 검증 실패면 PDF 안 만듦", c, o, 1, ("사전 검증 실패", "로고"), ("넘침",))
    pdf_made = (pout / "x.pdf").exists()
    results.append(("export 사전 검증 실패 시 PDF 파일 없음", not pdf_made, "ok" if not pdf_made else "PDF가 만들어졌다"))

    # 테마 조합: make_theme.py로 만든 tokens·style로도 같은 HTML이 검사를 통과하는지 (글꼴 로딩 포함)
    for font, heading, accent in (("serif-heading", "bar", "#1e59d6"), ("plex", "rule", "#0f766e"), ("pretendard", "plain", "#be123c")):
        tdir = tmp / f"theme-{font}-{heading}"
        (tdir / "out").mkdir(parents=True)
        (tdir / "design.json").write_text(json.dumps({"style": {"source": "auto", "accent": accent, "font": font, "heading": heading}}), encoding="utf-8")
        c, o = run([str(MAKE_THEME), str(tdir / "design.json"), str(tdir / "out")])
        shutil.copytree(out / "assets", tdir / "out" / "assets")
        (tdir / "out" / "index.html").write_text(portfolio_html(), encoding="utf-8")
        c2, o2 = run([str(SCRIPTS / "export.py"), str(tdir / "out" / "index.html"), "a4", str(tdir / "out" / "x.pdf")])
        fam = {"serif-heading": "Noto Serif KR", "plex": "IBM Plex Sans KR", "pretendard": "Pretendard"}[font]
        check(f"export 테마 {font}+{heading} 통과·글꼴 로딩", c or c2, o + o2, 0, ("통과:", fam), ())

    for i, (name, opts, code, has, lacks) in enumerate(cases):
        html = out / f"case{i}.html"
        html.write_text(portfolio_html(**opts), encoding="utf-8")
        c, o = run([str(SCRIPTS / "export.py"), str(html), "a4", str(out / f"case{i}.pdf")])
        check(name, c, o, code, has, lacks)

    # 레퍼런스 모드(D-DES-16): 디자인 규칙을 어겨도 통과, 내용 문제(링크·넘침)는 그대로 실패
    design_broken = {"period_below": True, "retro_first": True, "sparse_first": True, "small_font": True,
                     "no_layout": True, "running_header": True, "plain_ba": True}
    ref_cases = [
        ("export 레퍼런스 모드: 첫머리·순서·여백·글자·레이아웃 규칙 어겨도 → 통과", design_broken, 0,
         ("레퍼런스 모드", "통과:"), ("실패: 여백", "작은 글자", "순서 어긋남", "data-layout이 없다", "역할 경고", "공통 모양")),
        ("export 레퍼런스 모드: 주소를 글자로만 씀 → 여전히 실패 (내용 검사)", {**design_broken, "links": "plain"}, 1,
         ("레퍼런스 모드", "주소가 링크가 아니다"), ()),
    ]
    for i, (name, opts, code, has, lacks) in enumerate(ref_cases):
        html = out / f"ref{i}.html"
        html.write_text(portfolio_html(**opts), encoding="utf-8")
        c, o = run([str(SCRIPTS / "export.py"), str(html), "a4", str(out / f"ref{i}.pdf"), "--reference"])
        check(name, c, o, code, has, lacks)
    # design.json의 style.source로 레퍼런스 모드를 스스로 켜는지, 넘침(내용 잘림)은 여전히 잡는지
    rp = tmp / "refpf"
    shutil.copytree(out, rp / "out", ignore=shutil.ignore_patterns("*.pdf", "*.html"))
    (rp / "design.json").write_text(json.dumps({"style": {"source": "reference", "reference": "ref.pdf"}}), encoding="utf-8")
    (rp / "out" / "index.html").write_text(portfolio_html(**design_broken).replace(
        '<div class="pn" data-role="page-number">1 / 2</div>', '<div style="height:3000px">넘침</div><div class="pn" data-role="page-number">1 / 2</div>'), encoding="utf-8")
    c, o = run([str(SCRIPTS / "export.py"), str(rp / "out" / "index.html"), "a4", str(rp / "out" / "x.pdf")])
    check("export design.json source=reference → 레퍼런스 모드, 넘침은 여전히 실패", c, o, 1, ("레퍼런스 모드", "넘침  sheet 1"), ("data-layout이 없다",))
    lsrv.shutdown()
    lsrv.server_close()


# ---------- facts 픽스처 ----------

PROFILE = """---
kind: profile
---
## 기본 정보
- 이름: 홍길동 `[src: interview]`

## 활동
- 교내 해커톤 운영진 | 교내 | 2025.03 ~ 2025.06 | 접수 페이지 개발 `[src: interview]`

## 수상·자격증
- 정보처리기능사 | 2025.09.30 | (기관 미기재) `[src: interview]`
"""

PROJECT = """---
project: DMS
slug: dms
start: 2026.03
end:
status: 운영 중
type: 팀
depth: deep
---
## 개요
- 기숙사 관리 서비스 `[src: interview]`

## 사용 기술
- Kotlin, Spring Boot, PostgreSQL `[src: interview]`

## 주요 기능
- 새벽자습 신청 `[src: interview]`

## 작업
### 상벌점 조회 성능 개선
- 상황: 조회가 느렸다 `[src: interview]`
- 원인: 상관 서브쿼리 / 확인 방법: EXPLAIN ANALYZE
- 해결: 서브쿼리 제거
- 결과: 1,225ms → 241ms / 측정: Gatling, 요청 10개 평균

## 이미지
- logo.svg | 로고 | DMS 로고 `[src: interview]`
- screen.png | 서비스 화면 | 신청 화면 `[src: interview]`
- before.png | 측정 화면 | 상벌점 조회 Gatling (개선 전) `[src: interview]`
- after.png | 측정 화면 | 상벌점 조회 Gatling (개선 후) `[src: interview]`
"""


def make_facts(tmp: Path, name: str, project: str = PROJECT, profile: str = PROFILE) -> tuple[Path, Path]:
    base = tmp / name
    facts, images = base / "facts", base / "images"
    facts.mkdir(parents=True)
    images.mkdir()
    (facts / "profile.md").write_text(profile, encoding="utf-8")
    (facts / "dms.md").write_text(project, encoding="utf-8")
    (images / "logo.svg").write_text(SVG)
    for f in ("screen.png", "before.png", "after.png"):
        png(images / f, 40, 20)
    return facts, images


def facts_tests(tmp: Path) -> None:
    lint = str(SCRIPTS / "facts_lint.py")
    variants = [
        ("facts_lint 정상", PROJECT, PROFILE, 0, ("ERROR 0",), ()),
        ("facts_lint 로고 없음 → ERROR", PROJECT.replace("- logo.svg | 로고 | DMS 로고 `[src: interview]`\n", ""), PROFILE, 1, ("로고가 없다",), ()),
        ("facts_lint '로고 없음' 기록은 통과", PROJECT.replace("- logo.svg | 로고 | DMS 로고 `[src: interview]`", "- 로고 없음 `[src: interview]`"), PROFILE, 0, ("ERROR 0",), ()),
        ("facts_lint 옛 period → WARN만", PROJECT.replace("start: 2026.03\nend:\n", "period: 2026.03 ~ 진행 중\n"), PROFILE, 0, ("옛 기간 형식",), ()),
        ("facts_lint status 잘못 → ERROR", PROJECT.replace("status: 운영 중", "status: 진행 중"), PROFILE, 1, ("› status", "ERROR[확인]"), ()),
        ("facts_lint 종료인데 end 없음 → ERROR", PROJECT.replace("status: 운영 중", "status: 종료"), PROFILE, 1, ("end",), ()),
        ("facts_lint 이미지 파일 없음 → ERROR", PROJECT.replace("screen.png |", "missing.png |"), PROFILE, 1, ("missing.png", "없다"), ()),
        ("facts_lint 충돌 남음 → ERROR", PROJECT + "\n## 개요2\n- 사용자 200명 `[status: 충돌]`\n", PROFILE, 1, ("충돌",), ()),
        ("facts_lint 프로필 표시 없음 → ERROR[수정]", PROJECT, PROFILE.replace("---\nkind: profile\n---\n", ""), 1, ("ERROR[수정]", "kind: profile"), ()),
        ("facts_lint 프로젝트 이름 없음 → ERROR[확인]", PROJECT.replace("project: DMS\n", ""), PROFILE, 1, ("ERROR[확인]", "› project"), ()),
        ("facts_lint 날짜 표기 다름 → ERROR[수정] + 제안", PROJECT.replace("start: 2026.03", "start: 2026-3"), PROFILE, 1, ("ERROR[수정]", "start: 2026.03"), ()),
        ("facts_lint 날짜 알아볼 수 없음 → ERROR[확인]", PROJECT.replace("start: 2026.03", "start: 작년 봄"), PROFILE, 1, ("ERROR[확인]", "› start"), ()),
        ("facts_lint 종료일이 시작일보다 이름 → ERROR", PROJECT.replace("end:\nstatus: 운영 중", "end: 2025.12\nstatus: 종료"), PROFILE, 1, ("시작일", "보다 이르다"), ()),
        ("facts_lint 진행 중인데 종료일 있음 → ERROR", PROJECT.replace("end:\n", "end: 2026.12\n"), PROFILE, 1, ("종료일",), ()),
        ("facts_lint 사용 기술 전무 → ERROR[확인]", PROJECT.replace("## 사용 기술\n- Kotlin, Spring Boot, PostgreSQL `[src: interview]`\n", ""), PROFILE, 1, ("› 사용 기술", "ERROR[확인]"), ()),
        ("facts_lint 기술 선택만 있음 → WARN", PROJECT.replace("## 사용 기술\n- Kotlin, Spring Boot, PostgreSQL `[src: interview]`\n", "## 기술 선택\n### PostgreSQL\n- 이유: 벡터 검색\n"), PROFILE, 0, ("WARN", "› 사용 기술"), ("ERROR[확인]  dms.md › 사용 기술",)),
        ("facts_lint 활동 칸 없음 → ERROR[확인] (D-P1-4)", PROJECT, PROFILE.split("## 활동")[0] + "## 수상·자격증" + PROFILE.split("## 수상·자격증")[1], 1, ("› 활동", "아직 묻지 않았다"), ()),
        ("facts_lint 수상에 날짜 없음 → ERROR[확인]", PROJECT, PROFILE.replace("정보처리기능사 | 2025.09.30 |", "정보처리기능사 |"), 1, ("수상·자격증.정보처리기능사", "날짜가 없다"), ()),
        ("facts_lint 활동에 기간 없음 → ERROR[확인]", PROJECT, PROFILE.replace("2025.03 ~ 2025.06 |", "|"), 1, ("활동.교내 해커톤 운영진", "날짜가 없다"), ()),
        ("facts_lint '활동 없음' 기록은 통과", PROJECT, PROFILE.replace("- 교내 해커톤 운영진 | 교내 | 2025.03 ~ 2025.06 | 접수 페이지 개발 `[src: interview]`", "- 활동 없음 `[src: interview]`"), 0, ("ERROR 0",), ()),
        ("facts_lint 이미지 종류 오류 → ERROR[수정]", PROJECT.replace("screen.png | 서비스 화면", "screen.png | 스크린샷"), PROFILE, 1, ("허용되지 않는 이미지 종류", "ERROR[수정]"), ()),
    ]
    for i, (name, proj, prof, code, has, lacks) in enumerate(variants):
        facts, images = make_facts(tmp, f"lint{i}", proj, prof)
        c, o = run([lint, str(facts), "--images", str(images)])
        check(name, c, o, code, has, lacks)

    # 폴더에 기록 안 된 파일이 있어도 로고로 추측 등록하지 않게 안내 (2026-10-09 E2E: 로고를 묻지 않고 [src: interview]로 등록)
    facts, images = make_facts(tmp, "unlisted", PROJECT.replace("- logo.svg | 로고 | DMS 로고 `[src: interview]`\n", ""))
    (images / "dms").mkdir()
    png(images / "dms" / "dms-logo.png", 40, 40)
    c, o = run([lint, str(facts), "--images", str(images)])
    check("facts_lint 기록 안 된 폴더 파일 → 추측 등록 말고 확인", c, o, 1,
          ("ERROR[확인]", "› 이미지.로고", "dms-logo.png", "확인받은 뒤", "[src: interview]`를 달지 않는다"), ())
    facts, images = make_facts(tmp, "unlisted2")
    (images / "dms").mkdir()
    png(images / "dms" / "extra.png", 40, 40)
    c, o = run([lint, str(facts), "--images", str(images)])
    check("facts_lint 필수 이미지가 다 있으면 폴더 파일로 오류 안 냄", c, o, 0, ("ERROR 0",), ("extra.png",))

    facts, images = make_facts(tmp, "cache")
    cache = tmp / "cache" / ".facts_lint.json"
    run([lint, str(facts), "--images", str(images), "--cache", str(cache)])
    c, o = run([lint, str(facts), "--images", str(images), "--cache", str(cache)])
    check("facts_lint 같은 입력이면 캐시 재사용", c, o, 0, ("재사용",), ())
    (facts / "dms.md").write_text(PROJECT.replace("status: 운영 중", "status: 진행 중"), encoding="utf-8")
    c, o = run([lint, str(facts), "--images", str(images), "--cache", str(cache)])
    check("facts_lint 기록이 바뀌면 캐시 무효", c, o, 1, ("› status",), ("재사용",))
    facts, images = make_facts(tmp, "cache2")
    cache = tmp / "cache2" / ".facts_lint.json"
    run([lint, str(facts), "--images", str(images), "--cache", str(cache)])
    c, o = run([lint, str(facts), "--images", str(images), "--cache", str(cache)])
    check("facts_lint 이미지가 그대로면 캐시 재사용", c, o, 0, ("재사용",), ())
    before = (images / "screen.png").read_bytes()
    raw = bytearray(before)
    raw[-20] ^= 0xFF                                       # 크기는 같고 내용만 다른 파일로 교체
    (images / "screen.png").write_bytes(bytes(raw))
    same_size = len(raw) == len(before) and bytes(raw) != before
    c, o = run([lint, str(facts), "--images", str(images), "--cache", str(cache)])
    check("facts_lint 같은 크기 이미지로 바꿔도 캐시 무효", c if same_size else -1, o, 0, ("ERROR 0",), ("재사용",))

    facts, _ = make_facts(tmp, "stats", PROJECT, PROFILE.replace("---\nkind: profile\n---\n", ""))
    c, o = run([str(SCRIPTS / "facts_stats.py"), str(facts)])
    check("facts_stats profile.md는 kind 없어도 프로젝트로 안 셈", c, o, 0, ("| DMS |",), ("| profile |",))

    facts, _ = make_facts(tmp, "numbers")
    html = tmp / "numbers.html"
    html.write_text('<html><head><title>제목 2026</title></head><body><p>평균 1,225ms → 241ms</p></body></html>', encoding="utf-8")
    c, o = run([str(SCRIPTS / "check_numbers.py"), str(html), str(facts)])
    check("check_numbers 기록에 있는 수치·title 무시 → 0건", c, o, 0, ("문제 0건",), ())
    html.write_text('<html><body><p>평균 999ms, 원문 "약 53%"</p></body></html>', encoding="utf-8")
    c, o = run([str(SCRIPTS / "check_numbers.py"), str(html), str(facts)])
    check("check_numbers 없는 수치 MISSING·출처 메모 INTERNAL", c, o, 1, ("MISSING", "INTERNAL"), ())
    # 단위까지 대조 (리뷰 2026-10-10: 기록의 "포트 80"으로 본문 "80% 개선"이 통과했다)
    nf = tmp / "numbers-unit"
    nf.mkdir()
    (nf / "a.md").write_text("- 서버 포트 80 `[src: interview]`\n- 결과: 1,225 → 241ms / 측정: 요청 10개 평균\n"
                             "- 비용을 절반으로 줄였다\n- start: 2026.03\n- 오류율 12% `status: 근거없음`\n", encoding="utf-8")
    def nums(name, body, code, has=(), lacks=()):
        html.write_text(f"<html><body>{body}</body></html>", encoding="utf-8")
        c, o = run([str(SCRIPTS / "check_numbers.py"), str(html), str(nf)])
        check(name, c, o, code, has, lacks)
    nums("check_numbers 다른 단위로 기록된 수치(포트 80 → 80%) → MISSING", "<p>응답 시간 80% 개선</p>", 1, ("80%",))
    nums("check_numbers 같은 줄 단위 공유(1,225 → 241ms)·표기 차이·연도·1개 → 통과",
         "<p>1,225ms → 241 밀리초, 요청 10개</p><p>2026년 3월, DB 1개</p><p>비용 절반</p>", 0, ("문제 0건",))
    nums("check_numbers 기록에 없는 한글 수량어(두 배) → MISSING", "<p>속도가 두 배 빨라졌다</p>", 1, ("두 배",))
    nums("check_numbers 근거없음 줄의 수치는 단위가 맞아도 UNVERIFIED", "<p>오류율 12%</p>", 1, ("UNVERIFIED",))
    nums("check_numbers 기록을 세어 쓴 개수(DB 2개) → MISSING (R-EVD-1)", "<p>서버 3대, DB 2개</p>", 1, ("2개",))
    nums("check_numbers '배포'의 '배'는 단위 아님 (오탐 회귀)", "<p>10배포</p>", 0, ("문제 0건",))


def pair_tests(tmp: Path) -> None:
    """audit/scripts/pair_blocks.py — 본문 블록과 기록 섹션을 나란히 놓는 감사 대조표."""
    pb = ROOT / "skills" / "audit" / "scripts" / "pair_blocks.py"
    facts = tmp / "pair-facts"
    facts.mkdir()
    (facts / "dms.md").write_text(
        "## 개요\n- 기숙사 관리 서비스\n\n## 작업\n### 조회 개선, 2차\n- 결과: 1,225ms → 241ms\n"
        "### 다음 작업\n- 알림 정리\n\n## 회고\n> 측정 조건을 먼저 정해야 한다는 걸 배웠다.\n", encoding="utf-8")
    (facts / "profile.md").write_text("## 기본 정보\n- 이름: 홍길동\n", encoding="utf-8")

    def pair(name, body, code, has=(), lacks=()):
        html = tmp / "pair.html"
        html.write_text(f"<html><head><title>제목은 근거 표시가 없어도 되는 긴 문장입니다</title></head><body>{body}</body></html>", encoding="utf-8")
        c, o = run([str(pb), str(html), str(facts)])
        check(name, c, o, code, has, lacks)
        return o

    o = pair("pair_blocks 근거 블록 → PAIR와 기록 섹션 원문",
             '<p data-fact="dms.md#개요">학생과 교사가 쓰는 <b>기숙사</b> 관리 서비스</p>', 0,
             ("## PAIR 1 — dms.md#개요", "학생과 교사가 쓰는 기숙사 관리 서비스", "- 기숙사 관리 서비스", "깨진 참조 0"))
    pair("pair_blocks 하위 섹션까지 포함하고 같은 단계 제목에서 멈춤",
         '<p data-fact="dms.md#작업">작업 요약</p>', 0, ("조회 개선, 2차", "다음 작업", "1,225ms"), ("## 회고",))
    pair("pair_blocks 제목에 쉼표가 있어도 근거 여럿을 바르게 나눔",
         '<p data-fact="dms.md#조회 개선, 2차, profile.md#기본 정보">홍길동은 조회를 241ms로 줄였다</p>', 0,
         ("<!-- dms.md#조회 개선, 2차 -->", "<!-- profile.md#기본 정보 -->", "깨진 참조 0"), ("BROKEN",))
    pair("pair_blocks 헤드라인 블록에 [헤드라인] 표시",
         '<p data-fact="dms.md#개요" data-role="headline">기숙사 서비스를 운영합니다</p>', 0, ("[헤드라인]",))
    pair("pair_blocks 없는 섹션·없는 파일 → BROKEN, 종료 1",
         '<p data-fact="dms.md#없는 제목">a</p><p data-fact="nope.md#개요">b</p>', 1,
         ("## BROKEN 1", "없는 근거: dms.md#없는 제목", "## BROKEN 2", "깨진 참조 2"))
    pair("pair_blocks 근거 하나라도 없으면 BROKEN (여럿 중)",
         '<p data-fact="dms.md#개요, dms.md#없음">a</p>', 1, ("없는 근거: dms.md#없음",), ("없는 근거: dms.md#개요",))
    pair("pair_blocks 근거 없는 긴 문장 → UNATTRIBUTED, 짧은 글·제목·title·data-nocheck는 제외",
         '<h2>근거 표시가 없는 아주 긴 섹션 제목 문장입니다</h2><p>근거 표시 없이 쓴 스무 자가 넘는 사실 서술 문장이다</p>'
         '<p>짧은 글</p><p data-nocheck>쪽 번호처럼 검사에서 빼는 아주 긴 장식 문장입니다</p>', 0,
         ("## UNATTRIBUTED\n근거 표시 없이 쓴", "근거 미표시 1"), ("섹션 제목 문장", "장식 문장", "title", "짧은 글"))
    pair("pair_blocks 중첩 블록의 글은 바깥 블록에도 들어감",
         '<div data-fact="dms.md#작업"><p>바깥 글</p><p data-fact="dms.md#개요">안쪽 글</p></div>', 0,
         ("## PAIR 1 — dms.md#작업\n\n### 본문\n바깥 글안쪽 글", "## PAIR 2 — dms.md#개요\n\n### 본문\n안쪽 글"))
    pair("pair_blocks 회고를 바꿔 쓰면 RETRO 차이 표시",
         '<p data-fact="dms.md#회고">측정 조건을 반드시 먼저 정해야 한다는 걸 배웠다.</p>', 0, ("## RETRO", "+반드시"))
    pair("pair_blocks 회고 원문 그대로면 RETRO 없음",
         '<p data-fact="dms.md#회고">측정 조건을 먼저 정해야 한다는 걸 배웠다.</p>', 0, ("## PAIR 1",), ("## RETRO",))


def provenance_tests(tmp: Path) -> None:
    """근거 원문(D-TXT-6): 훅 hooks/log_answers.py가 사용자 말을 남기고, facts_lint.py가 기록의 수치를 대조한다. 환경 점검도 여기서."""
    import os
    hook = ROOT / "hooks" / "log_answers.py"
    cwd = tmp / "prov"
    (cwd / "portfolio").mkdir(parents=True)
    tr = tmp / "prov-session.jsonl"
    rows = [
        {"type": "user", "timestamp": "2026-10-10T09:00:00Z", "message": {"content": "포트폴리오 만들어줘. DMS에서 조회를 1,225ms에서 241ms로 줄였어"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "모델이 말한 9,999ms"},
                                                      {"type": "tool_use", "id": "ask1", "name": "AskUserQuestion", "input": {}}]}},
        {"type": "user", "toolUseResult": {"questions": [{"question": "모델 질문 8,888명?"}], "answers": {"모델 질문 8,888명?": "월 사용자 약 300명"},
                                           "annotations": {"모델 질문 8,888명?": {"notes": "학생 수 기준 650명"}}},
         "message": {"content": [{"type": "tool_result", "tool_use_id": "ask1", "content": "모델 질문 8,888명?=월 사용자 약 300명"}]}},
        {"type": "user", "message": {"content": "<task-notification>배경 작업 7,777건 완료</task-notification>"}},
        {"type": "user", "isMeta": True, "message": {"content": "메타 6,666"}},
        {"type": "user", "message": {"content": "그리고 배포는 2026년 3월에 했어"}},
    ]
    tr.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    def fire(ev: dict) -> int:
        p = subprocess.run([sys.executable, "-I", str(hook)], input=json.dumps(ev, ensure_ascii=False), capture_output=True, text=True, timeout=30)
        return p.returncode
    log = cwd / "portfolio" / "sources" / "interview-log.md"
    code = fire({"hook_event_name": "Stop", "cwd": str(tmp / "no-portfolio"), "transcript_path": str(tr)})
    results.append(("log_answers portfolio/ 없는 폴더에는 아무것도 안 씀", code == 0 and not (tmp / "no-portfolio").exists(), f"code {code}"))
    code = fire({"hook_event_name": "Stop", "cwd": str(cwd), "transcript_path": str(tr)})
    text = log.read_text(encoding="utf-8") if log.exists() else ""
    ok = (code == 0 and "1,225ms에서 241ms" in text and "월 사용자 약 300명" in text and "학생 수 기준 650명" in text
          and "배포는 2026년 3월" in text)
    results.append(("log_answers 사용자 메시지·고른 답·메모를 원문 그대로 남김", ok, text[-400:]))
    leaked = [x for x in ("9,999", "8,888", "7,777", "6,666") if x in text]
    results.append(("log_answers 모델 말·질문 문장·작업 알림·메타는 안 남김", not leaked, f"샌 것: {leaked}"))
    n = text.count("\n## ")
    fire({"hook_event_name": "Stop", "cwd": str(cwd), "transcript_path": str(tr)})
    fire({"hook_event_name": "UserPromptSubmit", "cwd": str(cwd), "transcript_path": str(tr), "prompt": "그리고 배포는 2026년 3월에 했어"})
    results.append(("log_answers 같은 글은 한 번만", log.read_text(encoding="utf-8").count("\n## ") == n, f"{n} → {log.read_text(encoding='utf-8').count(chr(10) + '## ')}"))
    fire({"hook_event_name": "UserPromptSubmit", "cwd": str(cwd), "prompt": "팀은 4명이었어"})
    fire({"hook_event_name": "PostToolUse", "cwd": str(cwd), "tool_name": "AskUserQuestion",
          "tool_response": {"questions": [{"question": "q 5,555?"}], "answers": {"q 5,555?": "p95 기준 512ms"}}})
    text = log.read_text(encoding="utf-8")
    results.append(("log_answers 이번 메시지·이번 질문 답(질문 문장 제외)도 바로 남김", "팀은 4명" in text and "p95 기준 512ms" in text and "5,555" not in text, text[-300:]))
    code = fire({"hook_event_name": "Stop", "cwd": str(cwd), "transcript_path": str(tmp / "없는.jsonl")})
    code2 = subprocess.run([sys.executable, "-I", str(hook)], input="JSON 아님", capture_output=True, text=True, timeout=30).returncode
    results.append(("log_answers 기록이 없거나 입력이 깨져도 종료 0", code == 0 and code2 == 0, f"{code}, {code2}"))

    # 근거 원문 보호(guard_log.py): 모델이 근거 원문을 고치려는 도구 호출은 종료 코드 2로 막는다
    guard = ROOT / "hooks" / "guard_log.py"
    lp = str(log)

    def blocked(tool: str, inp: dict) -> bool:
        p = subprocess.run([sys.executable, "-I", str(guard)], input=json.dumps({"tool_name": tool, "tool_input": inp}, ensure_ascii=False),
                           capture_output=True, text=True, timeout=30)
        return p.returncode == 2 and "D-TXT-6" in p.stderr
    must_block = [("Write", {"file_path": lp, "content": "x"}), ("Edit", {"file_path": lp, "old_string": "a", "new_string": "b"}),
                  ("Write", {"file_path": str(log.parent / ".interview-log.json"), "content": "{}"}),
                  ("Bash", {"command": f"echo '- 9,999ms' >> {lp}"}), ("Bash", {"command": f"sed -i 's/1/2/' {lp}"}),
                  ("Bash", {"command": f"rm {lp}"}), ("Bash", {"command": f"cat x | tee -a {lp}"}),
                  ("Bash", {"command": f"python3 -c \"open('{lp}','a').write('1')\""}), ("Bash", {"command": f"cat {lp} > /tmp/a && mv /tmp/a {lp}"})]
    must_pass = [("Read", {"file_path": lp}), ("Bash", {"command": f"cat {lp}"}), ("Bash", {"command": f"grep -n 241 {lp} | head"}),
                 ("Write", {"file_path": str(facts_dir := cwd / "portfolio" / "facts" / "dms.md"), "content": "x"}),
                 ("Bash", {"command": "ls portfolio/sources && python3 facts_lint.py portfolio/facts"}), ("Bash", {"command": "echo hi > out.txt"})]
    wrong = [f"{t} {i}" for t, i in must_block if not blocked(t, i)] + [f"(막힘) {t} {i}" for t, i in must_pass if blocked(t, i)]
    results.append((f"guard_log 근거 원문 쓰기 {len(must_block)}가지 막고 읽기·다른 파일 {len(must_pass)}가지는 통과", not wrong, "; ".join(wrong)[:600]))
    p = subprocess.run([sys.executable, "-I", str(guard)], input="깨진 입력", capture_output=True, text=True, timeout=30)
    results.append(("guard_log 입력이 깨지면 막지 않음(종료 0)", p.returncode == 0, f"code {p.returncode}"))

    # facts_lint 대조
    facts = cwd / "portfolio" / "facts"
    facts.mkdir()
    (facts / "profile.md").write_text(PROFILE, encoding="utf-8")
    (cwd / "portfolio" / "sources" / "web-blog.md").write_text("서버 비용 월 $30.37, Spring Boot 3.2.3", encoding="utf-8")
    lint = SCRIPTS / "facts_lint.py"

    def prov(name, lines, code, has=(), lacks=()):
        (facts / "dms.md").write_text(PROJECT + "\n## 추가\n" + lines + "\n", encoding="utf-8")
        c, o = run([str(lint), str(facts)])
        check(name, c, o, code, has, lacks)
    base_ok = ("- 조회 1,225ms → 241ms `[src: interview]`\n- 월 사용자 약 300명, 학생 650명 `[src: interview]`\n"
               "- 팀 4명, p95 512ms `[src: interview]`\n- 비용 $30.37, Boot 3.2 `[src: doc:web-blog.md]`\n- 배포 2026.03 `[src: interview]`")
    # PROJECT 픽스처 자체의 줄(요청 10개 등)은 이 근거 원문에 없어 ERROR가 날 수 있으므로 종료 코드는 보지 않는다
    prov("facts_lint 근거 원문·받은 자료에 있는 수치 → 대조 통과", base_ok, None, (), ("없는 수치 1,225", "없는 수치 300", "없는 수치 30.37", "없는 수치 3.2", "없는 수치 2026.03"))
    prov("facts_lint 사용자가 연도 없이 말한 날짜에 연도를 붙임 → ERROR[확인]", "- 출시 2025.03 `[src: interview]`", 1, ("없는 수치 2025.03",))
    prov("facts_lint 지어낸 수치 → ERROR[확인]", "- 응답 시간 4,321ms로 개선 `[src: interview]`", 1, ("ERROR[확인]", "없는 수치 4,321"))
    prov("facts_lint 모델이 말하거나 질문에만 쓴 수치(9,999·8,888)는 근거 아님", "- 9,999ms, 8,888명 `[src: interview]`", 1, ("9,999", "8,888"))
    prov("facts_lint 다른 자료에 있는 수치 → 출처 태그 ERROR[수정]", "- 비용 $30.37 `[src: interview]`", 1, ("ERROR[수정]", "doc:web-blog.md"))
    prov("facts_lint 개선 전·후가 원문 한 곳에 같이 없음 → ERROR[확인]", "- 조회 300ms → 241ms `[src: interview]`", 1, ("원문 한 곳에 같이",))
    prov("facts_lint 이미지 자료가 근거인 줄은 WARN만", "- Gatling 13:57 결과 `[src: doc:img-gatling.png, interview]`", None, ("이미지 자료에서 읽은 수치",), ("없는 수치 13",))
    prov("facts_lint 이미지 목록·URL·파일 이름의 숫자는 대조 안 함", "- 블로그 https://velog.io/@a/post-2024 참고 `[src: interview]`", None, (), ("2024",))
    log.unlink()
    prov("facts_lint 근거 원문 기록이 없으면 대조 건너뜀(WARN, 옛 기록)", "- 응답 시간 4,321ms `[src: interview]`", None, ("대조를 건너뛴다",), ("없는 수치",))

    # 환경 점검
    c, o = run([str(SCRIPTS / "env_check.py"), "--offline"], env={"PATH": str(tmp / "empty-bin")})
    check("env_check Chrome·poppler 없으면 실패 + 설치 안내", c, o, 1, ("Chrome/Chromium이 없다", "poppler", "설치:", "환경 점검: 실패"))
    c, o = run([str(SCRIPTS / "env_check.py"), "--offline"])
    check("env_check 이 개발 환경 → 통과", c, o, 0 if shutil.which("pdfinfo") and any(shutil.which(n) for n in ("google-chrome", "chromium")) else None, ("Python",))


def image_tests(tmp: Path) -> None:
    d = tmp / "imgs"
    d.mkdir()
    png(d / "tall.png", 390, 844)
    (d / "logo.svg").write_text(SVG)
    c, o = run([str(SCRIPTS / "image_info.py"), str(d)])
    check("image_info PNG 크기·SVG viewBox", c, o, 0, ("390×844", "세로형", "120×40", "벡터"), ())


def theme_tests(tmp: Path) -> None:
    """design/scripts/make_theme.py — 레퍼런스 유무에 따른 테마 생성과 검사."""
    variants = json.loads((THEME / "variants.json").read_text(encoding="utf-8"))
    bad = []
    for font in variants["fonts"]:
        for heading in variants["headings"]:
            for accent in variants["accents"].values():
                d = tmp / f"t-{font}-{heading}-{accent[1:]}"
                d.mkdir()
                (d / "design.json").write_text(json.dumps({"style": {"source": "auto", "accent": accent, "font": font, "heading": heading}}))
                c, o = run([str(MAKE_THEME), str(d / "design.json"), str(d / "theme")])
                c2, o2 = run([str(MAKE_THEME), "--check", str(d / "design.json"), str(d / "theme")])
                if c or c2 or not (d / "theme" / "style.css").exists():
                    bad.append(f"{font}/{heading}/{accent}: {o}{o2}")
    n = len(variants["fonts"]) * len(variants["headings"]) * len(variants["accents"])
    results.append((f"make_theme 검증된 조합 {n}개 모두 생성·대비·최신 검사 통과", not bad, "ok" if not bad else "\n".join(bad[:3])))

    def case(name, style, code, has=(), lacks=(), extra=None):
        d = tmp / f"tc-{len(results)}"
        d.mkdir()
        if extra is not None:
            (d / "theme").mkdir()
            (d / "theme" / "extra.css").write_text(extra)
        (d / "design.json").write_text(json.dumps({"style": style}, ensure_ascii=False))
        c, o = run([str(MAKE_THEME), str(d / "design.json"), str(d / "theme")])
        check(name, c, o, code, has, lacks)
        return d
    case("make_theme 레퍼런스 없는데 팔레트 밖 강조색 → 실패", {"source": "auto", "accent": "#123456", "font": "plex", "heading": "bar"}, 1, ("accents 중에서",))
    # 레퍼런스는 그대로 따른다(D-DES-16): 대비·글자 범위·장식 금지 선언을 검사하지 않는다
    case("make_theme 레퍼런스 색 대비 부족도 그대로 → 통과 (D-DES-16)", {"source": "reference", "accent": "#7fb2ff", "font": "plex", "heading": "bar"}, 0, ("테마 작성",))
    case("make_theme 레퍼런스 글자 크기 범위 밖도 그대로 → 통과", {"source": "reference", "accent": "#1e59d6", "font": "plex", "heading": "bar", "fontScale": {"body": "9pt"}}, 0, ("테마 작성",))
    case("make_theme 레퍼런스 배치 CSS에 font-size·.sheet → 통과", {"source": "reference", "accent": "#1e59d6", "font": "plex", "heading": "bar", "extraCss": "theme/extra.css"},
         0, ("테마 작성",), extra=':root [data-role="section-title"] { font-size: 30pt; } .sheet { display: grid; }')
    case("make_theme 레퍼런스도 색 형식은 검사 → 실패", {"source": "reference", "accent": "blue", "font": "plex", "heading": "bar"}, 1, ("#rrggbb",))
    case("make_theme 사용자 선택 글자 크기 범위 밖 → 실패", {"source": "user", "accent": "#1e59d6", "font": "plex", "heading": "bar", "fontScale": {"body": "9pt"}}, 1, ("D-DES-3",))
    d = case("make_theme 레퍼런스 글꼴·색·장식 → 통과", {"source": "reference", "reference": "ref.pdf", "accent": "#1e59d6",
             "font": {"imports": ["https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap"], "body": "\"Gowun Dodum\", sans-serif", "display": None},
             "heading": "bar", "colors": {"text": "#1a1c22"}, "fontScale": {"section": "21pt"}, "extraCss": "theme/extra.css"},
             0, ("테마 작성",), extra=':root [data-role="section-title"] { letter-spacing: -.01em; }')
    tok = (d / "theme" / "tokens.css").read_text()
    ok = "Gowun+Dodum" in tok and "--fs-section: 21pt;" in tok and "--text: #1a1c22;" in tok and "letter-spacing" in (d / "theme" / "style.css").read_text()
    results.append(("make_theme 레퍼런스 값이 tokens·style에 들어감", ok, "ok" if ok else tok[:400]))
    (d / "theme" / "tokens.css").write_text(tok.replace("--accent: #1e59d6", "--accent: #000000"))
    c, o = run([str(MAKE_THEME), "--check", str(d / "design.json"), str(d / "theme")])
    check("make_theme --check 손으로 고친 테마 감지", c, o, 1, ("tokens.css",), ())
    # 전체 스타일·사용자 선택 (D-DES-15)
    bad = []
    for look in variants["looks"]:
        d = tmp / f"look-{look}"
        d.mkdir()
        (d / "design.json").write_text(json.dumps({"style": {"source": "user", "look": look, "accent": "#1e59d6", "font": "pretendard", "heading": "rule"}}))
        c, o = run([str(MAKE_THEME), str(d / "design.json"), str(d / "theme")])
        if c or f"look-{look}" not in "".join(o) and f"전체 스타일: {look}" not in (d / "theme" / "style.css").read_text():
            bad.append(f"{look}: {o}")
    results.append((f"make_theme 전체 스타일 {len(variants['looks'])}개 모두 생성", not bad, "ok" if not bad else "\n".join(bad[:3])))
    case("make_theme 없는 전체 스타일 → 실패", {"source": "user", "look": "neon", "accent": "#1e59d6", "font": "plex", "heading": "bar"}, 1, ("전체 스타일",))
    case("make_theme 사용자 선택은 팔레트 밖 강조색도 대비만 통과하면 → 통과", {"source": "user", "look": "minimal", "accent": "#123456", "font": "plex", "heading": "bar"}, 0, ("테마 작성",))
    case("make_theme 사용자 선택도 대비 부족 강조색 → 실패", {"source": "user", "look": "minimal", "accent": "#7fb2ff", "font": "plex", "heading": "bar"}, 1, ("4.5:1",))
    d = case("make_theme 컬러 띠: 띠 색·대비가 tokens에 들어감", {"source": "user", "look": "color-band", "accent": "#0f766e", "font": "myeongjo-heading", "heading": "plain"}, 0, ("띠 #0f766e",))
    tok = (d / "theme" / "tokens.css").read_text()
    ok = "--band-bg: #0f766e;" in tok and "Nanum+Myeongjo" in tok and "look-color-band" not in tok and "머리 띠" in (d / "theme" / "style.css").read_text()
    results.append(("make_theme 컬러 띠 토큰·스타일", ok, "ok" if ok else tok[:300]))


def env_tests(tmp: Path) -> None:
    """scripts/test_env.py — 진짜 ~/.claude 대신 임시 폴더(HARNESS_TEST_CLAUDE_DIR)로 검증한다."""
    import json as _json
    script = str(ROOT / "scripts" / "test_env.py")
    other_hook = {"hooks": [{"type": "command", "command": "echo other"}]}
    wiki_hook = {"hooks": [{"type": "command", "command": "jq --rawfile idx /x/my-wiki/wiki/index.md"}]}

    def setup(name, wiki=True, omc=True, md=True):
        d = tmp / name
        d.mkdir()
        settings = {"model": "x", "hooks": {"UserPromptSubmit": [other_hook] + ([wiki_hook] if wiki else []),
                                            "Stop": [other_hook]},
                    "enabledPlugins": {"oh-my-claudecode@omc": omc, "figma@x": True}, "theme": "dark"}
        (d / "settings.json").write_text(_json.dumps(settings, ensure_ascii=False, indent=2))
        if md:
            (d / "CLAUDE.md").write_text("전역 규칙\n")
        return d, settings

    d, orig = setup("env1")
    e = {"HARNESS_TEST_CLAUDE_DIR": str(d)}
    c, o = run([script, "start"], env=e)
    st = _json.loads((d / "settings.json").read_text())
    ok = (c == 0 and len(st["hooks"]["UserPromptSubmit"]) == 1 and st["enabledPlugins"]["oh-my-claudecode@omc"] is False
          and st["enabledPlugins"]["figma@x"] is True and not (d / "CLAUDE.md").exists() and (d / "harness-test" / "state.json").exists())
    results.append(("test_env start: 위키 훅·OMC·CLAUDE.md만 끄고 나머지 유지", ok, "ok" if ok else o))
    c, o = run([script, "start"], env=e)
    check("test_env start 두 번 → 멈춤(백업 보호)", c, o, 1, ("이미 테스트 환경이 시작돼",), ())
    st["theme"] = "light"                                  # 테스트 중 다른 설정이 바뀜
    (d / "settings.json").write_text(_json.dumps(st, ensure_ascii=False, indent=2))
    c, o = run([script, "end"], env=e)
    st = _json.loads((d / "settings.json").read_text())
    expect = dict(orig, theme="light")
    ok = c == 0 and st == expect and (d / "CLAUDE.md").read_text() == "전역 규칙\n" and not (d / "harness-test" / "state.json").exists()
    results.append(("test_env end: 바꾼 것만 원래 자리로, 테스트 중 바뀐 설정은 유지", ok, "ok" if ok else o + "\n" + _json.dumps(st, ensure_ascii=False)))
    c, o = run([script, "end"], env=e)
    check("test_env end 두 번 → 안전하게 실패", c, o, 1, ("시작 기록(state.json)이 없다",), ())

    d, orig = setup("env2", wiki=False, omc=False, md=False)
    e = {"HARNESS_TEST_CLAUDE_DIR": str(d)}
    c, o = run([script, "start"], env=e)
    check("test_env 원래 꺼진 설정은 기록만", c, o, 0, ("원래 꺼져 있음", "원래 없음"), ())
    c, o = run([script, "end"], env=e)
    st = _json.loads((d / "settings.json").read_text())
    ok = c == 0 and st == orig and not (d / "CLAUDE.md").exists()
    results.append(("test_env end: 원래 꺼진 설정을 켜지 않음", ok, "ok" if ok else o))

    d, orig = setup("env3")
    e = {"HARNESS_TEST_CLAUDE_DIR": str(d)}
    run([script, "start"], env=e)
    (d / "CLAUDE.md").write_text("테스트 중 새로 생긴 파일\n")
    c, o = run([script, "end"], env=e)
    ok = c == 1 and (d / "CLAUDE.md").read_text() == "테스트 중 새로 생긴 파일\n" and "덮어쓰지 않았다" in o \
        and (d / "harness-test" / "state.json").exists()
    results.append(("test_env end: 새로 생긴 CLAUDE.md는 덮어쓰지 않고 실패로 알림", ok, "ok" if ok else o))


def layout_tests(tmp: Path) -> None:
    """layout_check.py — 세부 설명 이야기 모양(D-DES-13). 브라우저 없이 HTML만 본다."""
    lc = str(SCRIPTS / "layout_check.py")
    head = lambda p: f'<header data-project="{p}"><h1 data-role="page-title">{p}</h1></header>'  # noqa: E731
    sec = lambda key, body, extra="": (f'<section data-role="project-detail" data-fact="x.md#{key}"'  # noqa: E731
                                       + (f' data-layout="{key}"' if key else "") + f'{extra}><h2>{key}</h2>{body}</section>')
    steps = '<dl class="steps" data-role="steps"><dt>원인</dt><dd>a</dd></dl>'
    tl = '<ol class="timeline" data-role="timeline"><li>a</li></ol>'
    flow = '<div class="flow-compare" data-role="flow-compare"></div>'
    lead = '<p class="ba ba-lead" data-role="before-after"><span class="before">1</span><span class="after">2</span></p>'
    cases = [
        ("layout_check 작업마다 다른 모양 → 통과", head("dms") + sec("metric-compare", lead) + sec("timeline", tl) + sec("flow-compare", flow) + sec("problem-solving", steps),
         0, ("통과", "metric-compare → timeline → flow-compare → problem-solving"), ()),
        ("layout_check data-layout 없음 → 실패", head("dms") + sec("", steps), 1, ("data-layout이 없다",), ()),
        ("layout_check 없는 키 → 실패", head("dms") + sec("cards", steps), 1, ("없는 레이아웃 키 'cards'",), ()),
        ("layout_check 키만 바꾸고 부품 없음 → 실패", head("dms") + sec("timeline", "<p>본문</p>"), 1, ("부품이 없다",), ()),
        ("layout_check 다른 키 섹션에 라벨 행 → 실패", head("dms") + sec("timeline", tl + steps), 1, ("problem-solving 섹션에서만",), ()),
        ("layout_check 같은 키 반복, 이유 없음 → 실패", head("dms") + sec("problem-solving", steps) + sec("timeline", tl) + sec("problem-solving", steps),
         1, ("이미",), ()),
        ("layout_check 같은 키 반복 + 이유 → 통과", head("dms") + sec("problem-solving", steps) + sec("timeline", tl) + sec("flow-compare", flow)
         + sec("problem-solving", steps, ' data-layout-repeat="둘 다 원인 분석"'), 0, ("다시 씀", "둘 다 원인 분석"), ()),
        ("layout_check 범용 형식(라벨 행)은 이유가 있어도 절반 초과 → 실패", head("dms") + sec("problem-solving", steps) + sec("timeline", tl)
         + sec("problem-solving", steps, ' data-layout-repeat="r"'), 1, ("절반을 넘으면",), ()),
        ("layout_check 맞는 형식이면 반복 허용 (측정 개선 둘 다 metric-compare)", head("dms") + sec("metric-compare", lead) + sec("timeline", tl)
         + sec("metric-compare", lead, ' data-layout-repeat="둘 다 측정된 개선"'), 0, ("통과", "다시 씀"), ("절반",)),
        ("layout_check metric-compare인데 수치보다 단계 카드가 먼저 → 실패", head("dms")
         + sec("metric-compare", '<ol class="stage-cards" data-role="stage-cards"><li>a</li></ol>' + lead), 1, ("먼저 나온다",), ()),
        ("layout_check 프로젝트가 다르면 같은 키 허용", head("a") + sec("problem-solving", steps) + head("b") + sec("problem-solving", steps), 0, ("통과",), ()),
    ]
    for i, (name, body, code, has, lacks) in enumerate(cases):
        f = tmp / f"layout{i}.html"
        f.write_text(f"<!doctype html><html><body>{body}</body></html>", encoding="utf-8")
        c, o = run([lc, str(f)])
        check(name, c, o, code, has, lacks)


def upload_tests(tmp: Path) -> None:
    """upload.py(PDF 전송, D-FLOW-8). 네트워크 없이 로컬 가짜 Discord 웹훅으로 본다."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    got: list[bytes] = []

    class Fake(BaseHTTPRequestHandler):            # Discord 웹훅 흉내: /good만 받고 나머지는 404
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            if not self.path.startswith("/good?wait=true") or "multipart/form-data" not in self.headers.get("Content-Type", ""):
                self.send_response(404); self.end_headers(); self.wfile.write(b'{"message": "Unknown Webhook"}'); return  # noqa: E702
            got.append(body)
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"id": "1"}')  # noqa: E702

    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    up = str(SCRIPTS / "upload.py")
    out = tmp / "up" / "portfolio" / "out"                 # 실제 구조: portfolio/out/portfolio.pdf 옆에 portfolio/facts
    out.mkdir(parents=True)
    (out.parent / "facts").mkdir()
    (out.parent / "facts" / "profile.md").write_text("---\nkind: profile\n---\n## 기본 정보\n- 이름: 홍길동 `[src: interview]`\n", encoding="utf-8")
    pdf = out / "portfolio.pdf"
    pdf.write_bytes(b"%PDF-1.4 test one")
    cfg = tmp / "upload.json"
    cfg.write_text(json.dumps({"discord_webhook": f"{base}/good"}), encoding="utf-8")

    c, o = run([up, str(pdf), "--config", str(tmp / "none.json")])
    check("upload 설정 없으면 건너뜀", c, o, 0, ("설정 없음",), ("실패",))
    c, o = run([up, str(pdf), "--config", str(cfg)])
    check("upload 보냄 — 기록의 이름으로 <이름>.pdf", c, o, 0, ("보냄", "홍길동.pdf"), ("`[src", base))
    sent = got[0] if got else b""
    ok = (b"%PDF-1.4 test one" in sent and 'filename="홍길동.pdf"'.encode() in sent
          and "홍길동 포트폴리오".encode() in sent and b'"parse": []' in sent)
    results.append(("upload 웹훅이 받은 것: PDF 첨부·이름 파일명·메시지·멘션 끔", ok, f"받은 것 앞부분: {sent[:300]!r}"))
    c, o = run([up, str(pdf), "--config", str(cfg)])
    check("upload 같은 PDF는 다시 안 보냄", c if len(got) == 1 else -1, o, 0, ("이미 보냄",), ())
    pdf.write_bytes(b"%PDF-1.4 test two")
    c, o = run([up, str(pdf), "--config", str(cfg), "--name", "../a/b:c"])
    check("upload PDF가 바뀌면 다시 보냄 + 이름의 경로 문자 제거", c if len(got) == 2 else -1, o, 0, ("보냄", "(abc.pdf"), ("/",))
    bad = tmp / "bad.json"
    bad.write_text(json.dumps({"discord_webhook": f"{base}/deleted"}), encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4 test three")
    c, o = run([up, str(pdf), "--config", str(bad)])
    check("upload 웹훅 없음(404) → 실패 표시(작업은 계속), URL은 안 찍힘", c, o, 1, ("전송 실패", "404"), (base,))

    # 턴 끝 훅(hooks/upload_on_stop.py): 모델이 upload.py를 잊어도 검사를 통과한 새 PDF는 간다
    import hashlib
    import os
    hook = ROOT / "hooks" / "upload_on_stop.py"
    hcwd = tmp / "hookcwd"
    hout = hcwd / "portfolio" / "out"
    hout.mkdir(parents=True)
    (hcwd / "portfolio" / "facts").mkdir()
    (hcwd / "portfolio" / "facts" / "profile.md").write_text("---\nkind: profile\n---\n- 이름: 김훅\n", encoding="utf-8")
    hpdf = hout / "portfolio.pdf"

    def fire(stdin: str) -> int:
        p = subprocess.run([sys.executable, "-I", str(hook)], input=stdin, capture_output=True, text=True, timeout=120,
                           env={**os.environ, "HARNESS_UPLOAD_CONFIG": str(cfg)})
        return p.returncode

    def mark(ok: bool, data: bytes | None = None) -> None:
        (hout / ".export.json").write_text(json.dumps({"pdf": "portfolio.pdf", "ok": ok,
                                                       "sha256": hashlib.sha256(data or hpdf.read_bytes()).hexdigest()}), encoding="utf-8")
    transcript = tmp / "session.jsonl"
    transcript.write_text('{"type":"assistant","message":{"content":"python3 export.py portfolio/out/index.html a4"}}\n', encoding="utf-8")
    other_tr = tmp / "other-session.jsonl"
    other_tr.write_text('{"type":"user","message":{"content":"다른 작업"}}\n', encoding="utf-8")
    ev = json.dumps({"hook_event_name": "Stop", "cwd": str(hcwd), "transcript_path": str(transcript)})
    n0 = len(got)
    code = fire(ev)
    results.append(("hook PDF 없으면 아무것도 안 함(종료 0)", code == 0 and len(got) == n0, f"code {code}, 보낸 수 {len(got) - n0}"))
    # 범위: 하네스 포트폴리오 폴더(interview-state.md) + 이 세션에서 export.py를 돌렸을 때만
    hpdf.write_bytes(b"%PDF-1.4 hook scope")
    mark(True)
    code = fire(ev)
    results.append(("hook interview-state.md 없는 폴더는 안 보냄 (범위)", code == 0 and len(got) == n0, f"보낸 수 {len(got) - n0}"))
    (hcwd / "portfolio" / "interview-state.md").write_text("stage: done\n", encoding="utf-8")
    code = fire(json.dumps({"hook_event_name": "Stop", "cwd": str(hcwd), "transcript_path": str(other_tr)}))
    results.append(("hook 이 세션에서 export.py를 안 돌렸으면 안 보냄 (범위)", code == 0 and len(got) == n0, f"보낸 수 {len(got) - n0}"))
    code = fire(json.dumps({"hook_event_name": "Stop", "cwd": str(hcwd)}))
    results.append(("hook 세션 기록 경로가 없으면 안 보냄 (범위)", code == 0 and len(got) == n0, f"보낸 수 {len(got) - n0}"))
    hpdf.write_bytes(b"%PDF-1.4 hook draft")
    code = fire(ev)
    results.append(("hook export 검사 기록 없는 PDF는 안 보냄", code == 0 and len(got) == n0, f"보낸 수 {len(got) - n0}"))
    mark(False)
    code = fire(ev)
    results.append(("hook 검사 실패한 PDF는 안 보냄", code == 0 and len(got) == n0, f"보낸 수 {len(got) - n0}"))
    mark(True, b"other pdf")
    code = fire(ev)
    results.append(("hook 검사 뒤에 바뀐 PDF는 안 보냄", code == 0 and len(got) == n0, f"보낸 수 {len(got) - n0}"))
    mark(True)
    code = fire(ev)
    sent_ok = code == 0 and len(got) == n0 + 1 and "김훅.pdf".encode() in got[-1]
    results.append(("hook 검사 통과한 새 PDF는 보냄(이름.pdf)", sent_ok, f"code {code}, 보낸 수 {len(got) - n0}"))
    code = fire(ev)
    results.append(("hook 같은 PDF는 다음 턴에 다시 안 보냄", code == 0 and len(got) == n0 + 1, f"보낸 수 {len(got) - n0}"))
    code = fire("이건 JSON이 아님")
    results.append(("hook 입력이 깨져도 종료 0 (턴 종료를 막지 않음)", code == 0, f"code {code}"))
    srv.shutdown()
    srv.server_close()
    c, o = run([up, str(pdf), "--config", str(cfg)])
    check("upload 서버 없음 → 실패 표시", c, o, 1, ("전송 실패",), (base,))
    big = out / "big.pdf"
    big.write_bytes(b"%PDF" + b"0" * (11 * 1024 * 1024))
    c, o = run([up, str(big), "--config", str(cfg)])
    check("upload 10MB 넘으면 보내지 않음", c, o, 1, ("제한을 넘는다",), ())


def link_tests(tmp: Path) -> None:
    """link_check.py — 링크를 누르면 반드시 그 페이지로 가는지(D-DES-14). PDF는 /URI 항목을 직접 만든 가짜 파일로 본다."""
    lc = str(SCRIPTS / "link_check.py")
    srv, base = link_server()
    page = lambda body: f"<!doctype html><html><body>{body}</body></html>"  # noqa: E731
    cases = [
        ("link_check 절대 주소 링크·mailto → 통과", f'<a href="{base}/ok">저장소</a> <a href="mailto:a@b.co">a@b.co</a>', [], 0, ("통과", "접속 확인: 1/1개 열림"), ()),
        ("link_check 주소를 글자로만 → 실패", "<p>깃허브: github.com/hong</p>", ["--offline"], 1, ("주소가 링크가 아니다", "github.com/hong"), ()),
        ("link_check 이메일을 글자로만 → 실패", "<p>hong@example.com</p>", ["--offline"], 1, ("주소가 링크가 아니다",), ()),
        ("link_check href가 상대 경로(github.com/x) → 실패", '<a href="github.com/hong">github.com/hong</a>', ["--offline"], 1, ("절대 주소가 아니다",), ()),
        ("link_check 빈 href·# → 실패", '<a href="#">블로그</a><a>노션</a>', ["--offline"], 1, ("아무 데도 안 간다",), ()),
        ("link_check 글자와 다른 사이트로 연결 → 실패", '<a href="https://velog.io/@hong">github.com/hong</a>', ["--offline"], 1, ("다른 곳으로 간다",), ()),
        ("link_check 문서 안 링크는 대상 id가 있어야 함", '<a href="#p2">2쪽</a><section id="p3"></section>', ["--offline"], 1, ("대상 id가 없다",), ()),
        ("link_check 인쇄 숨김 요소의 주소는 제외", '<div data-print-hidden>github.com/hong</div>', ["--offline"], 0, ("통과",), ()),
        ("link_check 기술 이름(Node.js·Spring.io)은 주소로 안 봄", "<p>Node.js, Spring.io, ASP.NET, v2.3.0</p>", ["--offline"], 0, ("통과",), ()),
        ("link_check 404 → 실패", f'<a href="{base}/gone">배포 주소</a>', [], 1, ("링크가 열리지 않는다", "404"), ()),
        ("link_check 서버 없는 주소(연결 거부) → 실패", '<a href="http://127.0.0.1:9/x">데모</a>', [], 1, ("링크가 열리지 않는다", "연결 거부"), ()),
    ]
    for i, (name, body, extra, code, has, lacks) in enumerate(cases):
        f = tmp / f"link{i}.html"
        f.write_text(page(body), encoding="utf-8")
        c, o = run([lc, str(f), *extra])
        check(name, c, o, code, has, lacks)
    # PDF: HTML의 링크가 PDF 링크(/URI)로 들어갔는지
    f = tmp / "linkpdf.html"
    f.write_text(page('<a href="https://github.com/hong">github.com/hong</a> <a href="https://velog.io/@hong/%ED%95%9C">블로그</a>'), encoding="utf-8")
    good = tmp / "good.pdf"
    good.write_bytes(b"%PDF-1.4\n<< /S /URI /URI (https://github.com/hong) >>\n<< /S /URI /URI (https://velog.io/@hong/%ED%95%9C) >>\n%%EOF")
    c, o = run([lc, str(f), "--pdf", str(good), "--offline"])
    check("link_check PDF에 링크가 모두 있음 → 통과", c, o, 0, ("PDF 링크: 2개 모두",), ())
    bad = tmp / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4\n<< /S /URI /URI (https://github.com/hong) >>\n%%EOF")
    c, o = run([lc, str(f), "--pdf", str(bad), "--offline"])
    check("link_check PDF에 링크가 빠짐 → 실패", c, o, 1, ("PDF에서 눌러도 안 열린다", "velog.io"), ())
    srv.shutdown()
    srv.server_close()


def docs_tests() -> None:
    """규칙 단일 원본(rules/)과 스킬 로딩 구조가 깨지지 않았는지."""
    import re as _re
    rules = ROOT / "rules"
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    missing = [str(s.relative_to(ROOT)) for s in skills if "**먼저 읽는다**" not in s.read_text(encoding="utf-8")]
    results.append(("docs 모든 스킬에 '먼저 읽는다'", not missing, "ok" if not missing else f"없음: {missing}"))
    nostop = [str(s.relative_to(ROOT)) for s in skills if "읽지 못하면(파일 없음·읽기 실패) 이 스킬의 작업을 시작하지 않는다" not in s.read_text(encoding="utf-8")]
    results.append(("docs 모든 스킬이 원칙 문서를 못 읽으면 멈춤", not nostop, "ok" if not nostop else f"없음: {nostop}"))
    ud = (rules / "user-decisions.md").read_text(encoding="utf-8")
    evd = [f"R-EVD-{i}" for i in range(1, 8) if f"| R-EVD-{i} |" not in ud]
    results.append(("docs 기본 검증 규칙(R-EVD-1~7)이 결정 원본에 있음", not evd, "ok" if not evd else f"없음: {evd}"))
    bad = []
    for s in skills:
        for rel in ("../../rules/principles.md", "../../rules/user-decisions.md"):
            if rel in s.read_text(encoding="utf-8") and not (s.parent / rel).resolve().exists():
                bad.append(f"{s.parent.name}: {rel}")
    results.append(("docs 스킬 기준 상대 경로가 실제 파일을 가리킴", not bad, "ok" if not bad else str(bad)))
    old = ROOT / "skills" / "build" / "user-decisions.md"
    results.append(("docs 예전 결정 파일이 되살아나지 않음", not old.exists(), "ok" if not old.exists() else str(old)))
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    dup = "## Target Hiring Market" in claude or "@rules/principles.md" not in claude
    results.append(("docs CLAUDE.md는 원칙을 @import만 하고 다시 쓰지 않음", not dup, "ok" if not dup else "CLAUDE.md에 원칙 본문이 있거나 @import가 없다"))
    ids = set(_re.findall(r"\b(D-[A-Z0-9]+-\d+)\b", (rules / "user-decisions.md").read_text(encoding="utf-8")))
    used = set()
    for f in list(skills) + sorted((ROOT / "agents").glob("*.md")):
        used |= set(_re.findall(r"\b(D-[A-Z0-9]+-\d+)\b", f.read_text(encoding="utf-8")))
    unknown = sorted(used - ids)
    results.append(("docs 스킬이 참조하는 결정 ID가 원본에 있음", not unknown, "ok" if not unknown else f"원본에 없는 ID: {unknown}"))


def main() -> int:
    fast = "--fast" in sys.argv
    with tempfile.TemporaryDirectory(prefix="harness-tests-") as t:
        tmp = Path(t)
        docs_tests()
        facts_tests(tmp)
        pair_tests(tmp)
        provenance_tests(tmp)
        layout_tests(tmp)
        upload_tests(tmp)
        link_tests(tmp)
        image_tests(tmp)
        env_tests(tmp)
        theme_tests(tmp)
        if not fast:
            export_tests(tmp)
    width = max(len(n) for n, _, _ in results)
    for name, ok, msg in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {'' if ok else msg}")
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} 통과" + ("" if not fast else "  (--fast: export.py 테스트 건너뜀)"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
