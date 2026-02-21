#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ] || [ "${2:-}" = "" ]; then
  echo "Usage: $0 <MUSICGEN_API_URL> <MUSICGEN_API_KEY>"
  exit 1
fi

MUSICGEN_URL="$1"
MUSICGEN_KEY="$2"

for env in production preview development; do
  vercel env rm MUSICGEN_API_URL "$env" --yes --cwd backend >/dev/null 2>&1 || true
  printf '%s' "$MUSICGEN_URL" | vercel env add MUSICGEN_API_URL "$env" --cwd backend >/dev/null

  vercel env rm MUSICGEN_API_KEY "$env" --yes --cwd backend >/dev/null 2>&1 || true
  printf '%s' "$MUSICGEN_KEY" | vercel env add MUSICGEN_API_KEY "$env" --cwd backend >/dev/null

  echo "Updated MUSICGEN env for $env"
done

vercel deploy --prod --yes -A vercel.json --cwd backend
echo "Backend redeployed with new MusicGen endpoint."
