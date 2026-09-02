#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_HOST="${CHAN_REMOTE_HOST:?Set CHAN_REMOTE_HOST to the verified Raspberry Pi SSH address}"
REMOTE_DIR="${CHAN_REMOTE_DIR:-/home/tracelab/chan}"

echo "Deploying CHAN to ${REMOTE_HOST}:${REMOTE_DIR}"
rsync -av \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  --exclude '.env*' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'logs/' \
  "${SCRIPT_DIR}/" "${REMOTE_HOST}:${REMOTE_DIR}/"

echo "Deployment complete."
