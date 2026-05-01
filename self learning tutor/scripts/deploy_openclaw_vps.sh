#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  deploy_openclaw_vps.sh [--remote user@host] [--active-dir PATH] [--release-root PATH] [--data-dir PATH] [--allow-dirty]

Defaults:
  --remote       rookiestar@8.210.29.222
  --active-dir   /home/rookiestar/.openclaw/workspace/skills/self-learning-tutor
  --release-root /home/rookiestar/.openclaw/workspace/releases/self-learning-tutor

Flow:
  1. Require a clean git tree and archive HEAD into a release bundle
  2. Copy the bundle into a versioned release dir on the VPS
  3. Rebuild dictionary data locally if the cached DB is stale or missing
  4. Smoke test the release directly
  5. Promote the release into the active workspace dir
  6. Remove stale self-learning-tutor.bak.* workspace snapshots
  7. Patch the openclaw-lark inbound handler to run lookup directly
  8. Restart openclaw-gateway.service when it is available
  9. Smoke test the active workspace copy
EOF
}

REMOTE="rookiestar@8.210.29.222"
ACTIVE_DIR="/home/rookiestar/.openclaw/workspace/skills/self-learning-tutor"
RELEASE_ROOT="/home/rookiestar/.openclaw/workspace/releases/self-learning-tutor"
CODE_BRANCH="main"
LOCAL_DATA_DIR=""
ALLOW_DIRTY=false
SERVICE_NAME="openclaw-gateway.service"
REMOTE_ACTIVE_DB="${ACTIVE_DIR}/data/dictionary.db"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)       REMOTE="${2:?missing value}"; shift 2 ;;
    --active-dir)   ACTIVE_DIR="${2:?missing value}"; shift 2 ;;
    --release-root) RELEASE_ROOT="${2:?missing value}"; shift 2 ;;
    --data-dir)     LOCAL_DATA_DIR="${2:?missing value}"; shift 2 ;;
    --allow-dirty)  ALLOW_DIRTY=true; shift 1 ;;
    -h|--help)      usage; exit 0 ;;
    *)              echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GIT_ROOT="$(git -C "${REPO_ROOT}" rev-parse --show-toplevel || echo "${REPO_ROOT}")"

if [[ "${ALLOW_DIRTY}" == false ]]; then
  if ! git -C "${GIT_ROOT}" diff --quiet --ignore-submodules -- || ! git -C "${GIT_ROOT}" diff --cached --quiet --ignore-submodules --; then
    echo "Working tree has local changes. Commit or pass --allow-dirty if you really want to deploy from a dirty tree." >&2
    git -C "${GIT_ROOT}" status --short >&2 || true
    exit 1
  fi
fi

SOURCE_COMMIT="$(git -C "${GIT_ROOT}" rev-parse HEAD)"
SOURCE_SHORT="$(git -C "${GIT_ROOT}" rev-parse --short=12 HEAD)"
RELEASE_ID="${SOURCE_SHORT}-$(date -u +%Y%m%dT%H%M%SZ)"

TEMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TEMP_DIR}"
}
trap cleanup EXIT

if [[ -n "${LOCAL_DATA_DIR}" ]]; then
  if [[ ! -d "${LOCAL_DATA_DIR}" ]]; then
    echo "Local data directory not found: ${LOCAL_DATA_DIR}" >&2
    exit 1
  fi
fi

echo "Building release ${RELEASE_ID} from ${SOURCE_COMMIT}"
git -C "${GIT_ROOT}" archive "${SOURCE_COMMIT}" -- \
  'self learning tutor/' ':!data/*.db' ':!data/*.db-*' ':!**/data/dictionary.db*' \
  | tar -x -C "${TEMP_DIR}"

DEPLOY_SRC="${TEMP_DIR}/self learning tutor"
if [[ ! -d "${DEPLOY_SRC}" ]]; then
  DEPLOY_SRC="${TEMP_DIR}"
fi

DATA_DB_SOURCE="none"

