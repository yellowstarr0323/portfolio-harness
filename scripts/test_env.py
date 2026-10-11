#!/usr/bin/env python3
"""하네스 E2E 테스트용 환경 준비·복구.

사용법: test_env.py start [--keep-omc] [--keep-claude-md]
        test_env.py end
        test_env.py status

처음 쓰는 사람과 같은 조건에서 하네스를 시험하려고, 결과를 오염시키는 사용자 설정만 잠시 끈다.

| 항목 | 위치 | start | end |
|---|---|---|---|
| 위키 훅 | settings.json hooks.UserPromptSubmit 중 my-wiki를 읽는 항목 | 그 항목만 뺀다 | 뺀 항목만 원래 자리에 다시 넣는다 |
| OMC | settings.json enabledPlugins의 oh-my-claudecode 항목 | true면 false로 | start가 바꾼 것만 원래 값으로 |
| 전역 CLAUDE.md | ~/.claude/CLAUDE.md | 백업 폴더로 옮긴다 | 그 자리가 비어 있으면 되돌린다 |

안전 장치
- 시작 전에 settings.json과 CLAUDE.md를 백업하고, 백업이 원본과 같은지 확인한 뒤에만 바꾼다.
- 바꾼 것만 state.json에 기록하고 end는 그것만 되돌린다. 원래 꺼져 있던 설정은 켜지 않는다.
- settings.json은 통째로 덮어쓰지 않는다. 테스트 중 다른 설정이 바뀌어도 그대로 두고 해당 항목만 고친다.
- start를 두 번 하면 멈춘다(백업이 덮어써지지 않게). start 없이 end를 하면 멈춘다.
- 훅·스킬·플러그인 설정은 Claude Code 세션을 시작할 때 읽힌다. 테스트는 start 뒤 새로 연 세션에서 하고,
  end 뒤에도 원래 작업은 새 세션에서 한다.

대상 폴더는 기본이 ~/.claude이고, 환경변수 HARNESS_TEST_CLAUDE_DIR로 바꿀 수 있다(스크립트 자체 테스트용).
종료 코드: 성공 0, 실패·복구 안 된 항목 있음 1, 사용법 오류 2.
"""
import filecmp
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

CLAUDE = Path(os.environ.get("HARNESS_TEST_CLAUDE_DIR", Path.home() / ".claude"))
SETTINGS = CLAUDE / "settings.json"
CLAUDE_MD = CLAUDE / "CLAUDE.md"
WORK = CLAUDE / "harness-test"
STATE = WORK / "state.json"
WIKI_MARK = "my-wiki"
OMC_MARK = "oh-my-claudecode"


def load_settings() -> dict:
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def save_settings(d: dict) -> None:
    # 임시 파일에 쓰고 바꿔치기 — 쓰다가 실패해도 원본이 반쯤 깨지지 않게
    fd, tmp = tempfile.mkstemp(dir=CLAUDE, prefix=".settings.", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, SETTINGS)


def wiki_entries(d: dict) -> list[tuple[int, dict]]:
    arr = (d.get("hooks") or {}).get("UserPromptSubmit") or []
    return [(i, e) for i, e in enumerate(arr) if WIKI_MARK in json.dumps(e, ensure_ascii=False)]


def omc_keys(d: dict) -> list[str]:
    return [k for k in (d.get("enabledPlugins") or {}) if OMC_MARK in k]


def describe(d: dict) -> list[str]:
    out = [f"위키 훅: {'켜짐' if wiki_entries(d) else '꺼짐'}"]
    for k in omc_keys(d):
        out.append(f"OMC({k}): {'켜짐' if d['enabledPlugins'][k] else '꺼짐'}")
    if not omc_keys(d):
        out.append("OMC: 설치 기록 없음")
    out.append(f"전역 CLAUDE.md: {'있음' if CLAUDE_MD.exists() else '없음'}")
    return out


