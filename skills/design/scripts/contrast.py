#!/usr/bin/env python3
"""WCAG 2.x 명도 대비 계산. 사용법: contrast.py <전경 hex> <배경 hex> [<전경> <배경> ...]"""
import sys


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"hex 형식이 아님: {hex_color}")
    channels = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str) -> float:
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def main(args: list[str]) -> int:
    if len(args) < 2 or len(args) % 2:
        print(__doc__)
        return 2
    failed = False
    for fg, bg in zip(args[::2], args[1::2]):
        r = ratio(fg, bg)
        verdict = "본문 OK" if r >= 4.5 else "큰 글자만 OK" if r >= 3 else "FAIL"
        failed |= r < 4.5
        print(f"{fg} on {bg}: {r:.2f}:1  {verdict}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
