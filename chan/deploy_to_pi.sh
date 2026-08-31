#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_HOST="${CHAN_REMOTE_HOST:-tracelab@192.168.0.74}"
REMOTE_DIR="${CHAN_REMOTE_DIR:-/home/tracelab/chan}"

echo "Deploying CHAN to ${REMOTE_HOST}:${REMOTE_DIR}"
rsync -av \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'logs/' \
  "${SCRIPT_DIR}/" "${REMOTE_HOST}:${REMOTE_DIR}/"

echo "Deployment complete."
