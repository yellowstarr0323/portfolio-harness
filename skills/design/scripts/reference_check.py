#!/usr/bin/env python3
"""레퍼런스 근거 판정 (D-DES-16) — make_theme.py와 build의 export.py가 같이 쓴다.

레퍼런스 모드는 디자인 검사를 끄므로, 사용자가 실제로 레퍼런스를 줬다는 근거가 있을 때만 켠다.
검사가 계속 실패할 때 style.source만 "reference"로 바꿔 통과시키는 것을 막는다.

근거 (portfolio/ 기준)
  - style.reference가 비어 있지 않다
  - http(s) URL이면: 그 URL이 sources/interview-log.md(사용자 말 원문, 훅이 씀)에 있다
  - 파일 경로면: 파일이 실제로 있고(portfolio 기준 상대·절대 경로, ~ 확장), 파일 이름이
    sources/interview-log.md에 있다. 있는지만 보면 모델이 만든 파일(예: 자기 out/ PDF)도 통과하므로
    사용자가 그 파일을 말했는지까지 본다

사용법: reference_check.py <portfolio 폴더>   근거가 있으면 0, 없으면 이유를 출력하고 1
"""
import sys
from pathlib import Path


def reference_problem(style: dict, portfolio: Path) -> str | None:
    """레퍼런스 근거가 없으면 이유(한국어 한 줄), 있으면 None."""
    ref = str((style or {}).get("reference") or "").strip()
    if not ref:
        return "style.reference가 비어 있다 — 사용자가 준 레퍼런스 경로·URL이 없으면 레퍼런스 모드를 쓸 수 없다"
    log_path = portfolio / "sources" / "interview-log.md"
    try:
        log = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        log = None
    if ref.lower().startswith(("http://", "https://")):
        if log is None:
            return f"근거 원문 기록({log_path})이 없어 레퍼런스 URL `{ref}`을 사용자가 줬는지 확인할 수 없다"
        if ref not in log and ref.rstrip("/") not in log:
            return f"레퍼런스 URL `{ref}`이 사용자 말 원문(sources/interview-log.md)에 없다 — 사용자가 준 URL만 쓴다"
        return None
    p = Path(ref).expanduser()
    if not p.is_absolute():
        p = portfolio / p
    if not p.is_file():
        return f"레퍼런스 파일이 없다 — {p}"
    if log is None:
        return f"근거 원문 기록({log_path})이 없어 레퍼런스 파일 `{p.name}`을 사용자가 줬는지 확인할 수 없다"
    if p.name not in log:
        return f"레퍼런스 파일 이름 `{p.name}`이 사용자 말 원문(sources/interview-log.md)에 없다 — 사용자가 준 파일만 쓴다"
    return None


if __name__ == "__main__":
    import json
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    pf = Path(sys.argv[1])
    try:
        st = json.loads((pf / "design.json").read_text(encoding="utf-8")).get("style") or {}
    except (OSError, ValueError) as e:
        print(f"design.json을 읽지 못했다 — {e}")
        sys.exit(1)
    why = reference_problem(st, pf)
    print(why or "레퍼런스 근거: 있음")
    sys.exit(1 if why else 0)
