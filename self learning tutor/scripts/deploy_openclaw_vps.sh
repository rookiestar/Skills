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
  main  = source code + JSON data + deploy script + tests
  codex = prebuilt dictionary.db + test data

Flow:
  1. scp code+JSON from main branch → server
  2. Try scp prebuilt .db from codex (skip if size matches remote)
  3. Fallback: build dictionary.db on server (slow, needs internet)
  4. Verify lookup
EOF
}

REMOTE="rookiestar@8.210.29.222"
INSTALL_DIR="/home/rookiestar/.openclaw/workspace/skills/self-learning-tutor"
CODE_BRANCH="main"
CODEX_BRANCH="codex/local-dictionary-branch"
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

# ── Step 2: scp 到服务器（代码 + JSON 数据）────────────────────────────
echo ""
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

# ── Step 3: 从 codex 分支获取预构建 dictionary.db ──────────────────────
DB_UPLOADED=false
CODEX_DB="${TEMP_DIR}/dictionary.db"

echo ""
echo "--- Checking codex branch for prebuilt dictionary.db ---"
if git -C "${GIT_ROOT}" rev-parse --verify "${CODEX_BRANCH}" >/dev/null 2>&1; then
  # 尝试从 codex 提取 .db 文件
  if git -C "${GIT_ROOT}" archive "${CODEX_BRANCH}" \
    'self learning tutor/data/*.db' ':!**/*.db-*' 2>/dev/null | tar -x -C "${TEMP_DIR}" 2>/dev/null; then
    # archive 输出带目录前缀，找实际的 .db
    FOUND_DB=$(find "${TEMP_DIR}" -maxdepth 2 -name 'dictionary.db' -type f 2>/dev/null | head -1 || true)
    if [[ -n "${FOUND_DB}" && -s "${FOUND_DB}" ]]; then
      cp "${FOUND_DB}" "${CODEX_DB}"
      local_db_size=$(stat -f%z "${CODEX_DB}")
      remote_db_size=$(ssh "${REMOTE}" "stat -c%s '${INSTALL_DIR}/data/dictionary.db'" 2>/dev/null || echo "0")

      if [[ "${remote_db_size}" -eq "${local_db_size}" ]] && [[ "${remote_db_size}" -gt 0 ]]; then
        echo "  skip dictionary.db (${local_db_size}B up-to-date on server)"
        DB_UPLOADED=true   # 远端已有相同版本，视为已就绪
      else
        echo "  uploading dictionary.db (${local_db_size}B, remote was ${remote_db_size}B) ..."
        scp "${CODEX_DB}" "${REMOTE}:${INSTALL_DIR}/data/dictionary.db"
        DB_UPLOADED=true
      fi
    else
      echo "  no dictionary.db found in codex branch"
    fi
  else
    echo "  codex branch has no .db files (or archive failed)"
  fi
else
  echo "  codex branch '${CODEX_BRANCH}' not found"
fi

# ─ Step 4: 兜底 — 在服务器上构建 dictionary.db ────────────────────────
if [[ "${DB_UPLOADED}" == false ]]; then
  echo ""
  echo "--- No prebuilt .db available, building on server (slow) ---"
  ssh "${REMOTE}" "
    cd '${INSTALL_DIR}'
    python3 scripts/migrate_phrases_to_db.py --db data/dictionary.db --phrases data/gaokao_phrases.json 2>&1 || true
    python3 scripts/enrich_cambridge_phrases.py --db data/dictionary.db --phrases data/gaokao_phrases.json 2>&1 || true
    if [ ! -s data/dictionary.db ] || [ \$(sqlite3 data/dictionary.db 'SELECT count(*) FROM dictionary;' 2>/dev/null || echo 0) -lt 100 ]; then
      echo '  wordlist build needed (requires internet)...'
      python3 scripts/build_cambridge_dict.py --wordlist data/cambridge_wordlist.txt --db data/dictionary.db 2>&1 || true
    fi
    ls -lh data/dictionary.db
  "
else
  echo ""
  echo "--- dictionary.db ready (from codex branch) ---"
  ssh "${REMOTE}" "ls -lh '${INSTALL_DIR}/data/dictionary.db'"
fi

# ── Step 5: 验证 ────────────────────────────────────────────────────────
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
