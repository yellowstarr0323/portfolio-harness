#!/usr/bin/env python3
"""Stop 훅 — 턴이 끝날 때 portfolio/out/portfolio.pdf가 새로 바뀌었고 검사를 통과했으면 보낸다(D-FLOW-8).

모델이 끝 보고 전에 upload.py를 부르는 것을 잊거나, 스킬 흐름 밖에서 PDF를 다시 만들어도(2026-10-10 pf-new에서
실제로 그랬다) 전송이 빠지지 않게 하는 장치다.
- 범위: 하네스로 포트폴리오를 만드는 세션에서만 돈다 — 작업 폴더에 portfolio/interview-state.md가 있고, 이 세션 기록
  (transcript_path)에 export.py를 실행한 Bash 도구 호출이 있어야 한다(글자만 있는 줄은 세지 않음). 플러그인이 켜진 다른 작업 세션에서는 보내지 않는다
- 보내는 조건: 플러그인 루트에 upload.json이 있음 + 작업 폴더에 portfolio/out/portfolio.pdf가 있음 +
  export.py가 남긴 out/.export.json이 같은 PDF(sha256)를 "ok"로 기록함. 같은 PDF는 upload.py가 한 번만 보낸다
- **최종본만 보낸다**(D-FLOW-8, 10-10): 감사(audit)가 끝난 HTML로 만든 PDF여야 한다 — out/.build.json에 "audit"이 있고
  그 indexSha256이 지금 out/index.html과 같아야 한다. 첫 PDF, 디자인 고르기·리뷰 회차 중간본, 감사 질문을 기다리는 턴의
  PDF는 보내지 않는다. 감사 뒤에 HTML을 다시 고쳤으면 흐름 끝에서 모델이 upload.py를 부를 때 간다
- 무슨 일이 있어도 0으로 끝난다 — Stop 훅이 실패하면 사용자의 턴 종료를 막는다
결과는 out/.upload.log에 한 줄씩 남긴다(사용자 화면에는 나오지 않는다).
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ROOT / "skills" / "build" / "scripts" / "upload.py"


def ran_export(transcript: str | None) -> bool:
    """이 세션에서 export.py를 실제로 실행했는지. 기록을 읽지 못하면 보내지 않는다.

    세션 기록(JSONL)에서 assistant 메시지의 Bash tool_use 중 input.command에 export.py가 있을 때만 참이다.
    줄 어딘가에 "export.py" 글자만 있는 경우(스킬 본문·사용자 말·도구 결과)는 세지 않는다. 깨진 줄은 건너뛴다.
    """
    if not transcript:
        return False
    try:
        with open(transcript, "rb") as f:
            for raw in f:
                if b"export.py" not in raw:
                    continue                                # 빠른 거르기
                try:
                    entry = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or entry.get("type") != "assistant":
                    continue
                msg = entry.get("message")
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for item in content:
                    if not isinstance(item, dict) or item.get("type") != "tool_use" or item.get("name") != "Bash":
                        continue
                    inp = item.get("input")
                    if isinstance(inp, dict) and "export.py" in str(inp.get("command", "")):
                        return True
    except OSError:
        return False
    return False


def audited(out: Path) -> bool:
    """감사가 끝난 HTML인지: .build.json의 audit 표시 + 감사 뒤 HTML이 바뀌지 않음."""
    try:
        build = json.loads((out / ".build.json").read_text(encoding="utf-8"))
        html = (out / "index.html").read_bytes()
    except (OSError, ValueError):
        return False
    return bool(build.get("audit")) and build.get("indexSha256") == hashlib.sha256(html).hexdigest()


def main() -> None:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        event = {}
    cwd = Path(event.get("cwd") or ".")
    pdf = cwd / "portfolio" / "out" / "portfolio.pdf"
    if not pdf.is_file() or not (cwd / "portfolio" / "interview-state.md").is_file():
        return                                              # 하네스 포트폴리오 폴더가 아님
    if not ran_export(event.get("transcript_path")):
        return                                              # 이 세션에서 PDF를 만들지 않았다
    try:
        mark = json.loads((pdf.parent / ".export.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return                                              # export.py 검사를 거치지 않은 PDF
    if not mark.get("ok") or mark.get("sha256") != hashlib.sha256(pdf.read_bytes()).hexdigest():
        return                                              # 검사 실패했거나, 검사 뒤에 PDF가 바뀜
    if not audited(pdf.parent):
        return                                              # 감사 전 중간본
    r = subprocess.run([sys.executable, str(UPLOAD), str(pdf)], capture_output=True, text=True, timeout=80)
    line = (r.stdout.strip().splitlines() or ["(출력 없음)"])[-1]
    if "설정 없음" in line or "이미 보냄" in line:
        return
    with open(pdf.parent / ".upload.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().astimezone():%Y-%m-%d %H:%M} [턴 끝 훅] {line}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 — 훅은 어떤 경우에도 턴 종료를 막지 않는다
        pass
    sys.exit(0)
