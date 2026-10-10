#!/usr/bin/env python3
"""포트폴리오 테마 만들기 — design.json의 `style`로 portfolio/theme/의 세 파일을 만든다.

사용법
  make_theme.py <design.json> <theme 폴더>           style대로 tokens.css·components.css·style.css를 쓴다
  make_theme.py --check <design.json> <theme 폴더>   다시 만들어 보고 지금 파일과 같은지 본다(build 최신 여부)
  make_theme.py --auto <이름>                        레퍼런스가 없을 때 쓸 글꼴·제목 모양 기본 추천(이름 해시)
  make_theme.py --list                               고를 수 있는 전체 스타일·강조색·글꼴·제목 모양

style 형식 (design.json)
  "style": {
    "source": "auto" | "user" | "reference",   auto: AI가 고름 / user: 사용자가 시안을 보고 고름(D-DES-15) / reference: 레퍼런스를 따름
    "reference": "레퍼런스 경로·URL (아니면 null)",
    "look": "minimal" | "editorial" | "color-band" | "dark-header",   전체 스타일(없으면 minimal)
    "accent": "#0369a1",                       auto는 variants.json의 accents 중 하나, user·reference는 대비만 통과하면 아무 색
    "font": "pretendard" | "plex" | "serif-heading"
            | {"imports": [...], "body": "...", "display": "..." | null},   ← reference만
    "heading": "plain" | "bar" | "rule",
    "colors": {"text": "#..", "muted": "#..", "border": "#..", "surface": "#.."},  ← 선택, reference만
    "fontScale": {"name": "38pt", ...},        ← 선택, 범위(variants.json fontScaleRange) 안에서만(reference는 범위 없음)
    "extraCss": "theme/extra.css",             ← 선택, reference만. portfolio/ 기준 경로. 레퍼런스의 배치·장식을 제한 없이 담는다
    "why": "고른 이유 한 줄"
  }

검사 (어기면 종료 코드 1, 파일을 쓰지 않는다)
  - source: reference (D-DES-16): 레퍼런스를 그대로 따른다. 아래 디자인 조건(대비·띠 대비·글자 범위·글꼴 주소·
    extraCss 금지 선언)은 검사하지 않고, 값의 형식(#rrggbb, 숫자pt, 파일 있음)만 본다.
    단 레퍼런스 근거가 있어야 한다(reference_check.py): reference가 있고, 파일이면 실제로 있고 이름이,
    URL이면 그 URL이 sources/interview-log.md(사용자 말 원문)에 있어야 한다
  - 흰 바탕 대비: 본문·보조·강조색 4.5:1 이상, 강조색 위 흰 글자 4.5:1 이상
  - 머리 띠가 있는 look: 띠 위 글자·보조 글자 대비 4.5:1 이상
  - 글자 크기는 역할 범위 안 (rules/user-decisions.md D-DES-3)
  - auto는 variants.json에 있는 값만
  - 글꼴 import는 https://fonts.googleapis.com, https://cdn.jsdelivr.net 만
  - (reference 아닐 때) extraCss 금지 선언 — reference만 extraCss를 쓸 수 있으므로 지금은 쓰이지 않는 규칙이다
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEME = HERE.parent / "theme"
sys.path.insert(0, str(HERE))
from contrast import ratio  # noqa: E402
from reference_check import reference_problem  # noqa: E402

VARIANTS = json.loads((THEME / "variants.json").read_text(encoding="utf-8"))
FS_VARS = {"name": "--fs-name", "pageTitle": "--fs-page-title", "section": "--fs-section", "subtitle": "--fs-subtitle",
           "body": "--fs-body", "meta": "--fs-meta", "caption": "--fs-caption", "code": "--fs-code"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
IMPORT_OK = ("https://fonts.googleapis.com/", "https://cdn.jsdelivr.net/")
EXTRA_BANNED = [(r"font-size", "글자 크기는 tokens의 역할 크기만 쓴다"), (r"@page", "쪽 크기는 바꾸지 않는다"),
                (r"\.sheet\b", "쪽(.sheet) 구조는 바꾸지 않는다"), (r"\bzoom\s*:", "확대·축소는 쓰지 않는다"),
                (r"display\s*:\s*none", "내용을 숨기지 않는다"), (r"position\s*:\s*fixed", "고정 위치 요소는 인쇄에서 반복된다"),
                (r"@import", "글꼴은 style.font.imports로만 불러온다")]


def pick_auto(seed: str) -> dict:
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    fonts, heads, accents = list(VARIANTS["fonts"]), list(VARIANTS["headings"]), list(VARIANTS["accents"])
    return {"font": fonts[h % len(fonts)], "heading": heads[(h // 7) % len(heads)],
            "accent": VARIANTS["accents"][accents[(h // 49) % len(accents)]]}


def resolve(style: dict, root: Path) -> tuple[dict, list[str]]:
    """style을 실제 값으로 풀고 문제 목록을 돌려준다."""
    errs = []
    src = style.get("source")
    if src not in ("auto", "user", "reference"):
        errs.append(f"style.source는 auto·user·reference 중 하나 — `{src}`")
    ref = src == "reference"
    if ref and (why := reference_problem(style, root)):
        errs.append(f"레퍼런스 근거 없음 — {why}")
    look = style.get("look", "minimal")
    if look not in VARIANTS["looks"]:
        errs.append(f"전체 스타일 `{look}`이 없다 ({', '.join(VARIANTS['looks'])})")
        look = "minimal"
    font = style.get("font", "pretendard")
    if isinstance(font, str):
        if font not in VARIANTS["fonts"]:
            errs.append(f"글꼴 `{font}`이 variants.json에 없다 ({', '.join(VARIANTS['fonts'])})")
            font = "pretendard"
        f = VARIANTS["fonts"][font]
    elif ref and isinstance(font, dict) and font.get("body"):
        f = {"imports": font.get("imports", []), "body": font["body"], "display": font.get("display")}
    else:
        errs.append("글꼴을 직접 정하는 건 레퍼런스가 있을 때만, body가 있어야 한다")
        f = VARIANTS["fonts"]["pretendard"]
    for u in f["imports"]:
        if not ref and not u.startswith(IMPORT_OK):
            errs.append(f"글꼴 주소는 {' / '.join(IMPORT_OK)}만 — `{u}`")
    heading = style.get("heading", "plain")
    if heading not in VARIANTS["headings"]:
        errs.append(f"제목 모양 `{heading}`이 없다 ({', '.join(VARIANTS['headings'])})")
        heading = "plain"
    accent = style.get("accent", "")
    if not HEX.match(accent or ""):
        errs.append(f"강조색은 #rrggbb — `{accent}`")
        accent = "#0369a1"
    elif src == "auto" and accent.lower() not in [a.lower() for a in VARIANTS["accents"].values()]:
        errs.append(f"레퍼런스가 없으면 강조색은 variants.json accents 중에서 고른다 — `{accent}`")
    colors = {"text": "#16181d", "muted": "#5b616e", "border": "#e2e8f0", "surface": "#f6f7f9"}
    if style.get("colors"):
        if not ref:
            errs.append("colors는 레퍼런스가 있을 때만 바꾼다")
        for k, v in style["colors"].items():
            if k not in colors or not HEX.match(v):
                errs.append(f"colors.{k} = `{v}` — text·muted·border·surface에 #rrggbb만")
            else:
                colors[k] = v
    for name, fg in (("본문", colors["text"]), ("보조", colors["muted"]), ("강조", accent)):
        r = ratio(fg, "#ffffff")
        if not ref and r < 4.5:
            errs.append(f"{name}색 {fg}의 흰 바탕 대비 {r:.2f}:1 — 4.5:1 이상이어야 한다")
    if not ref and ratio("#ffffff", accent) < 4.5:
        errs.append(f"강조색 {accent} 위 흰 글자 대비가 4.5:1 미만")
    band = {"bg": "transparent", "text": colors["text"], "muted": colors["muted"]}
    spec = VARIANTS["looks"][look]["band"]
    if spec:
        bg = accent if spec["bg"] == "accent" else spec["bg"]
        text = spec["text"]
        muted = mix(text, bg, 0.82)          # 띠 위 보조 글자: 글자색 쪽으로 82%
        if ratio(muted, bg) < 4.5:
            muted = text
        band = {"bg": bg, "text": text, "muted": muted}
        for name, fg in (("띠 글자", text), ("띠 보조 글자", muted)):
            r = ratio(fg, bg)
            if not ref and r < 4.5:
                errs.append(f"{name} {fg}의 띠 {bg} 대비 {r:.2f}:1 — 4.5:1 이상이어야 한다")
    scale = {}
    for k, v in (style.get("fontScale") or {}).items():
        rng = VARIANTS["fontScaleRange"].get(k)
        m = re.fullmatch(r"(\d+(?:\.\d+)?)pt", str(v))
        if not rng or not m:
            errs.append(f"fontScale.{k} = `{v}` — 역할 이름과 `숫자pt`만")
        elif not ref and not rng[0] <= float(m.group(1)) <= rng[1]:
            errs.append(f"fontScale.{k} = {v} — 범위 {rng[0]}~{rng[1]}pt 밖 (D-DES-3)")
        else:
            scale[k] = v
    extra = ""
    if style.get("extraCss"):
        if not ref:
            errs.append("extraCss는 레퍼런스가 있을 때만 쓴다")
        p = root / style["extraCss"]
        if not p.exists():
            errs.append(f"extraCss 파일이 없다 — {p}")
        else:
            extra = p.read_text(encoding="utf-8")
            body = re.sub(r"/\*.*?\*/", "", extra, flags=re.S)
            for pat, why in EXTRA_BANNED:
                if not ref and re.search(pat, body, re.I):
                    errs.append(f"extraCss에 `{pat}` — {why}")
    return {"font": f, "heading": heading, "accent": accent, "colors": colors, "scale": scale, "extra": extra,
            "look": look, "band": band}, errs


def mix(fg: str, bg: str, t: float) -> str:
    """fg와 bg를 t:(1-t)로 섞은 #rrggbb."""
    a, b = fg.lstrip("#"), bg.lstrip("#")
    return "#" + "".join(f"{round(int(a[i:i+2], 16) * t + int(b[i:i+2], 16) * (1 - t)):02x}" for i in (0, 2, 4))


