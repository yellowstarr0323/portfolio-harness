#!/usr/bin/env python3
"""포트폴리오 HTML → PDF (또는 첫 화면 PNG).

사용법: make_pdf.py <index.html> <출력.pdf>        A4 쪽 단위 PDF
        make_pdf.py <preview.html> --png <출력.png>  디자인 시안 미리보기 이미지

- HTML이 있는 폴더를 로컬 http 서버로 띄운다(file://이면 웹폰트·이미지가 안 뜰 수 있다).
- PNG: 문서 전체 높이(최대 4쪽)로 찍는다. 디자인 시안 미리보기용.
- PDF: 쪽은 class="sheet" 요소 하나가 A4 한 장이다. 출력 전에 쪽마다 내용이 넘치는지 재고,
  넘치는 쪽이 있으면 PDF를 만들지 않는다(넘친 내용은 PDF에서 잘린다). 깨진 이미지도 실패다.
  출력 뒤 PDF 쪽수가 .sheet 수와 같은지 본다.
- 디자인·문장 판단은 하지 않는다. 그건 build의 리뷰와 수정 반복(portfolio-reviewer)이 맡는다.
종료 코드: 성공 0, 실패 1, 실행 불가 2.
"""
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

MEASURE_JS = "<script>\n" + (Path(__file__).resolve().parent / "measure.js").read_text(encoding="utf-8") + "\n</script>\n"
# 화면 보기용 장식(회색 바탕, 종이 간격·그림자)을 끄고 인쇄와 같은 상태로 잰다
PRINT_STATE_CSS = ("<style>html,body{background:#fff !important;margin:0 !important;padding:0 !important}"
                   ".sheet{margin:0 !important;box-shadow:none !important}</style>")


def find_chrome() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if path := shutil.which(name):
            return path
    print("Chrome/Chromium을 찾을 수 없다 (Ubuntu: sudo apt install chromium-browser, macOS: Chrome 설치)")
    sys.exit(2)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def inject(html: str, snippet: str, before: str) -> str:
    idx = html.lower().rfind(before)
    if idx < 0:
        print(f"{before} 태그가 없다")
        sys.exit(2)
    return html[:idx] + snippet + html[idx:]


def chrome(args: list[str]) -> str:
    base = [find_chrome(), "--headless", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=20000"]
    return subprocess.run(base + args, capture_output=True, text=True, timeout=120).stdout


def measure(url: str) -> dict:
    dom = chrome(["--dump-dom", url])
    m = re.search(r'<pre id="__measure">([^<]*)</pre>', dom)
    if not m:
        print("실측 실패: 페이지 로드나 폰트 로딩이 끝나지 않았다")
        sys.exit(2)
    return json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))


def pdf_pages(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def main(argv: list[str]) -> int:
    png = "--png" in argv
    args = [a for a in argv if a != "--png"]
    if len(args) != 2 or not Path(args[0]).is_file():
        print(__doc__.strip().splitlines()[2])
        print(__doc__.strip().splitlines()[3])
        return 2
    if not png and not shutil.which("pdfinfo"):
        print("pdfinfo가 없다 (Ubuntu: sudo apt install poppler-utils, macOS: brew install poppler)")
        return 2
    src, out = Path(args[0]).resolve(), Path(args[1]).resolve()
    html = src.read_text(encoding="utf-8")
    tmp = src.parent / "_measure.html"
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                               "--directory", str(src.parent)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    base = f"http://127.0.0.1:{port}"
    try:
        tmp.write_text(inject(inject(html, PRINT_STATE_CSS, "</head>"), MEASURE_JS, "</body>"), encoding="utf-8")
        m = measure(f"{base}/{tmp.name}")
        if png:
            # 문서 전체 높이로 찍는다(시안은 1쪽과 프로젝트 쪽을 같이 보여준다). 너무 길면 4쪽까지만
            height = min(max(int(m["height"]), 1123), 1123 * 4)
            out.unlink(missing_ok=True)
            chrome(["--hide-scrollbars", f"--window-size=794,{height}", f"--screenshot={out}", f"{base}/{src.name}"])
            if not out.exists():
                print("PNG 출력 실패")
                return 1
            print(f"미리보기: {out}")
            return 0

        ok = True
        if not m["sheets"]:
            print('쪽이 없다: A4 한 장마다 class="sheet" 요소로 감싼다')
            return 1
        for s in m["sheets"]:
            if s["overflow"]:
                ok = False
                print(f"넘침: {s['index']}쪽 — 내용이 약 {s['extra']}px 넘친다. 줄이거나 다음 쪽으로 옮긴다")
        for img in m["brokenImages"]:
            ok = False
            print(f"이미지 깨짐: {img}")
        print(f"로드된 글꼴: {', '.join(sorted(set(m['fonts']))) or '없음 (웹폰트 로딩 실패 가능성)'}")
        if not ok:
            print("실패: PDF를 만들지 않았다")
            return 1

        out.unlink(missing_ok=True)
        chrome(["--no-pdf-header-footer", f"--print-to-pdf={out}", f"{base}/{src.name}"])
        if not out.exists():
            print("PDF 출력 실패")
            return 1
        pages = pdf_pages(out)
        if pages != len(m["sheets"]):
            print(f"쪽수 불일치: PDF {pages}쪽 / sheet {len(m['sheets'])}개 — sheet 크기(210mm×297mm)와 @page 설정을 확인한다")
            return 1
        print(f"통과: {out} ({pages}쪽)")
        return 0
    finally:
        server.terminate()
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
