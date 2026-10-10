#!/usr/bin/env bash
# 하네스 E2E 테스트 시작: 위키 훅·OMC·전역 CLAUDE.md를 백업한 뒤 잠시 끈다.
# 옵션: --keep-omc, --keep-claude-md  (자세한 내용: scripts/test_env.py)
set -euo pipefail
exec python3 "$(dirname "$(readlink -f "$0")")/test_env.py" start "$@"