def render(v: dict, style: dict) -> dict[str, str]:
    base = (THEME / "tokens.css").read_text(encoding="utf-8")
    a = v["accent"].lstrip("#")
    tint = f"rgba({int(a[0:2], 16)}, {int(a[2:4], 16)}, {int(a[4:6], 16)}, 0.08)"
    imports = "".join(f'@import url("{u}");\n' for u in v["font"]["imports"])
    imports += '@import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap");\n'
    tokens = re.sub(r'(@import url\("[^"]*"\);\n)+', lambda _: imports, base, count=1)
    head = (f"/* 이 포트폴리오의 테마 — make_theme.py가 design.json style로 만들었다. 손으로 고치지 않는다.\n"
            f"   source: {style.get('source')}  font: {style.get('font') if isinstance(style.get('font'), str) else 'custom'}"
            f"  look: {v['look']}  heading: {v['heading']}  accent: {v['accent']}\n   why: {style.get('why', '')} */\n")
    tokens = head + re.sub(r"^/\*.*?\*/\n", "", tokens, count=1, flags=re.S)
    sub = {"--accent": v["accent"], "--accent-tint": tint, "--text": v["colors"]["text"], "--muted": v["colors"]["muted"],
           "--border": v["colors"]["border"], "--surface": v["colors"]["surface"], "--font-body": v["font"]["body"],
           "--band-bg": v["band"]["bg"], "--band-text": v["band"]["text"], "--band-muted": v["band"]["muted"]}
    sub.update({FS_VARS[k]: val for k, val in v["scale"].items()})
    for var, val in sub.items():
        tokens, n = re.subn(rf"({re.escape(var)}:\s*)[^;]+;", lambda m: m.group(1) + val + ";", tokens, count=1)
        assert n == 1, var
    display = v["font"]["display"] or "var(--font-body)"
    tokens = tokens.replace("  --font-mono:", f"  --font-display: {display};\n  --font-mono:", 1)
    style_css = ("/* 제목 글꼴·제목 모양·전체 스타일·레퍼런스 장식 — make_theme.py가 만든다. build는 components.css 다음에 <link>한다. */\n"
                 ':root [data-role="name"], :root [data-role="page-title"], :root [data-role="section-title"] '
                 "{ font-family: var(--font-display); }\n\n"
                 + (THEME / "variants" / f"heading-{v['heading']}.css").read_text(encoding="utf-8")
                 + "\n" + (THEME / "variants" / f"look-{v['look']}.css").read_text(encoding="utf-8"))
    if v["extra"]:
        style_css += "\n/* 레퍼런스의 배치·장식 (extraCss, D-DES-16) */\n" + v["extra"]
    return {"tokens.css": tokens, "components.css": (THEME / "components.css").read_text(encoding="utf-8"),
            "style.css": style_css}


