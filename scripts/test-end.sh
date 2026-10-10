#!/usr/bin/env bash
# 하네스 E2E 테스트 끝: test-start가 바꾼 설정만 원래대로 되돌린다.
set -euo pipefail
exec python3 "$(dirname "$(readlink -f "$0")")/test_env.py" end "$@"
