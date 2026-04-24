#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  deploy_openclaw_vps.sh [--remote user@host] [--workspace PATH] [--install-dir PATH] [--data-dir PATH] [--data-branch BRANCH]

Defaults:
  --remote      rookiestar@34.70.69.58
  --workspace   /home/rookiestar/.openclaw/workspace/agent-xiaodaixing/skills/self-learning-tutor
  --install-dir /home/rookiestar/.openclaw/skills/self-learning-tutor
  --data-branch codex/local-dictionary-branch
EOF
}

REMOTE="rookiestar@34.70.69.58"
REMOTE_WORKSPACE="/home/rookiestar/.openclaw/workspace/agent-xiaodaixing/skills/self-learning-tutor"
REMOTE_INSTALL_DIR="/home/rookiestar/.openclaw/skills/self-learning-tutor"
DATA_BRANCH="codex/local-dictionary-branch"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOCAL_DATA_DIR=""
TEMP_DATA_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE="${2:?missing value for --remote}"
      shift 2
      ;;
    --workspace)
      REMOTE_WORKSPACE="${2:?missing value for --workspace}"
      shift 2
      ;;
    --install-dir)
      REMOTE_INSTALL_DIR="${2:?missing value for --install-dir}"
      shift 2
      ;;
    --data-dir)
      LOCAL_DATA_DIR="${2:?missing value for --data-dir}"
      shift 2
      ;;
    --data-branch)
      DATA_BRANCH="${2:?missing value for --data-branch}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

cleanup() {
  if [[ -n "${TEMP_DATA_DIR}" && -d "${TEMP_DATA_DIR}" ]]; then
    rm -rf "${TEMP_DATA_DIR}"
  fi
}
trap cleanup EXIT

if [[ -z "${LOCAL_DATA_DIR}" ]]; then
  TEMP_DATA_DIR="$(mktemp -d)"
  git -C "${REPO_ROOT}" archive "${DATA_BRANCH}" 'self learning tutor/data' | tar -x -C "${TEMP_DATA_DIR}"
  LOCAL_DATA_DIR="${TEMP_DATA_DIR}/self learning tutor/data"
fi

if [[ ! -d "${LOCAL_DATA_DIR}" ]]; then
  echo "Local data directory not found: ${LOCAL_DATA_DIR}" >&2
  echo "Use --data-dir or ensure ${DATA_BRANCH} contains self learning tutor/data." >&2
  exit 1
fi

ssh "${REMOTE}" "set -euo pipefail; mkdir -p '${REMOTE_WORKSPACE}/data' '${REMOTE_INSTALL_DIR}/data' && cd '${REMOTE_WORKSPACE}' && git pull origin main"
rsync -av --delete "${LOCAL_DATA_DIR}/" "${REMOTE}:${REMOTE_WORKSPACE}/data/"
ssh "${REMOTE}" "set -euo pipefail; cd '${REMOTE_WORKSPACE}' && node bin/self-learning-tutor.js install && python3 '${REMOTE_INSTALL_DIR}/scripts/dict_lookup.py' --mode en_to_zh important && python3 '${REMOTE_INSTALL_DIR}/scripts/dict_lookup.py' --mode zh_to_en 重要的"
