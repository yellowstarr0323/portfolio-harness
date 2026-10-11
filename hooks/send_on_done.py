#!/usr/bin/env python3
"""Stop 훅 — 리뷰까지 끝난 최종 PDF를 Discord로 보낸다(rules/decisions.md "PDF 전송").

보내는 조건(모두):
- 작업 폴더에 portfolio/state.md가 있고 `stage: done`
- portfolio/out/portfolio.pdf가 있음
- portfolio/review/portfolio-reviewer-*.md 중 가장 최근 파일이 PDF보다 나중에 저장됨
  — 리뷰어가 이 PDF를 평가한 뒤라는 뜻이다. 끝난 뒤 PDF를 다시 만들었으면 리뷰를 다시 할 때까지 보내지 않는다
- 플러그인 루트에 upload.json이 있음(없으면 upload.py가 건너뜀). 같은 PDF는 upload.py가 한 번만 보낸다

작업 폴더 찾기: 모델이 Bash에서 `cd portfolio`를 하면 훅이 받는 cwd가 portfolio/ 안이 된다(2026-10-11 E2E에서
이것 때문에 전송이 빠졌다). 그래서 CLAUDE_PROJECT_DIR, cwd, cwd의 부모 폴더 순서로 portfolio/state.md를 찾는다.
모델은 전송하지 않고 끝 보고에 전송 결과를 적지 않는다. 결과는 portfolio/out/.upload.log에 남는다.
무슨 일이 있어도 0으로 끝난다 — Stop 훅이 실패하면 사용자의 턴 종료를 막는다.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

UPLOAD = Path(__file__).resolve().parent.parent / "skills" / "build" / "scripts" / "upload.py"


def find_root(cwd: str | None) -> Path | None:
    starts = [os.environ.get("CLAUDE_PROJECT_DIR"), cwd]
    for start in filter(None, starts):
        p = Path(start).resolve()
        for d in (p, *p.parents):
            if (d / "portfolio" / "state.md").is_file():
                return d
    return None


def ready(portfolio: Path) -> bool:
    try:
        state = (portfolio / "state.md").read_text(encoding="utf-8")
    except OSError:
        return False
    if not re.search(r"^[-*\s]*stage\s*:\s*done\b", state, re.M):
        return False
    pdf = portfolio / "out" / "portfolio.pdf"
    reviews = list((portfolio / "review").glob("portfolio-reviewer-*.md"))
    if not pdf.is_file() or not reviews:
        return False
    return max(r.stat().st_mtime for r in reviews) >= pdf.stat().st_mtime


def main() -> None:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        event = {}
    root = find_root(event.get("cwd"))
    if root is None:
        return
    portfolio = root / "portfolio"
    if not ready(portfolio):
        return
    pdf = portfolio / "out" / "portfolio.pdf"
    r = subprocess.run([sys.executable, str(UPLOAD), str(pdf)], capture_output=True, text=True, timeout=80)
    line = (r.stdout.strip().splitlines() or ["(출력 없음)"])[-1]
    if "설정 없음" in line or "이미 보냄" in line:
        return
    with open(pdf.parent / ".upload.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().astimezone():%Y-%m-%d %H:%M} {line}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 — 훅은 어떤 경우에도 턴 종료를 막지 않는다
        pass
    sys.exit(0)
