#!/bin/bash
# 发布脚本：将 skill 源码复制到 publish/ 目录并发布到 npm

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLISH_DIR="$SCRIPT_DIR/publish"

echo "📦 Preparing npm package..."

# 清理旧的源码文件（保留 npm 配置文件）
cd "$PUBLISH_DIR"
rm -rf scripts templates references examples docs SKILL.md CLAUDE.md README.md README_EN.md requirements.txt 2>/dev/null || true

# 复制最新的源码文件
echo "📋 Copying source files..."
cp -r "$SCRIPT_DIR/scripts" .
cp -r "$SCRIPT_DIR/templates" .
cp -r "$SCRIPT_DIR/references" .
cp -r "$SCRIPT_DIR/examples" .
cp -r "$SCRIPT_DIR/docs" .
cp "$SCRIPT_DIR/SKILL.md" .
cp "$SCRIPT_DIR/CLAUDE.md" .
cp "$SCRIPT_DIR/README.md" .
cp "$SCRIPT_DIR/README_EN.md" .
cp "$SCRIPT_DIR/requirements.txt" .

echo "📦 Publishing to npm..."
npm publish "$@"

echo "✅ Done!"