def main(argv: list[str]) -> int:
    if argv[:1] == ["--list"]:
        print("전체 스타일:", ", ".join(f"{k} ({d['label']})" for k, d in VARIANTS["looks"].items()))
        print("강조색:", ", ".join(f"{k} {c}" for k, c in VARIANTS["accents"].items()))
        print("글꼴:", ", ".join(f"{k} ({f['label']})" for k, f in VARIANTS["fonts"].items()))
        print("제목 모양:", ", ".join(f"{k} ({d})" for k, d in VARIANTS["headings"].items()))
        return 0
    if argv[:1] == ["--auto"] and len(argv) == 2:
        print(json.dumps(pick_auto(argv[1]), ensure_ascii=False))
        return 0
    check = argv[:1] == ["--check"]
    args = argv[1:] if check else argv
    if len(args) != 2:
        print(__doc__)
        return 2
    design, out = Path(args[0]), Path(args[1])
    style = json.loads(design.read_text(encoding="utf-8")).get("style")
    if not style:
        print(f"{design}에 style이 없다 — design을 다시 돈다")
        return 1
    v, errs = resolve(style, design.parent)
    if errs:
        print("테마 검사 실패:")
        for e in errs:
            print(f"  - {e}")
        return 1
    files = render(v, style)
    if check:
        diff = [n for n, t in files.items() if not (out / n).exists() or (out / n).read_text(encoding="utf-8") != t]
        print("테마 최신: 일치" if not diff else f"테마가 design.json style·원본과 다르다: {', '.join(diff)} — design을 다시 돈다")
        return 1 if diff else 0
    out.mkdir(parents=True, exist_ok=True)
    for n, t in files.items():
        (out / n).write_text(t, encoding="utf-8")
    print(f"테마 작성: {out}/tokens.css, components.css, style.css  (스타일 {v['look']}, 강조 {v['accent']}, 글꼴 "
          f"{style['font'] if isinstance(style['font'], str) else 'custom'}, 제목 {v['heading']})")
    for name, fg in (("본문", v["colors"]["text"]), ("보조", v["colors"]["muted"]), ("강조", v["accent"])):
        print(f"  대비 {name} {fg}: {ratio(fg, '#ffffff'):.2f}:1")
    if v["band"]["bg"] != "transparent":
        print(f"  띠 {v['band']['bg']} 위 글자 {ratio(v['band']['text'], v['band']['bg']):.2f}:1, 보조 {ratio(v['band']['muted'], v['band']['bg']):.2f}:1")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