local_db_is_acceptable() {
  python3 - "$1" <<'PY'
import json
import sqlite3
import sys

db_path = sys.argv[1]
required = {"important", "in the future"}

conn = sqlite3.connect(db_path)
try:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(dictionary)")}
    if "definition" in columns or "definitions" not in columns:
        raise SystemExit(1)
    rows = set()
    for word, definitions in conn.execute(
        "SELECT word, definitions FROM dictionary WHERE word IN (?, ?)",
        tuple(required),
    ):
        text = (definitions or "").strip()
        if not text or text == "[]":
            continue
        try:
            parsed = json.loads(text)
        except Exception:
            rows.add(word)
            continue
        if isinstance(parsed, list) and any(str(item).strip() for item in parsed):
            rows.add(word)
except Exception:
    raise SystemExit(1)
finally:
    conn.close()

raise SystemExit(0 if required <= rows else 1)
PY
}

if [[ -n "${LOCAL_DATA_DIR}" ]]; then
  rm -rf "${DEPLOY_SRC}/data"
  cp -R "${LOCAL_DATA_DIR}" "${DEPLOY_SRC}/data"
  DATA_DB_SOURCE="local data override"
else
  LOCAL_DB_CACHE="${REPO_ROOT}/data/dictionary.db"
  if [[ -s "${LOCAL_DB_CACHE}" ]]; then
    if local_db_is_acceptable "${LOCAL_DB_CACHE}"; then
      mkdir -p "${DEPLOY_SRC}/data"
      cp "${LOCAL_DB_CACHE}" "${DEPLOY_SRC}/data/dictionary.db"
      echo "Using cached local dictionary.db: ${LOCAL_DB_CACHE}"
      DATA_DB_SOURCE="local cache"
    else
      mkdir -p "${DEPLOY_SRC}/data"
      cp "${LOCAL_DB_CACHE}" "${DEPLOY_SRC}/data/dictionary.db"
      echo "Local dictionary.db is stale; refreshing it locally in the release bundle"
      DATA_DB_SOURCE="local refresh"
    fi
  fi
fi

if [[ ! -s "${DEPLOY_SRC}/data/dictionary.db" ]]; then
  mkdir -p "${DEPLOY_SRC}/data"
  echo "No local dictionary.db cache; building it locally in the release bundle"
  DATA_DB_SOURCE="local rebuild"
fi

local_has_requests() {
  python3 - <<'PY'
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec('requests') else 1)
PY
}

count_missing_release_phrases() {
  python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path

phrases_path = Path(sys.argv[1])
data = json.loads(phrases_path.read_text(encoding="utf-8"))
missing = sum(1 for item in data.get("phrases", []) if not any(str(d).strip() for d in item.get("definitions", [])))
print(missing)
PY
}

refresh_local_release_data() {
  local release_dir="$1"
  local db_path="${release_dir}/data/dictionary.db"
  local phrases_path="${release_dir}/data/gaokao_phrases.json"
  local missing_count

  if [[ "${DATA_DB_SOURCE}" == "local cache" ]]; then
    return 0
  fi

  missing_count="$(count_missing_release_phrases "${phrases_path}")"

  if [[ "${missing_count}" -gt 0 ]]; then
    if ! local_has_requests; then
      echo "Local Python has no requests module; cannot refresh Cambridge phrases locally" >&2
      exit 1
    fi

    if ! (cd "${release_dir}" && python3 scripts/enrich_cambridge_phrases.py --input data/gaokao_phrases.json --output data/gaokao_phrases.json --workers 1 --delay 2); then
      echo "Local Cambridge enrichment failed" >&2
      exit 1
    fi
  fi

  if ! (cd "${release_dir}" && python3 scripts/migrate_phrases_to_db.py --db data/dictionary.db --phrases data/gaokao_phrases.json); then
    echo "Local phrase migration failed" >&2
    exit 1
  fi

  if local_db_is_acceptable "${db_path}"; then
    if [[ "${DATA_DB_SOURCE}" == "local cache" ]]; then
      DATA_DB_SOURCE="local cache + refresh"
    fi
    return 0
  fi

  echo "Local dictionary.db is still incomplete; building Cambridge core locally"
  if ! local_has_requests; then
    echo "Local Python has no requests module; cannot build Cambridge core locally" >&2
    exit 1
  fi
  if ! (cd "${release_dir}" && python3 scripts/build_cambridge_dict.py --wordlist data/cambridge_wordlist.txt --db data/dictionary.db --workers 1 --delay 1.5); then
    echo "Local Cambridge build failed" >&2
    exit 1
  fi

  if ! (cd "${release_dir}" && python3 scripts/migrate_phrases_to_db.py --db data/dictionary.db --phrases data/gaokao_phrases.json); then
    echo "Local phrase migration after core build failed" >&2
    exit 1
  fi

  if ! local_db_is_acceptable "${db_path}"; then
    echo "Local dictionary.db is still not acceptable after local rebuild" >&2
    exit 1
  fi
}

