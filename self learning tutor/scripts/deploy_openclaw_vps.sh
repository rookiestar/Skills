#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  deploy_openclaw_vps.sh [--remote user@host] [--workspace-dir PATH] [--data-dir PATH] [--data-branch BRANCH]

Defaults:
  --remote      rookiestar@34.70.69.58
  --workspace-dir /home/rookiestar/.openclaw/workspace/agent-xiaodaixing/skills/self-learning-tutor
  --data-branch codex/local-dictionary-branch

Deploys code + prebuilt data to the active workspace copy on VPS, then verifies dict lookup.
EOF
}

REMOTE="rookiestar@34.70.69.58"
WORKSPACE_DIR="/home/rookiestar/.openclaw/workspace/agent-xiaodaixing/skills/self-learning-tutor"
DATA_BRANCH="codex/local-dictionary-branch"
LOCAL_DATA_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE="${2:?missing value for --remote}"
      shift 2
      ;;
    --workspace-dir)
      WORKSPACE_DIR="${2:?missing value for --workspace-dir}"
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GIT_ROOT="$(git -C "${REPO_ROOT}" rev-parse --show-toplevel || echo "${REPO_ROOT}")"

# Step 1: 准备数据（从 git 分支提取或用本地目录）
TEMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "${TEMP_DIR}"; }
trap cleanup EXIT

if [[ -n "${LOCAL_DATA_DIR}" ]]; then
  if [[ ! -d "${LOCAL_DATA_DIR}" ]]; then
    echo "Local data directory not found: ${LOCAL_DATA_DIR}" >&2
    exit 1
  fi
  cp -r "${LOCAL_DATA_DIR}" "${TEMP_DIR}/data"
else
  echo "Extracting data from branch: ${DATA_BRANCH}"
  git -C "${GIT_ROOT}" archive "${DATA_BRANCH}" 'self learning tutor/data' \
    | tar -x -C "${TEMP_DIR}"
fi

DATA_SRC="${TEMP_DIR}/self learning tutor/data"
if [[ ! -d "${DATA_SRC}" ]]; then
  DATA_SRC="${TEMP_DIR}/data"
fi
if [[ ! -d "${DATA_SRC}" ]]; then
  echo "Data directory not found after extraction." >&2
  exit 1
fi

echo "Data ready: $(ls "${DATA_SRC}")"

deploy_to_dir() {
  local target_dir="$1"
  echo "Deploying to ${REMOTE}:${target_dir} ..."

  ssh "${REMOTE}" "mkdir -p '${target_dir}'"

  scp -r \
    "${REPO_ROOT}/SKILL.md" \
    "${REPO_ROOT}/bin" \
    "${REPO_ROOT}/scripts" \
    "${REPO_ROOT}/references" \
    "${REPO_ROOT}/package.json" \
    "${REMOTE}:${target_dir}/"

  ssh "${REMOTE}" "mkdir -p '${target_dir}/data'"
  for f in "${DATA_SRC}"/*; do
    name="$(basename "${f}")"
    # dictionary.db is binary — size comparison is unreliable, always upload
    if [[ "${name}" == "dictionary.db" ]]; then
      echo "  force upload ${name} ..."
      scp "${f}" "${REMOTE}:${target_dir}/data/"
    else
      local_size=$(stat -f%z "${f}")
      remote_size=$(ssh "${REMOTE}" "stat -c%s '${target_dir}/data/${name}'" 2>/dev/null || echo "0")
      if [[ "${remote_size}" -eq "${local_size}" ]]; then
        echo "  skip ${name} (already up to date, ${local_size} bytes)"
      else
        echo "  uploading ${name} ..."
        scp "${f}" "${REMOTE}:${target_dir}/data/"
      fi
    fi
  done

  ssh "${REMOTE}" "grep -n 'Default to the local dictionary data' '${target_dir}/SKILL.md' >/dev/null"
}

# Step 2: scp 代码 + 数据到 VPS（单一工作区目录）
deploy_to_dir "${WORKSPACE_DIR}"

# Step 3: 清除旧 session，确保新 SKILL.md / 脚本立即生效
echo ""
echo "--- Clearing xiaodaixing sessions ---"
SESSIONS_DIR="/home/rookiestar/.openclaw/agents/xiaodaixing/sessions"
ssh "${REMOTE}" "rm -rf '${SESSIONS_DIR}' && echo 'sessions cleared'"

# Step 4: 验证字典查询
echo ""
echo "--- Verifying en_to_zh lookup ---"
ssh "${REMOTE}" "python3 '${WORKSPACE_DIR}/scripts/dict_lookup.py' --mode en_to_zh important"

echo ""
echo "--- Verifying zh_to_en lookup ---"
ssh "${REMOTE}" "python3 '${WORKSPACE_DIR}/scripts/dict_lookup.py' --mode zh_to_en 重要的"

echo ""
echo "--- Attempting OpenClaw reload ---"
ssh "${REMOTE}" "bash -lc '
  if command -v openclaw >/dev/null 2>&1; then
    openclaw gateway restart
    exit 0
  fi
  if systemctl list-unit-files 2>/dev/null | grep -q \"^openclaw-gateway.service\"; then
    sudo systemctl restart openclaw-gateway
    exit 0
  fi
  echo \"No known OpenClaw restart command found; restart the service manually.\" >&2
'"

echo ""
echo "All done."
echo "Deployment complete."
