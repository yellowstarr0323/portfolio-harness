#!/usr/bin/env bash
# 친구들에게 나눠 줄 하네스 zip을 만든다. 플러그인에 필요한 것 + upload.json만 넣는다.
# 빼는 것: 개발용(tests/, scripts/의 테스트 환경 도구, temp.py), OMC 상태(.omc/), 캐시, 사용자 작업물
# 사용법: scripts/make-zip.sh [출력 zip 경로]   (기본 ~/portfolio-harness-<날짜>.zip)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$HOME/portfolio-harness-$(date +%Y%m%d).zip}"

[ -f "$ROOT/upload.json" ] || echo "주의: upload.json이 없다 — 이 zip은 PDF를 보내지 않는다 (플러그인 루트에 {\"discord_webhook\": \"…\"})"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
DEST="$STAGE/portfolio-harness"
mkdir -p "$DEST"
cp -r "$ROOT/.claude-plugin" "$ROOT/agents" "$ROOT/hooks" "$ROOT/rules" "$ROOT/skills" "$DEST/"
[ -f "$ROOT/upload.json" ] && cp "$ROOT/upload.json" "$DEST/"
find "$DEST" \( -name .omc -o -name __pycache__ \) -prune -exec rm -rf {} +
find "$DEST" -name '*.pyc' -delete

rm -f "$OUT"
(cd "$STAGE" && zip -qr "$OUT" portfolio-harness)
echo "만듦: $OUT"
unzip -l "$OUT" | tail -1
echo "받은 사람: 압축을 풀고  claude --plugin-dir <풀린 폴더>/portfolio-harness  → /portfolio-harness:start"