refresh_local_release_data "${DEPLOY_SRC}"

RELEASE_ID="${RELEASE_ID}" \
SOURCE_COMMIT="${SOURCE_COMMIT}" \
SOURCE_BRANCH="${CODE_BRANCH}" \
ACTIVE_DIR="${ACTIVE_DIR}" \
RELEASE_ROOT="${RELEASE_ROOT}" \
DATA_DB_SOURCE="${DATA_DB_SOURCE}" \
python3 - <<'PY' > "${TEMP_DIR}/release-manifest.json"
import json
import os
from datetime import datetime, timezone

payload = {
    "release_id": os.environ["RELEASE_ID"],
    "source_commit": os.environ["SOURCE_COMMIT"],
    "source_branch": os.environ["SOURCE_BRANCH"],
    "built_at_utc": datetime.now(timezone.utc).isoformat(),
    "active_dir": os.environ["ACTIVE_DIR"],
    "release_root": os.environ["RELEASE_ROOT"],
    "dictionary_db_source": os.environ["DATA_DB_SOURCE"],
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY

REMOTE_RELEASE_DIR="${RELEASE_ROOT}/${RELEASE_ID}"

echo ""
echo "Deploying to ${REMOTE_RELEASE_DIR} ..."
ssh "${REMOTE}" "mkdir -p '${REMOTE_RELEASE_DIR}' '${ACTIVE_DIR}' '${RELEASE_ROOT}'"

scp -r \
  "${DEPLOY_SRC}/SKILL.md" \
  "${DEPLOY_SRC}/bin" \
  "${DEPLOY_SRC}/scripts" \
  "${DEPLOY_SRC}/references" \
  "${DEPLOY_SRC}/package.json" \
  "${REMOTE}:${REMOTE_RELEASE_DIR}/"
scp -r "${DEPLOY_SRC}/data" "${REMOTE}:${REMOTE_RELEASE_DIR}/"
scp "${TEMP_DIR}/release-manifest.json" "${REMOTE}:${REMOTE_RELEASE_DIR}/release-manifest.json"

echo ""
echo "--- dictionary.db ready from ${DATA_DB_SOURCE} ---"

smoke_release() {
  local target_dir="$1"
  ssh "${REMOTE}" "cd '${target_dir}' && python3 - <<'PY'
import subprocess
import sys

lookup_cases = [
    ('en_to_zh', 'setup'),
    ('en_to_zh', 'important'),
    ('en_to_zh', 'in the future'),
    ('en_to_zh', 'zzzznotaword'),
    ('zh_to_en', '期待'),
    ('zh_to_en', '重要的'),
    ('zh_to_en', '不存在的中文词'),
]

for mode, query in lookup_cases:
    output = subprocess.check_output([
        'python3',
        'scripts/dict_lookup.py',
        '--mode', mode,
        '--format', 'text',
        '--db', 'data/dictionary.db',
        query,
    ], text=True)
    proc = subprocess.run([
        'python3',
        'scripts/validate_lookup_output.py',
        '--mode', mode,
    ], input=output, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(output)
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)

print('smoke ok')
PY"
}

echo ""
echo "--- Smoke testing release bundle ---"
smoke_release "${REMOTE_RELEASE_DIR}"

echo ""
echo "--- Updating release-root current symlink ---"
ssh "${REMOTE}" "ln -sfn '${REMOTE_RELEASE_DIR}' '${RELEASE_ROOT}/current'"

echo ""
echo "--- Promoting release to active workspace ---"
ssh "${REMOTE}" "RELEASE_DIR='${REMOTE_RELEASE_DIR}' ACTIVE_DIR='${ACTIVE_DIR}' python3 - <<'PY'
import os
import shutil
from pathlib import Path

release = Path(os.environ['RELEASE_DIR'])
active = Path(os.environ['ACTIVE_DIR'])

managed_files = ['SKILL.md', 'package.json', 'release-manifest.json']
managed_dirs = ['bin', 'scripts', 'references']
managed_data_files = [
    'cambridge_wordlist.txt',
    'gaokao_phrases.json',
    'prototype_wordlist.txt',
    'sample_dictionary.json',
    'zh_en_core_supplement.json',
    'zh_en_hand_curated.json',
    'dictionary.db',
]

active.mkdir(parents=True, exist_ok=True)
(active / '.release-version').write_text(release.name + '\n', encoding='utf-8')

for name in managed_files:
    target = active / name
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)

