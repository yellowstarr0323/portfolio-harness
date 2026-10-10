#!/usr/bin/env python3
"""이미지 폴더의 파일 목록과 픽셀 크기·비율을 출력한다 (표준 라이브러리만 사용).

사용법: image_info.py <portfolio/images> [--json]

- 지원: png, jpg/jpeg, webp, gif, svg. 그 밖의 파일은 '지원 안 함'으로 표시한다
- svg는 벡터라 흐릿해지지 않는다. 크기는 width/height 또는 viewBox에서 읽고, 최대 인쇄 폭은 '제한 없음'이다
- 비율(가로/세로)로 배치 성격을 적는다: 가로형(≥1.3) / 세로형(≤0.8, 휴대폰 화면 캡처 등) / 정사각형에 가까움
- 'A4 본문 폭 최대 인쇄 폭(mm)': 이 이미지를 선명하게(약 200dpi) 찍을 수 있는 최대 폭. 이보다 크게 배치하면 흐릿하다
종료 코드: 항상 0. 폴더가 없으면 2.
"""
import json
import re
import struct
import sys
from pathlib import Path

DPI_SHARP = 200
MM_PER_INCH = 25.4


def png_size(b: bytes):
    if b[:8] == b"\x89PNG\r\n\x1a\n" and b[12:16] == b"IHDR":
        return struct.unpack(">II", b[16:24])
    return None


def gif_size(b: bytes):
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", b[6:10])
    return None


def webp_size(b: bytes):
    if b[:4] != b"RIFF" or b[8:12] != b"WEBP":
        return None
    kind = b[12:16]
    if kind == b"VP8 ":
        w, h = struct.unpack("<HH", b[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if kind == b"VP8L":
        v = int.from_bytes(b[21:25], "little")
        return (v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1
    if kind == b"VP8X":
        return int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1
    return None


def jpeg_size(path: Path):
    with path.open("rb") as f:
        if f.read(2) != b"\xff\xd8":
            return None
        while True:
            marker = f.read(2)
            if len(marker) < 2 or marker[0] != 0xFF:
                return None
            while marker[1] == 0xFF:                      # 채움 바이트
                marker = marker[1:] + f.read(1)
            m = marker[1]
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:     # 길이 없는 마커
                continue
            seg_len = struct.unpack(">H", f.read(2))[0]
            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                f.read(1)
                h, w = struct.unpack(">HH", f.read(4))
                return w, h
            f.seek(seg_len - 2, 1)


def svg_size(path: Path):
    head = path.read_text(encoding="utf-8", errors="ignore")[:4000]
    m = re.search(r"<svg\b[^>]*>", head, re.S)
    if not m:
        return None
    tag = m.group()
    num = lambda a: (lambda v: float(v.group(1)) if v else None)(re.search(rf'\b{a}="\s*([\d.]+)(?:px)?\s*"', tag))
    w, h = num("width"), num("height")
    if not (w and h):
        vb = re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', tag)
        if not vb:
            return None
        w, h = float(vb.group(1)), float(vb.group(2))
    return round(w), round(h)


def size_of(path: Path):
    ext = path.suffix.lower()
    if ext == ".svg":
        return svg_size(path)
    if ext in (".jpg", ".jpeg"):
        return jpeg_size(path)
    head = path.read_bytes()[:64]
    return png_size(head) or gif_size(head) or webp_size(head)


def shape(w: int, h: int) -> str:
    r = w / h
    if r >= 1.3:
        return "가로형"
    if r <= 0.8:
        return "세로형"
    return "정사각형에 가까움"


def main(folder: str, as_json: bool) -> int:
    root = Path(folder)
    if not root.is_dir():
        print(f"폴더가 없다: {root}")
        return 2
    rows = []
    for p in sorted(x for x in root.rglob("*") if x.is_file() and not x.name.startswith(".")):
        rel = str(p.relative_to(root))
        try:
            wh = size_of(p)
        except (OSError, struct.error):
            wh = None
        if not wh:
            rows.append({"file": rel, "supported": False})
            continue
        w, h = wh
        vector = p.suffix.lower() == ".svg"
        rows.append({"file": rel, "supported": True, "width": w, "height": h,
                     "ratio": round(w / h, 3), "shape": shape(w, h), "vector": vector,
                     "maxPrintWidthMm": None if vector else round(w / DPI_SHARP * MM_PER_INCH),
                     "kb": round(p.stat().st_size / 1024)})
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("이미지가 없다")
        return 0
    print("| 파일 | 크기(px) | 비율 | 모양 | 선명하게 찍을 수 있는 최대 폭 | 용량 |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        if not r["supported"]:
            print(f"| {r['file']} | 지원 안 함 (png/jpg/webp/gif/svg만) | | | | |")
            continue
        maxw = "제한 없음 (벡터)" if r["vector"] else f"{r['maxPrintWidthMm']}mm"
        print(f"| {r['file']} | {r['width']}×{r['height']} | {r['ratio']} | {r['shape']} | {maxw} | {r['kb']}KB |")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--json"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], "--json" in sys.argv))
