#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  deploy_openclaw_vps.sh [--remote user@host] [--install-dir PATH] [--data-dir PATH] [--data-branch BRANCH]

Defaults:
  --remote      rookiestar@34.70.69.58
  --install-dir /home/rookiestar/.openclaw/skills/self-learning-tutor
  --data-branch codex/local-dictionary-branch

Deploys code + data to a single target directory on VPS via scp, then verifies dict lookup.
EOF
}

REMOTE="rookiestar@34.70.69.58"
INSTALL_DIR="/home/rookiestar/.openclaw/skills/self-learning-tutor"
DATA_BRANCH="codex/local-dictionary-branch"
LOCAL_DATA_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE="${2:?missing value for --remote}"
      shift 2
      ;;
    --install-dir)
      INSTALL_DIR="${2:?missing value for --install-dir}"
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
  git -C "${GIT_ROOT}" archive "${DATA_BRANCH}" -- 'data/*' \
    | tar -x -C "${TEMP_DIR}"
fi

DATA_SRC="${TEMP_DIR}/data"
if [[ ! -d "${DATA_SRC}" ]]; then
  echo "Data directory not found after extraction." >&2
  exit 1
fi

echo "Data ready: $(ls "${DATA_SRC}")"

# Step 2: scp 代码 + 数据到 VPS（单一目标目录）
echo "Deploying to ${REMOTE}:${INSTALL_DIR} ..."

ssh "${REMOTE}" "mkdir -p '${INSTALL_DIR}'"

# 传代码文件
scp -r \
  "${REPO_ROOT}/SKILL.md" \
  "${REPO_ROOT}/bin" \
  "${REPO_ROOT}/scripts" \
  "${REPO_ROOT}/references" \
  "${REPO_ROOT}/package.json" \
  "${REMOTE}:${INSTALL_DIR}/"

# 传数据（跳过已存在且大小一致的文件）
ssh "${REMOTE}" "mkdir -p '${INSTALL_DIR}/data'"
for f in "${DATA_SRC}"/*; do
  name="$(basename "${f}")"
  local_size=$(stat -f%z "${f}")
  remote_size=$(ssh "${REMOTE}" "stat -c%s '${INSTALL_DIR}/data/${name}'" 2>/dev/null || echo "0")
  if [[ "${remote_size}" -eq "${local_size}" ]]; then
    echo "  skip ${name} (already up to date, ${local_size} bytes)"
  else
    echo "  uploading ${name} ..."
    scp "${f}" "${REMOTE}:${INSTALL_DIR}/data/"
  fi
done

echo "Deployment complete."

# Step 3: 验证字典查询
echo ""
echo "--- Verifying en_to_zh lookup ---"
ssh "${REMOTE}" "python3 '${INSTALL_DIR}/scripts/dict_lookup.py' --mode en_to_zh important"

echo ""
echo "--- Verifying zh_to_en lookup ---"
ssh "${REMOTE}" "python3 '${INSTALL_DIR}/scripts/dict_lookup.py' --mode zh_to_en 重要的"

echo ""
echo "All done."