for name in managed_dirs:
    target = active / name
    if target.exists():
        shutil.rmtree(target)

data_dir = active / 'data'
data_dir.mkdir(parents=True, exist_ok=True)
for name in managed_data_files:
    target = data_dir / name
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)

for name in ['SKILL.md', 'package.json', 'release-manifest.json']:
    src = release / name
    if src.exists():
        shutil.copy2(src, active / name)

(active / '.release-version').write_text(release.name + '\n', encoding='utf-8')

for name in managed_dirs:
    src = release / name
    if src.exists():
        shutil.copytree(src, active / name, dirs_exist_ok=True)

src_data = release / 'data'
if src_data.exists():
    shutil.copytree(src_data, data_dir, dirs_exist_ok=True)

print(f'promoted {release.name} to {active}')
PY"

echo ""
echo "--- Removing stale skill backup snapshots ---"
ssh "${REMOTE}" "find '$(dirname "${ACTIVE_DIR}")' -maxdepth 1 -type d -name 'self-learning-tutor.bak.*' -exec rm -rf {} +"

patch_remote_lark_handler() {
  echo ""
  echo "--- Patching openclaw-lark inbound handler ---"
  ssh "${REMOTE}" "python3 - <<'PY'
from pathlib import Path

path = Path.home() / '.openclaw' / 'extensions' / 'openclaw-lark' / 'src' / 'messaging' / 'inbound' / 'handler.js'
text = path.read_text(encoding='utf-8')
if 'LOOKUP_WORKSPACE_DIR' in text and 'runDirectLookup' in text:
    print(f'already patched: {path}')
    raise SystemExit(0)

old_import = 'const parse_1 = require(\"./parse.js\");\\n'
new_import = (
    'const parse_1 = require(\"./parse.js\");\\n'
    'const child_process_1 = require(\"child_process\");\\n'
    'const os_1 = require(\"os\");\\n'
    'const path_1 = require(\"path\");\\n'
    'const util_1 = require(\"util\");\\n'
    'const execFileAsync = (0, util_1.promisify)(child_process_1.execFile);\\n'
)
if old_import not in text:
    raise SystemExit('import anchor not found')
text = text.replace(old_import, new_import, 1)

old_block = '''function buildLookupCommand(text) {
    return LOOKUP_COMMAND_PREFIX + " " + shellQuote(normalizeLookupText(text));
}
'''
new_block = '''function buildLookupCommand(text) {
    return LOOKUP_COMMAND_PREFIX + " " + shellQuote(normalizeLookupText(text));
}

const LOOKUP_WORKSPACE_DIR = (0, path_1.join)((0, os_1.homedir)(), '.openclaw', 'workspace', 'skills', 'self-learning-tutor');
const LOOKUP_SCRIPT_PATH = (0, path_1.join)(LOOKUP_WORKSPACE_DIR, 'scripts', 'dict_lookup.py');
const LOOKUP_DB_PATH = (0, path_1.join)(LOOKUP_WORKSPACE_DIR, 'data', 'dictionary.db');
const LOOKUP_PYTHON = process.env.SELF_LEARNING_TUTOR_PYTHON || 'python3';

function extractLookupQuery(text) {
    const normalized = normalizeLookupText(text);
    const strippedEn = stripLookupCuesEn(normalized);
    if (strippedEn !== normalized && isEnglishTerm(strippedEn)) {
        return strippedEn;
    }
    const strippedZh = stripLookupCuesZh(normalized);
    if (strippedZh !== normalized && strippedZh) {
        return strippedZh;
    }
    if (isEnglishTerm(normalized)) {
        return normalized;
    }
    if (ZH_LOOKUP_CUES.some((cue) => normalized.includes(cue))) {
        const cleaned = stripLookupCuesZh(normalized);
        if (cleaned) {
            return cleaned;
        }
    }
    return null;
}

async function runDirectLookup(query) {
    try {
        const { stdout, stderr } = await execFileAsync(LOOKUP_PYTHON, [LOOKUP_SCRIPT_PATH, '--format', 'text', '--style', 'strict', '--db', LOOKUP_DB_PATH, query], {
            cwd: LOOKUP_WORKSPACE_DIR,
            maxBuffer: 1024 * 1024,
        });
        if (stderr) {
            logger.info('lookup stderr: ' + String(stderr).trim());
        }
        return stdout;
    }
    catch (err) {
        const stdout = err?.stdout ?? '';
        const stderr = err?.stderr ?? '';
        if (stdout) {
            return stdout;
        }
        logger.error('lookup failed for "' + query + '": ' + String(err) + (stderr ? ' stderr=' + String(stderr).trim() : ''));
        return '词典查询暂时失败了，你稍后再试一下。';
    }
}
'''
if old_block not in text:
    raise SystemExit('lookup helper anchor not found')
text = text.replace(old_block, new_block, 1)

old_router = '''    const routerResult = classifyLookupMessage(ctx.content ?? '', undefined);
    if (routerResult.replyText && !routerResult.command) {
        await sendRouterReply({ cfg: accountScopedCfg, chatId: ctx.chatId, accountId: account.accountId, messageId: ctx.messageId, replyInThread: Boolean(ctx.threadId) }, params.replyToMessageId, routerResult.replyText);
        return;
    }
    if (routerResult.command) {
        ctx = { ...ctx, content: routerResult.command };
    }
'''
new_router = '''    const routerResult = classifyLookupMessage(ctx.content ?? '', undefined);
    if (routerResult.replyText && !routerResult.command) {
        await sendRouterReply({ cfg: accountScopedCfg, chatId: ctx.chatId, accountId: account.accountId, messageId: ctx.messageId, replyInThread: Boolean(ctx.threadId) }, params.replyToMessageId, routerResult.replyText);
        return;
    }
    if (routerResult.command) {
        const lookupQuery = extractLookupQuery(ctx.content ?? '');
        if (!lookupQuery) {
            logger.error('lookup routing failed: could not extract query from "' + (ctx.content ?? '') + '"');
            await sendRouterReply({ cfg: accountScopedCfg, chatId: ctx.chatId, accountId: account.accountId, messageId: ctx.messageId, replyInThread: Boolean(ctx.threadId) }, params.replyToMessageId, '词典查询暂时失败了，你稍后再试一下。');
            return;
        }
        const lookupText = await runDirectLookup(lookupQuery);
        await sendRouterReply({ cfg: accountScopedCfg, chatId: ctx.chatId, accountId: account.accountId, messageId: ctx.messageId, replyInThread: Boolean(ctx.threadId) }, params.replyToMessageId, lookupText);
        return;
    }
'''
if old_router not in text:
    raise SystemExit('router block anchor not found')
text = text.replace(old_router, new_router, 1)

path.write_text(text, encoding='utf-8')
print(f'patched {path}')
PY"
}

patch_remote_lark_handler

restart_service_if_present() {
  if ssh "${REMOTE}" "systemctl --user show -p LoadState --value '${SERVICE_NAME}' 2>/dev/null | grep -qx loaded"; then
    echo ""
    echo "--- Restarting ${SERVICE_NAME} ---"
    ssh "${REMOTE}" "systemctl --user restart '${SERVICE_NAME}'"
    ssh "${REMOTE}" "systemctl --user is-active --quiet '${SERVICE_NAME}'"
  else
    echo ""
    echo "--- ${SERVICE_NAME} not found; skipping restart ---"
  fi
}

restart_service_if_present

echo ""
echo "--- Smoke testing active workspace copy ---"
smoke_release "${ACTIVE_DIR}"

echo ""
echo "Deployment complete."