def start(keep_omc: bool, keep_md: bool) -> int:
    if STATE.exists():
        print(f"이미 테스트 환경이 시작돼 있다 ({STATE}). 먼저 test-end를 실행한다.")
        return 1
    if not SETTINGS.exists():
        print(f"{SETTINGS}가 없다. 바꿀 설정이 없어 멈춘다.")
        return 1
    d = load_settings()
    print("현재 상태:\n  " + "\n  ".join(describe(d)))

    # 1) 백업 — 실패하면 아무것도 바꾸지 않는다
    backup = WORK / ("backup-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    try:
        backup.mkdir(parents=True, exist_ok=False)
        shutil.copy2(SETTINGS, backup / "settings.json")
        if not filecmp.cmp(SETTINGS, backup / "settings.json", shallow=False):
            raise OSError("settings.json 백업이 원본과 다르다")
        if CLAUDE_MD.exists():
            shutil.copy2(CLAUDE_MD, backup / "CLAUDE.md")
            if not filecmp.cmp(CLAUDE_MD, backup / "CLAUDE.md", shallow=False):
                raise OSError("CLAUDE.md 백업이 원본과 다르다")
    except OSError as e:
        print(f"백업 실패: {e}. 설정을 바꾸지 않았다.")
        return 1

    # 2) 바꿀 것만 바꾸고 기록
    changes, skipped = [], []
    entries = wiki_entries(d)
    if entries:
        arr = d["hooks"]["UserPromptSubmit"]
        for i, e in reversed(entries):
            arr.pop(i)
        changes += [{"item": "wiki-hook", "event": "UserPromptSubmit", "index": i, "entry": e} for i, e in entries]
    else:
        skipped.append("위키 훅: 원래 꺼져 있음 — 그대로 둔다(end에서도 켜지 않는다)")
    if keep_omc:
        skipped.append("OMC: --keep-omc로 건드리지 않음")
    else:
        for k in omc_keys(d):
            if d["enabledPlugins"][k] is True:
                d["enabledPlugins"][k] = False
                changes.append({"item": "omc", "key": k, "before": True, "after": False})
            else:
                skipped.append(f"OMC({k}): 원래 꺼져 있음 — 그대로 둔다")
    md_moved = False
    if keep_md:
        skipped.append("전역 CLAUDE.md: --keep-claude-md로 건드리지 않음")
    elif CLAUDE_MD.exists():
        md_moved = True
    else:
        skipped.append("전역 CLAUDE.md: 원래 없음")

    try:
        if any(c["item"] in ("wiki-hook", "omc") for c in changes):
            save_settings(d)
        if md_moved:
            CLAUDE_MD.unlink()        # 백업 폴더에 같은 내용이 있는 것을 위에서 확인했다
            changes.append({"item": "claude-md", "backup": str(backup / "CLAUDE.md")})
    except OSError as e:
        print(f"설정 변경 중 실패: {e}. 백업은 {backup}에 있다.")
        STATE.write_text(json.dumps({"started": datetime.now().isoformat(timespec="seconds"),
                                     "backup": str(backup), "changes": changes}, ensure_ascii=False, indent=2))
        print("지금까지 바꾼 것은 state.json에 기록했다. test-end로 되돌린다.")
        return 1

    STATE.write_text(json.dumps({"started": datetime.now().isoformat(timespec="seconds"),
                                 "backup": str(backup), "changes": changes}, ensure_ascii=False, indent=2),
                     encoding="utf-8")

    # 3) 확인
    d2 = load_settings()
    problems = []
    if any(c["item"] == "wiki-hook" for c in changes) and wiki_entries(d2):
        problems.append("위키 훅이 아직 남아 있다")
    for c in changes:
        if c["item"] == "omc" and d2["enabledPlugins"].get(c["key"]) is not False:
            problems.append(f"{c['key']}가 꺼지지 않았다")
    if md_moved and CLAUDE_MD.exists():
        problems.append("전역 CLAUDE.md가 아직 있다")

    print(f"\n백업: {backup}")
    print("바꾼 것:" + ("".join(f"\n  - {c['item']}" + (f" ({c.get('key')})" if c.get('key') else "") for c in changes) or " 없음"))
    if skipped:
        print("건드리지 않은 것:\n  - " + "\n  - ".join(skipped))
    if problems:
        print("확인 실패:\n  - " + "\n  - ".join(problems))
        return 1
    print("\n테스트 환경 준비 완료. 설정은 세션 시작 때 읽히므로 **새 세션**에서 테스트한다:")
    # 매번 새로 clone한 폴더에서 시작한다(처음 쓰는 사람 조건, 커밋된 내용만). 옛 결과가 남은 폴더를 다시 쓰면 "이어서" 흐름이 섞인다
    work = Path.home() / f"pf-e2e-{datetime.now():%m%d-%H%M}"
    repo = Path(__file__).resolve().parent.parent
    copy_cfg = f" && cp {repo}/upload.json {work}/" if (repo / "upload.json").exists() else ""
    print(f"  git clone -q {repo} {work}{copy_cfg} && cd {work} && claude")
    print("끝나면 test-end를 실행한다.")
    return 0


def end() -> int:
    if not STATE.exists():
        print("시작 기록(state.json)이 없다. test-start를 하지 않았거나 이미 end를 했다. 아무것도 바꾸지 않았다.")
        return 1
    state = json.loads(STATE.read_text(encoding="utf-8"))
    changes = state.get("changes", [])
    restored, failed = [], []

    if any(c["item"] in ("wiki-hook", "omc") for c in changes):
        try:
            d = load_settings()
            shutil.copy2(SETTINGS, Path(state["backup"]) / "settings.before-end.json")
        except (OSError, json.JSONDecodeError) as e:
            print(f"settings.json을 읽을 수 없다: {e}. 아무것도 되돌리지 않았다.")
            return 1
        hooks = d.setdefault("hooks", {})
        for c in sorted((c for c in changes if c["item"] == "wiki-hook"), key=lambda c: c["index"]):
            arr = hooks.setdefault(c["event"], [])
            if c["entry"] in arr:
                restored.append("위키 훅: 이미 들어 있음(그대로)")
                continue
            arr.insert(min(c["index"], len(arr)), c["entry"])
            restored.append("위키 훅: 다시 넣음")
        for c in (c for c in changes if c["item"] == "omc"):
            plugins = d.setdefault("enabledPlugins", {})
            cur = plugins.get(c["key"])
            if cur == c["after"]:
                plugins[c["key"]] = c["before"]
                restored.append(f"OMC({c['key']}): 다시 켬")
            else:
                failed.append(f"OMC({c['key']}): 테스트 중 값이 {cur}로 바뀌어 있어 건드리지 않았다(원래 값 {c['before']})")
        try:
            save_settings(d)
        except OSError as e:
            failed.append(f"settings.json 저장 실패: {e}")

    for c in (c for c in changes if c["item"] == "claude-md"):
        src = Path(c["backup"])
        if CLAUDE_MD.exists():
            if src.exists() and filecmp.cmp(src, CLAUDE_MD, shallow=False):
                restored.append("전역 CLAUDE.md: 이미 같은 내용이 있음(그대로)")
            else:
                failed.append(f"전역 CLAUDE.md: 테스트 중 새 파일이 생겨 덮어쓰지 않았다. 원래 파일은 {src}")
        elif not src.exists():
            failed.append(f"전역 CLAUDE.md: 백업 {src}이 없다")
        else:
            try:
                shutil.copy2(src, CLAUDE_MD)
                restored.append("전역 CLAUDE.md: 되돌림")
            except OSError as e:
                failed.append(f"전역 CLAUDE.md: 되돌리기 실패 {e}. 원래 파일은 {src}")

    # 확인
    d2 = load_settings() if SETTINGS.exists() else {}
    for c in changes:
        if c["item"] == "wiki-hook" and c["entry"] not in (d2.get("hooks") or {}).get(c["event"], []):
            failed.append("위키 훅: 확인해 보니 들어 있지 않다")
        if c["item"] == "omc" and not any(c["key"] in f for f in failed) and (d2.get("enabledPlugins") or {}).get(c["key"]) != c["before"]:
            failed.append(f"OMC({c['key']}): 확인해 보니 원래 값이 아니다")
        if c["item"] == "claude-md" and not CLAUDE_MD.exists():
            failed.append("전역 CLAUDE.md: 확인해 보니 없다")

    print("되돌린 것:" + ("".join(f"\n  - {r}" for r in restored) or " 없음"))
    if not changes:
        print("  (시작할 때 바꾼 것이 없었다)")
    if failed:
        print("되돌리지 못한 것:\n  - " + "\n  - ".join(dict.fromkeys(failed)))
        print(f"state.json을 남겨 둔다({STATE}). 위 항목을 손으로 확인한 뒤 다시 실행하거나 state.json을 지운다.")
        return 1
    done = WORK / f"state-{datetime.now().strftime('%Y%m%d-%H%M%S')}.done.json"
    STATE.rename(done)
    print(f"\n복구 완료. 기록은 {done}, 백업은 {state['backup']}에 남겨 둔다.")
    print("설정은 세션 시작 때 읽히므로, 원래 작업은 새 세션에서 한다.")
    print("현재 상태:\n  " + "\n  ".join(describe(d2)))
    return 0


def status() -> int:
    if SETTINGS.exists():
        print("현재 상태:\n  " + "\n  ".join(describe(load_settings())))
    print(f"테스트 환경: {'시작됨 (' + str(STATE) + ')' if STATE.exists() else '시작 안 됨'}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in ("start", "end", "status"):
        print(__doc__)
        sys.exit(2)
    if args[0] == "start":
        sys.exit(start("--keep-omc" in args, "--keep-claude-md" in args))
    sys.exit(end() if args[0] == "end" else status())
