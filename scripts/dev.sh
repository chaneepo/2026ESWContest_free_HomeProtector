#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if [[ ! -x .venv/bin/python || ! -d frontend/node_modules ]]; then
  echo "[CARE-PACK] 개발 환경이 준비되지 않았습니다." >&2
  echo "먼저 ./scripts/setup.sh 를 실행하세요." >&2
  exit 1
fi

# 향후 FastAPI/비전 프로세스도 같은 Python 환경을 사용한다.
source .venv/bin/activate

echo "[CARE-PACK] Python: $(python --version 2>&1)"
echo "[CARE-PACK] Node.js: $(node --version)"
echo "[CARE-PACK] 프론트엔드 개발 서버를 시작합니다."

exec npm --prefix frontend run dev -- "$@"

