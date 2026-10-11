#!/usr/bin/env python3
"""완성된 PDF를 테스트 운영자의 Discord 채널로 보낸다(웹훅).

사용법: upload.py <portfolio/out/portfolio.pdf> [--config <upload.json>] [--name <이름>]

부르는 곳은 턴 끝 훅(hooks/send_on_done.py) 하나다. 모델은 부르지 않는다(rules/decisions.md "PDF 전송").
설정 파일(기본: 플러그인 루트의 upload.json)이 없으면 아무것도 하지 않는다 — 개발 환경과 일반 배포에서는 꺼져 있다.
  {"discord_webhook": "https://discord.com/api/webhooks/<id>/<token>"}
웹훅 URL은 그 채널에 글을 올릴 수 있는 비밀값이다. 출력에 찍지 않고, 레포에 올리지 않는다(.gitignore).

1. 이름은 --name이 없으면 portfolio/profile.md의 "이름:" 값에서 읽는다
2. 웹훅에 <이름>.pdf 첨부 + 한 줄 메시지(이름·시각·크기)를 multipart로 POST 한다
3. 보낸 PDF의 SHA-256을 PDF 옆 .upload.json에 남겨, 같은 PDF는 다시 보내지 않는다
종료 코드: 보냄·이미 보냄·설정 없음 0, 전송 실패 1, 사용법 오류 2.
"""
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

import os

# 기본은 플러그인 루트의 upload.json. HARNESS_UPLOAD_CONFIG로 바꿀 수 있다(회귀 테스트가 가짜 웹훅을 쓸 때)
DEFAULT_CONFIG = Path(os.environ.get("HARNESS_UPLOAD_CONFIG") or Path(__file__).resolve().parents[3] / "upload.json")
MAX_BYTES = 10 * 1024 * 1024   # Discord 웹훅 첨부 한도(부스트 없는 서버)
TIMEOUT = 60
# Discord(Cloudflare)는 기본 Python-urllib User-Agent를 막는 경우가 있다
USER_AGENT = "portfolio-harness-upload (https://github.com/, 1.0)"


def profile_name(pdf: Path) -> str:
    """portfolio/out/portfolio.pdf → portfolio/profile.md의 "이름: 홍길동" 값(출처 표시는 뺀다)."""
    profile = pdf.resolve().parent.parent / "profile.md"
    try:
        text = profile.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if m := re.search(r"^[-*\s]*이름\s*:\s*(.+)$", text, re.M):
        return re.sub(r"\((?:출처|source)\s*:[^)]*\)", "", m.group(1)).strip()
    return ""


def safe_name(raw: str) -> str:
    """파일 이름에 쓸 수 없는 문자(경로·제어 문자·따옴표)를 지운다. 비면 '이름없음'."""
    name = re.sub(r'[\x00-\x1f\x7f/\\:*?"<>|]', "", raw or "")
    return re.sub(r"\s+", " ", name).strip().strip(".")[:40].strip() or "이름없음"


def send(webhook: str, filename: str, content: str, body: bytes) -> int:
    boundary = uuid.uuid4().hex
    payload = json.dumps({"content": content, "allowed_mentions": {"parse": []}}, ensure_ascii=False)
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\n'
        f"Content-Type: application/json\r\n\r\n{payload}\r\n".encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n".encode() + body + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    data = b"".join(parts)
    url = webhook + ("&" if "?" in webhook else "?") + "wait=true"
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status


def main(argv: list[str]) -> int:
    args = argv[1:]
    usage = "사용법: upload.py <pdf> [--config <upload.json>] [--name <이름>]"
    opts = {}
    for flag in ("--config", "--name"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(usage)
                return 2
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    if len(args) != 1:
        print(usage)
        return 2
    config = Path(opts.get("--config", DEFAULT_CONFIG))
    pdf = Path(args[0])

    if not config.is_file():
        print("PDF 전송: 설정 없음 — 건너뜀")
        return 0
    try:
        webhook = json.loads(config.read_text(encoding="utf-8"))["discord_webhook"]
    except (ValueError, KeyError) as e:
        print(f"PDF 전송 실패: 설정 파일을 읽지 못함 — {type(e).__name__}")
        return 1
    if not pdf.is_file():
        print(f"PDF 전송 실패: PDF가 없다 ({pdf})")
        return 1

    body = pdf.read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    state = pdf.parent / ".upload.json"
    try:
        last = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last = {}
    if last.get("sha256") == digest:
        print(f"PDF 전송: 같은 PDF를 이미 보냄 ({last.get('at', '?')}) — 건너뜀")
        return 0
    if len(body) > MAX_BYTES:
        print(f"PDF 전송 실패: {len(body) / 1024 / 1024:.1f}MB — {MAX_BYTES // 1024 // 1024}MB 제한을 넘는다")
        return 1

    name = safe_name(opts.get("--name") or profile_name(pdf))
    at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    filename = f"{name}.pdf"
    try:
        status = send(webhook, filename, f"{name} 포트폴리오 · {at} · {len(body) // 1024:,}KB", body)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:160]
        print(f"PDF 전송 실패: HTTP {e.code} {detail}")
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"PDF 전송 실패: {type(e).__name__} {getattr(e, 'reason', e)}")
        return 1
    if status not in (200, 204):
        print(f"PDF 전송 실패: 응답 {status}")
        return 1

    state.write_text(json.dumps({"sha256": digest, "file": filename, "at": at}, ensure_ascii=False), encoding="utf-8")
    print(f"PDF 전송: 보냄 ({filename}, {len(body) // 1024:,}KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
