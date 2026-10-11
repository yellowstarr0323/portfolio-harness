#!/usr/bin/env python3
"""감사 끝 표시를 out/.build.json에 남긴다 (audit 4-3, D-FLOW-8).

사용법: mark_audit.py <portfolio/out/index.html> <report 파일명>

- "audit": report 파일명, "auditTextSha256": 지금 HTML의 보이는 글자 해시, "indexSha256": 지금 HTML 해시를 적는다.
- 턴 끝 전송 훅(hooks/upload_on_stop.py)은 auditTextSha256이 지금 HTML의 글자와 같을 때만 최종본으로 보고 보낸다.
  감사 뒤 디자인 리뷰로 배치·색만 바꾼 것은 그대로 최종본이고, 문장을 바꿨으면 감사를 다시 해야 간다.
- 해시를 모델이 손으로 적지 않게 하려고 만든 스크립트다.
종료 코드: 성공 0, 실패 1, 사용법 오류 2.
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "build" / "scripts"))
from htmltext import visible_text  # noqa: E402


def text_sha(html: str) -> str:
    """감사 대상인 보이는 글자의 해시. 공백 차이는 무시한다(배치만 바뀐 HTML은 같은 값)."""
    text = " ".join(visible_text(html, skip_attrs=()).split())
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("사용법: mark_audit.py <portfolio/out/index.html> <report 파일명>")
        return 2
    index, report = Path(argv[0]), argv[1]
    try:
        raw = index.read_bytes()
    except OSError as e:
        print(f"감사 표시 실패: HTML을 읽지 못함 — {e}")
        return 1
    mark_path = index.parent / ".build.json"
    try:
        build = json.loads(mark_path.read_text(encoding="utf-8")) if mark_path.exists() else {}
    except ValueError:
        print(f"감사 표시 실패: {mark_path}가 JSON이 아니다")
        return 1
    build.update({
        "indexSha256": hashlib.sha256(raw).hexdigest(),
        "audit": report,
        "auditTextSha256": text_sha(raw.decode("utf-8", errors="replace")),
        "auditedAt": f"{datetime.now():%Y-%m-%dT%H:%M}",
    })
    mark_path.write_text(json.dumps(build, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"감사 표시: {mark_path} (report {report})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
