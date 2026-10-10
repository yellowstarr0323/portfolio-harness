#!/usr/bin/env python3
"""근거 원문 보호 훅(PreToolUse) — 모델이 portfolio/sources/interview-log.md와 .interview-log.json을 고치지 못하게 막는다.

근거 원문은 훅(log_answers.py)만 쓴다(D-TXT-6). 모델이 이 파일에 수치를 적어 넣으면 기록 수치 대조가 무의미해진다.
- Write·Edit·MultiEdit·NotebookEdit: 대상 경로가 근거 원문 파일이면 막는다
- Bash: 명령에 근거 원문 파일 이름이 나오고, 읽기 전용 명령(cat·grep·head 등, 출력 넘기기 없음)이 아니면 막는다
막을 때는 종료 코드 2와 이유(stderr)를 돌려준다 — Claude Code가 도구 실행을 취소하고 이유를 모델에게 보여준다.
그 밖의 경우와 입력이 깨진 경우는 0으로 끝난다(다른 작업을 막지 않는다).
"""
import json
import re
import shlex
import sys

PROTECTED = re.compile(r"(?:^|[/\\\s'\"])\.?interview-log\.(?:md|json)\b")
READ_ONLY = {"cat", "grep", "egrep", "rg", "ugrep", "head", "tail", "wc", "less", "more", "ls", "stat", "file", "diff", "sha256sum", "md5sum"}
WRITE_SIGNS = re.compile(r">|\btee\b|\bsed\s+-i|\bperl\s+-[a-z]*i")
WHY = ("portfolio/sources/interview-log.md는 사용자가 직접 한 말의 기록이라 훅만 쓴다(D-TXT-6). 고치거나 지우지 않는다. "
       "수치를 확인받아야 하면 질문 도구(AskUserQuestion) 선택지에 그 값을 넣어 사용자에게 고르게 한다 — 고른 답은 훅이 자동으로 남긴다.")


def bash_writes(cmd: str) -> bool:
    if not PROTECTED.search(cmd):
        return False
    for part in re.split(r"&&|\|\||;|\|", cmd):
        if not PROTECTED.search(part):
            continue
        try:
            words = shlex.split(part)
        except ValueError:
            return True
        if not words or words[0] not in READ_ONLY or WRITE_SIGNS.search(part):
            return True
    return False


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    tool, inp = event.get("tool_name", ""), event.get("tool_input") or {}
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = str(inp.get("file_path") or inp.get("notebook_path") or "")
        blocked = bool(PROTECTED.search(path))
    elif tool == "Bash":
        blocked = bash_writes(str(inp.get("command") or ""))
    else:
        blocked = False
    if blocked:
        print(WHY, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — 검사 자체가 깨지면 막지 않는다
        sys.exit(0)
