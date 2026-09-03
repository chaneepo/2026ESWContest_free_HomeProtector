#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[CARE-PACK] 필요한 명령을 찾을 수 없습니다: $1" >&2
    exit 1
  fi
}

require_command node
require_command npm
require_command python3

node -e '
const [major, minor] = process.versions.node.split(".").map(Number);
if (major < 22 || (major === 22 && minor < 13)) {
  console.error(`[CARE-PACK] Node.js 22.13 이상이 필요합니다. 현재: ${process.version}`);
  process.exit(1);
}
'

echo "[CARE-PACK] 1/3 Node.js 패키지를 설치합니다."
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

echo "[CARE-PACK] 2/3 Python 가상환경을 준비합니다."
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

echo "[CARE-PACK] 3/3 Python 개발 패키지를 설치합니다."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements/requirements-dev.txt

echo
echo "[CARE-PACK] 환경 설정이 완료되었습니다."
echo "개발 실행: ./scripts/dev.sh"
echo "Python 활성화: source .venv/bin/activate"

