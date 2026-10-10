#!/usr/bin/env python3
"""포트폴리오 HTML → PDF 출력과 검증.

사용법: export.py <portfolio/out/index.html> <a4|continuous> <출력 pdf 경로>

0. 사전 검증: 옆에 facts/가 있으면 facts_lint.py와 check_numbers.py(본문 수치 근거·내부 용어), 그리고 layout_check.py(세부 설명의 이야기 모양, D-DES-13). 실패면 PDF를 만들지 않는다
1. out/ 디렉터리를 로컬 http 서버로 띄운다 (file:// 이면 웹폰트·이미지가 안 뜰 수 있음)
2. 레이아웃 실측 (headless Chrome --dump-dom)
   - 실측과 PDF 출력 모두 data-print-hidden 요소를 숨긴 상태로 한다.
     빈 이미지 슬롯처럼 PDF에서 빠지는 요소가 화면 실측에 끼면, PDF에선 안 넘치는 쪽을 넘친다고 잘못 판단한다.
   - a4: 각 .sheet 의 넘침 검사 (scrollHeight > clientHeight 이면 실패)
   - a4: 각 .sheet 의 채움 검사. 글자·이미지·배경/테두리 있는 상자가 덮는 세로 구간을 합쳐
     채움 비율과 가장 큰 빈 띠를 잰다. 빈 띠가 내용 영역의 GAP_WARN 이상이면 '여백 경고'
     (실패는 아니다. 의도한 여백이면 .sheet 에 data-sparse-ok 를 달아 경고를 끈다.
      마지막 쪽을 뺀 모든 쪽은 채움이 FILL_MIN(50%) 미만이면 실패 — 여백 50% 상한. data-sparse-ok는 마지막 쪽에서만 통한다)
   - 역할 검사(경고): 60자 넘는 문장 덩어리가 본문(--fs-body)보다 큼 / 100자 넘는 덩어리가 본문보다 작음 /
     제목(h1~h4, [data-role=section-title])이 본문보다 작음 / 제목이 아닌 글자(강조 수치 등)가 섹션 제목 크기 이상 /
     소제목 크기 굵은 강조(수치 등)가 한 쪽에 2곳 이상 (한 줄 소개 data-role="tagline", 헤드라인 data-role="headline"은 제외 — 긴 헤드라인은 허용) /
     쪽 번호가 오른쪽 아래가 아님 /
     화면 캡처(img[data-kind=capture])가 원본의 절반 미만으로 줄어 안의 글자를 읽기 어려움
   - before → after(경고): "숫자 → 숫자" 글이 [data-role=before-after] 밖에 있음 / before-after 안에 .before·.after가 없음 /
     바로 다음 요소가 측정 조건 [data-role=measure-cond]가 아님 (components.css .ba). 측정된 before → after는 개수 제한 없이 크게 강조해도 된다
   - 큰 강조(경고): 측정된 before → after가 아닌 글이 소제목 크기로 굵게 강조됨
   - 측정 화면 짝(실패/경고): img[data-kind=measure]를 data-pair로 묶은 전·후 두 장이 다른 쪽에 있으면 실패.
     한 장이 본문 폭의 절반을 넘거나, 짝 묶음([data-role=measure-pair])이 쪽 높이의 30%를 넘으면 경고 — 측정 화면은 증빙이라 작게 둔다
   - 전·후 이미지 짝(실패/경고): data-pair로 묶은 이미지(종류 무관)의 렌더 크기가 2px 넘게 다르면 실패.
     data-pair 없이 캡션이 "전"·"후"인 이미지가 한 쪽에 같이 있으면 경고
   - 프로젝트 블록 순서(실패): 이름·기간 → 한 줄 소개 → 팀원 → 사용 기술 → 기능 소개 → 주요 성과 → 세부 설명 → 전체 회고.
     data-role(project-team, project-tech, project-features, project-highlights, project-detail, project-retro)로 표시. 팀원·사용 기술은 필수
   - 프로젝트 기간(실패): 첫머리의 [data-role=project-meta]가 "2026.03 ~ 운영 중" / "2025.03 ~ 2025.06" 형식으로 시작하지 않으면 실패
   - 머리글(경고): 쪽 위쪽 10% 안에 있는 같은 글이 2쪽 이상에서 반복되면 머리글로 본다 (build 머리글 금지 규칙)
   - 프로젝트 첫머리(실패): [data-role=page-title](프로젝트 이름) 바로 다음 글이 [data-role=project-summary](한 줄 설명)가
     아니면 실패. 쪽이 2장 이상인데 page-title이 하나도 없어도 실패 — 이름 다음에 한 일이 먼저 나오면 독자는 무슨 서비스인지 모른다
   - 프로젝트 이미지(실패): 프로젝트마다 로고(img[data-kind=logo], 첫머리 안)와 서비스 화면(img[data-kind=screen], 같은
     data-project) 1장 이상. 사용자가 없다고 확인한 것은 첫머리의 data-image-missing="logo screen"으로 표시하면 통과
   - 1쪽 직무명(실패, D-P1-5): data-layout="profile" 쪽에 data-role="job-title"이 없거나 비면 실패. 레퍼런스 모드에서도 본다
   - 글자 대비(D-DES-1): 글자색과 실제 바탕색(조상의 background-color)의 대비가 1.5:1 미만이면 안 보이는 글자로 실패(레퍼런스 모드 포함),
     4.5:1(큰 글자 3:1) 미만이면 경고. 바탕이 배경 이미지·그라디언트면 건너뛴다
   - 1쪽 첫머리 순서(실패, D-P1-1): name → job-title → tagline. 레퍼런스 모드에서는 보지 않는다
   - 모노 폰트 수치(경고, D-DES-10): before → after·강조 수치에 모노 글꼴
   - 쪽 수(경고, D-DES-17): 1 + 3 × 프로젝트 수(page-title 개수)를 넘으면 경고
   - 이미지: 로드 실패(naturalWidth 0)는 실패. 인쇄 폭 대비 원본 픽셀이 LOWRES_RATIO 배 미만이면 '흐릿함 경고'(SVG는 벡터라 제외) 
   - continuous: 문서 높이를 재서 @page 높이를 정한다
   - 글자 크기: 보이는 글자의 계산된 font-size가 MIN_PT 미만이면 실패 (design의 캡션 하한)
3. PDF 출력 후 쪽수 검증 (a4: .sheet 개수와 같아야 함, continuous: 1쪽)
4. HTML 텍스트와 PDF 텍스트의 문자 구성 대조 (<title>, 인쇄에서 숨기는 data-print-hidden 요소 제외)
5. 링크 검사(link_check.py, D-DES-14): 보이는 주소는 모두 <a href>, href는 절대 주소, PDF에서 누를 수 있음, 실제로 열림(404·없는 도메인 실패)
레퍼런스 모드(D-DES-16): 옆의 design.json에서 style.source가 "reference"이고 레퍼런스 근거가 있으면
(design/scripts/reference_check.py: reference 파일이 있고 이름이, URL이면 URL이 sources/interview-log.md에 있음)
레퍼런스를 그대로 따른 결과물로 보고 **내용 검사만** 한다. 근거가 없으면 이유를 한 줄 출력하고 일반 검사를 그대로 돈다. 디자인 검사(레이아웃 사전 검증, 측정 화면 짝, 첫머리·블록 순서·기간 형식·필수 이미지,
채움·여백, 글자 크기·역할·분포, 머리글, 흐릿함)는 돌리지 않는다. 남는 것: 기록·수치 사전 검증, 이미지 로드 실패(빠진 내용),
넘침(내용이 잘림), 쪽수, 텍스트 대조(내용 누락), 링크.
종료 코드: 모두 통과 0, 하나라도 실패 1, 실행 불가 2. 여백 경고만 있으면 0.
"""
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from htmltext import visible_text  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "design" / "scripts"))
from reference_check import reference_problem  # noqa: E402

