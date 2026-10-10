#!/usr/bin/env python3
"""근거 원문 기록 훅 — 사용자가 직접 한 말을 portfolio/sources/interview-log.md에 그대로 남긴다.

모델이 기록(facts)에 수치를 지어 넣어도 그 뒤 검사가 모두 통과하던 구멍을 막는 장치다(2026-10-10 구조 평가).
이 파일은 모델이 아니라 훅이 쓴다. facts_lint.py가 기록의 수치를 이 원문과 받은 자료(sources/)에 대조한다.

남기는 것 (세션 기록 transcript_path와 훅 입력에서)
- 사용자가 보낸 메시지 원문 (명령 출력·작업 알림·시스템 메시지는 뺀다)
- 질문 도구(AskUserQuestion)의 답: 사용자가 고른 선택지나 직접 친 글만. 질문 문장과 고르지 않은 선택지는
  모델이 쓴 글이라 남기지 않는다
남기지 않는 것: 모델의 말 전부

이벤트
- UserPromptSubmit: 이번 메시지 + 세션 기록에서 빠진 것
- PostToolUse(AskUserQuestion): 이번 답 + 세션 기록에서 빠진 것
- Stop: 세션 기록에서 빠진 것 (portfolio/가 생기기 전에 보낸 첫 메시지도 여기서 들어간다)
범위: 작업 폴더에 portfolio/가 있을 때만. 같은 글은 한 번만 남긴다(sources/.interview-log.json에 해시).
무슨 일이 있어도 0으로 끝난다 — 훅 실패가 사용자의 입력이나 턴 종료를 막으면 안 된다.
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

SKIP_PREFIX = ("<local-command", "<command-name>", "<command-message>", "<command-args>", "<task-notification>",
               "<bash-input>", "<bash-stdout>", "<bash-stderr>", "<system-reminder>", "[Request interrupted")
HEADER = ("# 근거 원문 기록\n\n"
          "훅(hooks/log_answers.py)이 사용자가 직접 한 말과 질문 답을 그대로 옮겨 적는다. **손으로 고치지 않는다.**\n"
          "기록(facts)의 수치는 이 파일이나 받은 자료(sources/)에 있어야 한다(facts_lint.py가 대조).\n")


def user_text(text: str) -> str | None:
    t = (text or "").strip()
    if not t or t.startswith(SKIP_PREFIX):
        return None
    return t


def answers_text(result) -> str | None:
    """AskUserQuestion 결과에서 사용자가 고르거나 친 답만 꺼낸다."""
    if not isinstance(result, dict):
        return None
    vals = [str(v) for v in (result.get("answers") or {}).values() if str(v).strip()]
    for note in (result.get("annotations") or {}).values():          # 선택지에 덧붙인 메모(사용자 입력)
        if isinstance(note, dict) and str(note.get("notes") or "").strip():
            vals.append(str(note["notes"]))
    return "\n".join(f"- {v}" for v in vals) or None


def from_transcript(path: str | None) -> list[tuple[str, str, str]]:
    """(시각, 종류, 글) 목록. 읽지 못하면 빈 목록."""
    out: list[tuple[str, str, str]] = []
    if not path:
        return out
    ask_ids: set[str] = set()
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                msg = d.get("message") if isinstance(d.get("message"), dict) else {}
                content = msg.get("content")
                ts = str(d.get("timestamp", ""))[:16].replace("T", " ")
                if d.get("type") == "assistant" and isinstance(content, list):
                    ask_ids.update(x.get("id") for x in content
                                   if isinstance(x, dict) and x.get("type") == "tool_use" and x.get("name") == "AskUserQuestion")
                if d.get("type") != "user" or d.get("isMeta"):
                    continue
                if isinstance(content, str):
                    if t := user_text(content):
                        out.append((ts, "메시지", t))
                elif isinstance(content, list):
                    for x in content:
                        if not isinstance(x, dict):
                            continue
                        if x.get("type") == "text" and (t := user_text(x.get("text", ""))):
                            out.append((ts, "메시지", t))
                        elif x.get("type") == "tool_result" and x.get("tool_use_id") in ask_ids:
                            if t := answers_text(d.get("toolUseResult")):
                                out.append((ts, "질문 답", t))
    except OSError:
        pass
    return out


def append(portfolio: Path, entries: list[tuple[str, str, str]]) -> None:
    src = portfolio / "sources"
    src.mkdir(exist_ok=True)
    log, seen_file = src / "interview-log.md", src / ".interview-log.json"
    try:
        seen = set(json.loads(seen_file.read_text(encoding="utf-8")).get("seen", []))
    except (OSError, ValueError):
        seen = set()
    new = []
    for ts, kind, text in entries:
        h = hashlib.sha256(text.encode()).hexdigest()[:20]
        if h in seen:
            continue
        seen.add(h)
        new.append(f"\n## {ts or datetime.now().strftime('%Y-%m-%d %H:%M')} · {kind}\n\n{text}\n")
    if not new:
        return
    if not log.exists():
        log.write_text(HEADER, encoding="utf-8")
    with open(log, "a", encoding="utf-8") as f:
        f.writelines(new)
    seen_file.write_text(json.dumps({"seen": sorted(seen)}), encoding="utf-8")


def main() -> None:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    portfolio = Path(event.get("cwd") or ".") / "portfolio"
    if not portfolio.is_dir():
        return
    entries = from_transcript(event.get("transcript_path"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = event.get("hook_event_name")
    if name == "UserPromptSubmit" and (t := user_text(event.get("prompt", ""))):
        entries.append((now, "메시지", t))
    elif name == "PostToolUse" and event.get("tool_name") == "AskUserQuestion":
        if t := answers_text(event.get("tool_response")):
            entries.append((now, "질문 답", t))
    append(portfolio, entries)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 — 훅은 어떤 경우에도 막지 않는다
        pass
    sys.exit(0)
