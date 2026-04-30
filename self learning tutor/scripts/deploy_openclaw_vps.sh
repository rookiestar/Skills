#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  deploy_openclaw_vps.sh [--remote user@host] [--install-dir PATH] [--data-dir PATH]

Defaults:
  --remote      rookiestar@8.210.29.222
  --install-dir /home/rookiestar/.openclaw/workspace/skills/self-learning-tutor

Branch strategy (file互斥):
  main  = source code + JSON data (wordlist, phrases, curated .json)
  codex = prebuilt dictionary.db only (gitignored on main)

Flow:
  1. scp code+JSON from main branch → server
  2. Build dictionary.db on server (from wordlist + JSON data)
  3. Verify lookup
EOF
}

REMOTE="rookiestar@8.210.29.222"
INSTALL_DIR="/home/rookiestar/.openclaw/workspace/skills/self-learning-tutor"
CODE_BRANCH="main"
LOCAL_DATA_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)      REMOTE="${2:?missing value}"; shift 2 ;;
    --install-dir) INSTALL_DIR="${2:?missing value}"; shift 2 ;;
    --data-dir)    LOCAL_DATA_DIR="${2:?missing value}"; shift 2 ;;
    -h|--help)      usage; exit 0 ;;
    *)              echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GIT_ROOT="$(git -C "${REPO_ROOT}" rev-parse --show-toplevel || echo "${REPO_ROOT}")"

# ── Step 1: 从 main 分支提取代码 + JSON 数据 ──────────────────────────
TEMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "${TEMP_DIR}"; }
trap cleanup EXIT

if [[ -n "${LOCAL_DATA_DIR}" ]]; then
  if [[ ! -d "${LOCAL_DATA_DIR}" ]]; then
    echo "Local data directory not found: ${LOCAL_DATA_DIR}" >&2; exit 1
  fi
  cp -r "${LOCAL_DATA_DIR}" "${TEMP_DIR}/data"
else
  echo "Extracting code + data from branch: ${CODE_BRANCH}"
  git -C "${GIT_ROOT}" archive "${CODE_BRANCH}" \
    'self learning tutor/' ':!data/*.db' ':!data/*.db-*' ':!**/data/dictionary.db*' \
    | tar -x -C "${TEMP_DIR}"
fi

DEPLOY_SRC="${TEMP_DIR}/self learning tutor"
if [[ ! -d "${DEPLOY_SRC}" ]]; then
  DEPLOY_SRC="${TEMP_DIR}"
fi
echo "Deploy source ready: $(ls "${DEPLOY_SRC}")"

# ── Step 2: scp 到服务器 ────────────────────────────────────────────────
echo "Deploying to ${REMOTE}:${INSTALL_DIR} ..."

ssh "${REMOTE}" "mkdir -p '${INSTALL_DIR}' '{'${INSTALL_DIR}/data''}'"

# 代码文件
scp -r \
  "${DEPLOY_SRC}/SKILL.md" \
  "${DEPLOY_SRC}/bin" \
  "${DEPLOY_SRC}/scripts" \
  "${DEPLOY_SRC}/references" \
  "${DEPLOY_SRC}/package.json" \
  "${REMOTE}:${INSTALL_DIR}/"

# 数据文件（JSON/txt，不含 .db）
for f in "${DEPLOY_SRC}/data/"*; do
  name="$(basename "${f}")"
  case "$name" in *.db|*.db-*) continue ;;  # 跳过 .db 文件
  esac
  local_size=$(stat -f%z "${f}")
  remote_size=$(ssh "${REMOTE}" "stat -c%s '${INSTALL_DIR}/data/${name}'" 2>/dev/null || echo "0")
  if [[ "${remote_size}" -eq "${local_size}" ]]; then
    echo "  skip ${name} (${local_size}B up-to-date)"
  else
    echo "  upload ${name} ..."
    scp "${f}" "${REMOTE}:${INSTALL_DIR}/data/"
  fi
done

# ── Step 3: 在服务器上构建 dictionary.db ────────────────────────────────────
echo ""
echo "--- Building dictionary.db on server ---"
ssh "${REMOTE}" "
  cd '${INSTALL_DIR}'
  python3 scripts/migrate_phrases_to_db.py --db data/dictionary.db --phrases data/gaokao_phrases.json 2>&1 || true
  python3 scripts/enrich_cambridge_phrases.py --db data/dictionary.db --phrases data/gaokao_phrases.json 2>&1 || true
  # 如果 db 不存在或为空，从 wordlist 构建（需要网络，较慢）
  if [ ! -s data/dictionary.db ] || [ \$(sqlite3 data/dictionary.db 'SELECT count(*) FROM dictionary;' 2>/dev/null || echo 0) -lt 100 ]; then
    echo '  wordlist build needed (slow, requires internet)...'
    python3 scripts/build_cambridge_dict.py --wordlist data/cambridge_wordlist.txt --db data/dictionary.db 2>&1 || true
  fi
  ls -lh data/dictionary.db
"

# ── Step 4: 验证 ────────────────────────────────────────────────────────
echo ""
echo "--- Verifying en_to_zh lookup ---"
ssh "${REMOTE}" "python3 '${INSTALL_DIR}/scripts/dict_lookup.py' --mode en_to_zh important"

echo ""
echo "--- Verifying zh_to_en lookup ---"
ssh "${REMOTE}" "python3 '${INSTALL_DIR}/scripts/dict_lookup.py' --mode zh_to_en 重要的"

echo ""
echo "--- Verifying phrase lookup ---"
ssh "${REMOTE}" "python3 '${INSTALL_DIR}/scripts/dict_lookup.py' --mode en_to_zh 'sit down'"
ssh "${REMOTE}" "python3 '${INSTALL_DIR}/scripts/dict_lookup.py' --mode en_to_zh 'good morning'"

echo ""
echo "Deployment complete."