GAP_WARN = 0.25   # 가장 큰 빈 띠가 내용 영역 높이의 이 비율 이상이면 경고
FILL_MIN = 0.50   # 마지막 쪽을 뺀 모든 쪽의 최소 채움 (여백 50% 상한, 사용자 결정 2026-10-09: 40% → 50%)
LOWRES_RATIO = 1.5      # 원본 폭 / 렌더 폭(CSS px, 96dpi). 1.5 미만이면 인쇄 시 약 144dpi 미만이라 흐릿하다
MIN_PT = 8        # 캡션 하한. 이보다 작은 글자는 실패
MERGE_PX = 24     # 이보다 좁은 틈(줄 간격, 문단 간격)은 빈 띠로 보지 않는다
INVISIBLE_RATIO = 1.5   # 글자와 바탕 대비가 이 미만이면 안 보이는 글자로 보고 실패
PAGES_PER_PROJECT = 3   # 쪽 수 권장 상한 = 1쪽 + 프로젝트당 이 쪽 수 (D-DES-17, 넘으면 경고만)

# PDF에서 빠지는 요소를 실측에서도 뺀다. index.html의 @media print 짝과 상관없이 항상 적용한다.
PRINT_HIDE_CSS = "<style>[data-print-hidden]{display:none !important}</style>"
# components.css의 화면 보기(회색 바탕·종이 간격·그림자·좁은 화면 축소)를 끄고 인쇄와 같은 상태로 잰다
SCREEN_RESET_CSS = ("<style>html,body{background:#fff !important}body{padding:0 !important;zoom:1 !important}"
                    ".sheet{margin:0 !important;box-shadow:none !important}</style>")

