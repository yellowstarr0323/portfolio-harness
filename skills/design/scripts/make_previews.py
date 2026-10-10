#!/usr/bin/env python3
"""디자인 시안 — 사용자의 실제 쪽을 스타일마다 렌더해 나란히 보여준다 (사용자 결정 D-DES-15).

사용법
  make_previews.py <portfolio 폴더> [--vary look|font|accent|heading] [--values a,b,c] [--pages 2] [--set look=color-band]

  --vary    바꿔 볼 축 (기본 look). 나머지는 지금 design.json의 style 그대로
  --values  그 축의 값들 (기본: variants.json의 전부. accent는 #rrggbb 목록을 줘야 한다)
  --pages   앞에서 몇 쪽까지 보여줄지 (기본 2 — 1쪽 프로필 + 첫 프로젝트 첫 쪽)
  --set     시안 전체에 깔 값 (예: 강조색 차이가 잘 보이게 look=color-band). 쉼표로 여러 개: look=editorial,font=plex

결과
  portfolio/review/looks/<축>-<값>/      그 시안의 테마·index.html·page-N.png
  portfolio/review/looks/index.html       폴더 안의 시안 전부를 축별로 나란히 보는 비교 페이지 (브라우저로 연다)

out/index.html은 건드리지 않는다. 시안마다 HTML 사본에 그 테마를 붙여 렌더만 한다.
make_theme.py와 같은 검사(대비·허용 값)를 통과하지 못한 시안은 건너뛰고 이유를 출력한다.
"""
import functools
import http.server
import json
import shutil
import socket
import subprocess
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_theme  # noqa: E402

VARIANTS = make_theme.VARIANTS
AXES = {"look": "looks", "font": "fonts", "heading": "headings"}


def chrome() -> str:
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        p = shutil.which(n)
        if p:
            return p
    sys.exit("Chrome/Chromium이 없다")


def serve(root: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Quiet, directory=str(root))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def label(axis: str, value: str) -> str:
    if axis == "look":
        return VARIANTS["looks"][value]["label"]
    if axis == "font":
        return VARIANTS["fonts"][value]["label"]
    if axis == "heading":
        return VARIANTS["headings"][value]
    return value


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    root = Path(argv[0])
    opts = dict(zip(argv[1::2], argv[2::2]))
    axis = opts.get("--vary", "look")
    pages = int(opts.get("--pages", "2"))
    design = json.loads((root / "design.json").read_text(encoding="utf-8"))
    base = dict(design.get("style") or {})
    for kv in filter(None, opts.get("--set", "").split(",")):
        k, _, val = kv.partition("=")
        base[k] = val
    if not base:
        print("design.json에 style이 없다 — design을 먼저 돈다")
        return 1
    if axis == "accent":
        values = [v for v in opts.get("--values", "").split(",") if v]
        if not values:
            print("--vary accent는 --values #rrggbb,... 가 필요하다")
            return 2
    elif axis in AXES:
        values = opts["--values"].split(",") if "--values" in opts else list(VARIANTS[AXES[axis]])
    else:
        print(f"--vary는 look·font·accent·heading 중 하나 — `{axis}`")
        return 2
    src_html = root / "out" / "index.html"
    if not src_html.exists():
        print("out/index.html이 없다 — 시안은 첫 PDF를 만든 뒤에 만든다")
        return 1
    looks_dir = root / "review" / "looks"
    looks_dir.mkdir(parents=True, exist_ok=True)
    made, skipped = [], []
    srv, port = serve(looks_dir)
    try:
        for val in values:
            st = dict(base)
            st[axis] = val
            if st.get("source") == "auto":
                st["source"] = "user"     # 시안은 사용자가 고르는 단계라 팔레트 밖 강조색도 대비만 통과하면 된다
            v, errs = make_theme.resolve(st, root)
            if errs:
                skipped.append((val, errs))
                continue
            d = looks_dir / f"{axis}-{val.lstrip('#')}"
            if d.exists():
                shutil.rmtree(d)
            d.mkdir()
            for n, t in make_theme.render(v, st).items():
                (d / n).write_text(t, encoding="utf-8")
            shutil.copy2(src_html, d / "index.html")
            (d / "assets").symlink_to((root / "out" / "assets").resolve())
            pdf = d / "preview.pdf"
            subprocess.run([chrome(), "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                            "--virtual-time-budget=10000", "--run-all-compositor-stages-before-draw",
                            f"--print-to-pdf={pdf}", f"http://127.0.0.1:{port}/{d.name}/index.html"],
                           check=True, capture_output=True, timeout=120)
            subprocess.run(["pdftoppm", "-f", "1", "-l", str(pages), "-r", "60", "-png", str(pdf), str(d / "page")],
                           check=True, timeout=120)
            made.append((val, d))
    finally:
        srv.shutdown()
    groups: dict[str, list[str]] = {}
    for d in sorted(p for p in looks_dir.iterdir() if p.is_dir() and list(p.glob("page-*.png"))):
        ax, _, val = d.name.partition("-")
        if ax == "accent":
            val = "#" + val
        imgs = "".join(f'<img src="{d.name}/{p.name}" alt="">' for p in sorted(d.glob("page-*.png")))
        groups.setdefault(ax, []).append(f'<section><h3>{val}</h3><p>{label(ax, val) if ax != "accent" else ""}</p>'
                                         f'<div class="pages">{imgs}</div></section>')
    names = {"look": "전체 스타일", "font": "글꼴", "accent": "강조색", "heading": "제목 모양"}
    body = "".join(f"<h2>{names.get(ax, ax)}</h2>" + "".join(cs) for ax, cs in groups.items())
    (looks_dir / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>디자인 시안</title>"
        "<style>body{font-family:sans-serif;margin:24px;background:#eef0f3}section{background:#fff;padding:16px;"
        "margin:0 0 24px;border-radius:6px}h3{margin:0}p{color:#555;margin:4px 0 12px}.pages{display:flex;gap:12px;"
        "flex-wrap:wrap}.pages img{width:360px;border:1px solid #ccc}</style>"
        "<h1>디자인 시안</h1>" + body, encoding="utf-8")
    print(f"시안 {len(made)}개: {looks_dir / 'index.html'}")
    for val, d in made:
        print(f"  {axis}={val}: {d}")
    for val, errs in skipped:
        print(f"  건너뜀 {axis}={val}: {'; '.join(errs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
