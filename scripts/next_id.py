#!/usr/bin/env python3
"""rules/user-decisions.md와 rules/history.md에서 다음 번호를 알려준다.

사용법: next_id.py <접두어>   예) next_id.py D-DES  →  D-DES-18,  next_id.py U  →  U-13,  next_id.py E  →  E-12

결정(D-*·R-EVD-*)과 사용자 결정 기록(U-*)은 user-decisions.md, 이력(C-*·E-*)은 history.md에 있다. 두 파일을 함께 본다.
두 세션이 동시에 결정을 추가하면 같은 번호를 쓸 수 있다(10-10 D-DES-14 충돌). 번호는 기억이 아니라
이 스크립트로 추가 직전에 정하고, 붙인 뒤 회귀 테스트(docs 결정 번호 중복 없음)가 중복을 잡는다.
"""
import re
import sys
from pathlib import Path

RULES = Path(__file__).resolve().parent.parent / "rules"
FILES = (RULES / "user-decisions.md", RULES / "history.md")


def main(prefix: str) -> int:
    prefix = prefix.rstrip("-")
    text = "\n".join(f.read_text(encoding="utf-8") for f in FILES if f.exists())
    nums = [int(n) for n in re.findall(rf"^\| {re.escape(prefix)}-(\d+) \|", text, re.M)]
    print(f"{prefix}-{max(nums, default=0) + 1}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