# 측정 스크립트는 measure.js에 있다. 숫자 설정은 __이름__ 자리표시자를 문자열 치환으로 넣는다.
MEASURE_JS = "<script>\n" + (Path(__file__).resolve().parent / "measure.js").read_text(encoding="utf-8") \
    .replace("__MERGE_PX__", str(MERGE_PX)).replace("__MIN_PT__", str(MIN_PT)) + "\n</script>\n"


def find_chrome() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if path := shutil.which(name):
            return path
    sys.exit("Chrome/Chromium을 찾을 수 없다")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def inject(html: str, snippet: str, before: str) -> str:
    idx = html.lower().rfind(before)
    if idx < 0:
        sys.exit(f"{before} 태그가 없다")
    return html[:idx] + snippet + html[idx:]


def chrome(args: list[str]) -> str:
    base = [find_chrome(), "--headless", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=20000"]
    return subprocess.run(base + args, capture_output=True, text=True, timeout=120).stdout


def measure(url: str) -> dict:
    dom = chrome(["--dump-dom", url])
    m = re.search(r'<pre id="__measure">(.*?)</pre>', dom, re.S)
    if not m:
        sys.exit("실측 실패: 페이지 로드나 폰트 로딩이 끝나지 않았다")
    return json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&"))


def pdf_pages(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    return int(re.search(r"^Pages:\s+(\d+)", out, re.M).group(1))


def print_pdf(url: str, pdf: Path) -> None:
    chrome(["--no-pdf-header-footer", f"--print-to-pdf={pdf}", url])
    if not pdf.exists():
        sys.exit("PDF 출력 실패")


def report_type(sheets: list[dict]) -> None:
    """쪽마다 글자 크기 분포를 출력한다. 크기 단계가 많거나, 쪽마다 같은 역할의 크기가 다르면 디자인 리뷰가 판단한다."""
    for s in sheets:
        t = s.get("type") or {}
        sizes = sorted({float(k.split("pt")[0]) for k in t}, reverse=True)
        parts = ", ".join(f"{k} {v}자" for k, v in sorted(t.items(), key=lambda kv: -float(kv[0].split("pt")[0])))
        warn = f"  ← 크기 단계 {len(sizes)}개 (5개 이하 권장)" if len(sizes) > 5 else ""
        print(f"글자  sheet {s['i'] + 1}: {parts}{warn}")


def report_fill(sheets: list[dict]) -> bool:
    """쪽마다 채움 비율을 출력한다. 마지막 쪽을 뺀 쪽의 채움이 FILL_MIN 미만이면 실패(False)를 돌려준다.
    큰 빈 띠는 경고만 한다(data-sparse-ok는 마지막 쪽에서만 경고를 끈다)."""
    ok, warned = True, 0
    last = max((s["i"] for s in sheets), default=0)
    for s in sheets:
        f = s["fill"]
        if f["content"] <= 0:
            continue
        pct = round(100 * f["covered"] / f["content"])
        gap_pct = round(100 * f["gap"]["size"] / f["content"])
        line = f"채움  sheet {s['i'] + 1}: {pct}% / 가장 큰 빈 띠 {round(f['gap']['size'])}px ({gap_pct}%)"
        is_last = s["i"] == last
        if f["sparseOk"] and not is_last:
            line += "  [data-sparse-ok는 마지막 쪽에서만 통한다 — 무시함]"
        if not is_last and f["covered"] < FILL_MIN * f["content"]:
            ok = False
            line += f"  ← 실패: 여백 {100 - pct}% (마지막 쪽 외에는 {round((1 - FILL_MIN) * 100)}%를 넘으면 안 된다)"
        elif f["gap"]["size"] >= GAP_WARN * f["content"]:
            where = f"y={round(f['gap']['from'])}~{round(f['gap']['to'])}px"
            if f["sparseOk"] and is_last:
                line += f"  [data-sparse-ok: 경고 생략, {where}]"
            else:
                warned += 1
                line += f"  ← 여백 경고 ({where})"
        print(line)
    if not ok:
        print("여백 실패: 다음 쪽 블록을 당겨오거나, 쪽을 합치거나, 블록 간격을 --space-* 안에서 늘린다. "
              "글자를 역할보다 키워서 채우지 않는다. 1쪽이 모자라면 사용자에게 1쪽에 넣을 내용을 묻는다.")
    if warned:
        print(f"여백 경고 {warned}쪽: 빈 띠 위치를 보고 블록을 고르게 배치한다.")
    return ok


def reference_mode(portfolio: Path) -> bool:
    """design.json의 style.source가 reference이고 사용자가 레퍼런스를 줬다는 근거가 있으면
    레퍼런스를 그대로 따른 결과물이다(D-DES-16). 근거가 없으면 이유를 출력하고 일반 검사로 간다."""
    try:
        style = json.loads((portfolio / "design.json").read_text(encoding="utf-8")).get("style") or {}
    except (OSError, ValueError):
        return False
    if style.get("source") != "reference":
        return False
    why = reference_problem(style, portfolio)
    if why:
        print(f"레퍼런스 모드 안 켬: {why}. 일반 디자인 검사를 그대로 한다 (D-DES-16)")
        return False
    return True


def main(html_path: str, fmt: str, pdf_out: str) -> int:
    for tool in ("pdfinfo", "pdftotext"):
        if not shutil.which(tool):
            sys.exit(f"{tool}이 없다 (sudo apt install poppler-utils)")
    src = Path(html_path).resolve()
    root, pdf = src.parent, Path(pdf_out).resolve()
    html = src.read_text(encoding="utf-8")
    probe, printable = root / "_probe.html", root / "_print.html"
    ok = True

    # 사전 검증: portfolio/out/index.html이면 옆의 portfolio/facts를 먼저 검사한다.
    # 입력(기록)에 ERROR가 있으면 PDF를 만들지 않는다. 같은 입력이면 facts_lint 캐시를 재사용한다.
    portfolio = root.parent
    ref = reference_mode(portfolio)
    if ref:
        print("레퍼런스 모드: 배치·색·글자 같은 디자인 검사는 하지 않고 내용만 검사한다 (D-DES-16)")
    if (portfolio / "facts").is_dir():
        lint = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "facts_lint.py"),
                               str(portfolio / "facts"), "--images", str(portfolio / "images"),
                               "--cache", str(portfolio / ".facts_lint.json")], capture_output=True, text=True)
        if lint.returncode != 0:
            print(lint.stdout.rstrip())
            print("\n사전 검증 실패: 기록(facts)에 ERROR가 있어 PDF를 만들지 않는다. 기록을 고친 뒤 다시 만든다.")
            return 1
        print("기록 사전 검증: 통과" + (" (이전 결과 재사용)" if "재사용" in lint.stdout else ""))
        # 수치 근거(D-TXT-1, R-EVD-1): 본문 수치가 기록에 같은 단위로 있는지, 출처 메모가 새지 않았는지. 레퍼런스 모드에서도 돈다
        nums = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "check_numbers.py"),
                               str(src), str(portfolio / "facts")], capture_output=True, text=True)
        if nums.returncode != 0:
            print(nums.stdout.rstrip())
            print("\n사전 검증 실패: 기록에 근거가 없는 수치나 내부 용어가 본문에 있어 PDF를 만들지 않는다.")
            return 1
        print("수치 사전 검증: 통과")

    # 레이아웃 사전 검증(D-DES-13): 세부 설명 작업마다 이야기 모양 키와 부품이 있는지, 같은 형식 반복. 브라우저 없이 HTML만 본다
    # 레퍼런스 모드에서는 배치를 레퍼런스가 정하므로 건너뛴다
    if not ref:
        lay = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "layout_check.py"), str(src)],
                             capture_output=True, text=True)
        print(lay.stdout.rstrip())
        if lay.returncode != 0:
            print("\n사전 검증 실패: 세부 설명의 레이아웃이 규칙에 맞지 않아 PDF를 만들지 않는다.")
            return 1

    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                               "--directory", str(root)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    base = f"http://127.0.0.1:{port}"
    try:
        hidden = inject(html, PRINT_HIDE_CSS + SCREEN_RESET_CSS, "</head>")
        probe.write_text(inject(hidden, MEASURE_JS, "</body>"), encoding="utf-8")
        m = measure(f"{base}/_probe.html")
        print(f"로드된 폰트: {sorted(set(m['fonts'])) or '없음 (웹폰트 로딩 실패 가능성)'}")
        if ref:                                # 디자인 판정은 비우고, 내용에 닿는 것(이미지 로드·넘침·텍스트)만 남긴다
            m["pairs"] = {"fails": [], "warns": []}
            m["heads"] = {"count": 0, "problems": []}
            m["small"] = []
        for f_ in m["pairs"]["fails"]:
            ok = False
            print(f"측정 화면 실패: {f_}")
        for w_ in m["pairs"]["warns"]:
            print(f"측정 화면 경고: {w_}")
        heads = m["heads"]
        if fmt == "a4" and len(m["sheets"]) > 1 and heads["count"] == 0 and not ref:
            ok = False
            print('프로젝트 첫머리 실패: 프로젝트 이름에 data-role="page-title"이 없다. 이름 → 한 줄 설명(data-role="project-summary") 순서로 표시한다')
        for prob in heads["problems"]:
            ok = False
            print(f"프로젝트 첫머리 실패: {prob}")
        if heads["problems"]:
            print("  프로젝트 첫머리는 이름 → 한 줄 설명(무슨 서비스) 순서이고, 로고와 서비스 화면이 있어야 한다(없다고 확인한 것만 data-image-missing)")
        elif heads["count"]:
            print(f"프로젝트 첫머리: {heads['count']}개 모두 이름 → 한 줄 설명, 로고·서비스 화면 있음")
        # 1쪽 직무명(D-P1-5): 1쪽(data-layout="profile")이 있으면 이름 아래 직무명이 있어야 한다. 내용이라 레퍼런스 모드에서도 본다
        # 쪽 안에 section이 겹칠 수 있어 닫는 태그 대신 다음 .sheet 시작까지를 1쪽으로 본다
        sheet_tags = [t for t in re.finditer(r'<section\b[^>]*>', html) if re.search(r'class="[^"]*\bsheet\b', t.group())]
        profile = next((i for i, t in enumerate(sheet_tags) if 'data-layout="profile"' in t.group()), None)
        if profile is not None:
            end = sheet_tags[profile + 1].start() if profile + 1 < len(sheet_tags) else len(html)
            page1 = html[sheet_tags[profile].end():end]
            job = re.search(r'data-role="job-title"[^>]*>\s*([^<\s][^<]*)<', page1)
            if not job:
                ok = False
                print('1쪽 실패: 이름 아래 직무명(data-role="job-title")이 없다. 기록의 `직무명:`을 이름 바로 아래에 넣는다 (D-P1-5)')
            # 1쪽 첫머리 순서(D-P1-1): 이름 → 직무명 → 한 줄 소개. 배치는 레퍼런스가 정하므로 레퍼런스 모드에서는 보지 않는다
            pos = [(r, page1.find(f'data-role="{r}"')) for r in ("name", "job-title", "tagline")]
            pos = [(r, i) for r, i in pos if i >= 0]
            if not ref and [r for r, _ in sorted(pos, key=lambda x: x[1])] != [r for r, _ in pos]:
                ok = False
                print(f"1쪽 실패: 첫머리 순서가 {' → '.join(r for r, _ in sorted(pos, key=lambda x: x[1]))} — "
                      "이름 → 직무명 → 한 줄 소개 순서로 둔다 (D-P1-1)")
        # 글자 대비(D-DES-1): 1.5:1 미만은 안 보이는 글자라 실패(레퍼런스 모드 포함 — 내용이 사라진다). 4.5:1(큰 글자 3:1) 미만은 경고
        for c_ in m.get("contrast", []):
            where = f"sheet {c_['sheet']}" if c_["sheet"] else "쪽 밖"
            if c_["ratio"] < INVISIBLE_RATIO:
                ok = False
                print(f"안 보이는 글자 실패  {where}: \"{c_['text']}\" 글자색과 바탕 대비 {c_['ratio']}:1 — 페이지 CSS가 글자색이나 바탕을 덮었는지 본다")
            elif not ref:
                print(f"대비 경고  {where}: \"{c_['text']}\" {c_['ratio']}:1 (기준 {'3' if c_['large'] else '4.5'}:1) — 글자색을 --color-* 토큰으로 되돌린다")
        for im in m["images"]:
            if not im["natural"]:
                ok = False
                print(f"이미지 로드 실패: {im['src']}")
            elif not ref and not im.get("vector") and im["rendered"] and im["natural"] < LOWRES_RATIO * im["rendered"]:
                print(f"흐릿함 경고: {im['src']} 원본 폭 {im['natural']}px, 인쇄 폭 {im['rendered']}px "
                      f"(원본이 {LOWRES_RATIO}배 이상이어야 선명). 더 작게 배치하거나 큰 원본을 받는다")
        if m["small"]:
            ok = False
            print(f"작은 글자 {len(m['small'])}곳 ({MIN_PT}pt 미만):")
            for t in m["small"][:10]:
                print(f"  {t['pt']}pt  {t['text']}")
        elif not ref:                          # 레퍼런스 모드에서는 글자 크기를 레퍼런스가 정한다
            print(f"글자 크기: {MIN_PT}pt 미만 없음")

        if fmt == "a4":
            if not m["sheets"]:
                sys.exit(".sheet 요소가 없다")
            for s in m["sheets"]:
                if s["scroll"] > s["client"]:
                    ok = False
                    print(f"넘침  sheet {s['i'] + 1}: 내용 {s['scroll']}px > 페이지 {s['client']}px")
            if ok:
                print(f"넘침 없음 ({len(m['sheets'])}장)")
            # 쪽 수 권장 범위(D-DES-17): 1쪽 + 프로젝트당 3쪽까지. 넘어도 막지 않고 경고만 한다
            nproj = len(set(re.findall(r'data-role="page-title"[^>]*>\s*([^<]+?)\s*<', html)))
            if not ref and nproj and len(m["sheets"]) > 1 + PAGES_PER_PROJECT * nproj:
                print(f"쪽 수 경고: {len(m['sheets'])}쪽 — 프로젝트 {nproj}개면 {1 + PAGES_PER_PROJECT * nproj}쪽 이하를 권장한다. "
                      "우선순위가 낮은 세부 설명(원칙 → Priorities)부터 줄일 후보를 끝 보고에 적는다 (D-DES-17)")
            if not ref and not report_fill(m["sheets"]):
                ok = False
            if not ref:
                report_type(m["sheets"])
            role_warns = [] if ref else [w for sh in m["sheets"] for w in sh["roles"]]
            seen: dict[str, list[int]] = {}
            for sh in ([] if ref else m["sheets"]):
                for t in sh["top"]:
                    seen.setdefault(t, []).append(sh["i"] + 1)
            for t, pages in seen.items():
                if len(pages) >= 2:
                    role_warns.append(f"sheet {', '.join(map(str, pages))}: 쪽 위쪽에 \"{t}\"가 반복됨 — 머리글은 두지 않는다 (build 머리글 금지 규칙)")
            for w in role_warns:
                print(f"역할 경고  {w}")
            if role_warns:
                print(f"역할 경고 {len(role_warns)}건: 글자 크기를 역할에 맞는 --fs-* 변수로 바꾸고, 쪽 번호는 오른쪽 아래로 옮긴다")
            printable.write_text(hidden, encoding="utf-8")
            if pdf.exists():
                pdf.unlink()
            print_pdf(f"{base}/_print.html", pdf)
            pages = pdf_pages(pdf)
            if pages != len(m["sheets"]):
                ok = False
            print(f"쪽수: PDF {pages} / sheet {len(m['sheets'])} {'OK' if pages == len(m['sheets']) else 'FAIL'}")
        else:
            w, h = m["width"], m["height"]
            for extra in range(0, 21):
                page_css = f"<style>@page {{ size: {w}px {h + extra}px; margin: 0; }}</style>"
                printable.write_text(inject(hidden, page_css, "</head>"), encoding="utf-8")
                if pdf.exists():
                    pdf.unlink()
                print_pdf(f"{base}/_print.html", pdf)
                if pdf_pages(pdf) == 1:
                    print(f"@page 높이: {h + extra}px (실측 {h}px + {extra})")
                    break
            else:
                ok = False
                print(f"FAIL: 실측 {h}px + 20px까지 늘려도 1쪽이 되지 않는다")
    finally:
        server.terminate()
        probe.unlink(missing_ok=True)
        printable.unlink(missing_ok=True)

    pdf_text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    norm = lambda t: Counter(c for c in t.casefold() if not c.isspace())  # noqa: E731
    a, b = norm(visible_text(html, ("data-print-hidden",))), norm(pdf_text)
    only_html, only_pdf = a - b, b - a
    if only_html or only_pdf:
        print(f"텍스트 차이 — HTML에만: {dict(only_html)} / PDF에만: {dict(only_pdf)}")
        print("  줄바꿈 자리의 '-' 1~2개는 pdftotext가 먹은 것이라 무시해도 된다. 그 외는 확인 필요.")
        if set(only_html) - {"-"} or only_pdf:
            ok = False
    else:
        print("텍스트 대조: 일치")

    # 링크(D-DES-14): 보이는 주소는 모두 링크, href는 절대 주소, PDF에서 누를 수 있음, 실제로 열림
    # HARNESS_LINK_OFFLINE=1이면 접속 확인만 건너뛴다(회귀 테스트·오프라인)
    import os
    link_args = [sys.executable, str(Path(__file__).resolve().parent / "link_check.py"), str(src), "--pdf", str(pdf)]
    if os.environ.get("HARNESS_LINK_OFFLINE") == "1":
        link_args.append("--offline")
    link = subprocess.run(link_args, capture_output=True, text=True, timeout=300)
    print(link.stdout.rstrip())
    if link.returncode != 0:
        ok = False

    # 검사 결과를 PDF 옆에 남긴다 — 턴 끝 전송 훅(hooks/upload_on_stop.py)은 통과한 PDF만 보낸다(D-FLOW-8)
    if pdf.exists():
        import hashlib
        (pdf.parent / ".export.json").write_text(json.dumps(
            {"pdf": pdf.name, "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "ok": ok}), encoding="utf-8")

    print(f"\n{'통과' if ok else '실패'}: {pdf}")
    return 0 if ok else 1


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) != 3 or argv[1] not in ("a4", "continuous"):
        print(__doc__)
        sys.exit(2)
    sys.exit(main(*argv))
