#!/usr/bin/env bash
# 按 GitNexus 官方 README 构建 gitnexus-web，产出到 public/gitnexus-app（本地后端模式）
# 见 https://github.com/abhigyanpatwari/GitNexus#web-ui-browser-based

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PUBLIC_APP="$REPO_DIR/public/gitnexus-app"
BUILD_DIR="${BUILD_DIR:-$REPO_DIR/.gitnexus-web-build}"

echo "Building GitNexus web (Local Backend Mode) -> $PUBLIC_APP"

if [ -d "$BUILD_DIR" ]; then
  echo "Using existing clone at $BUILD_DIR"
  cd "$BUILD_DIR"
  git fetch origin main && git reset --hard origin/main || true
else
  git clone --depth 1 https://github.com/abhigyanpatwari/GitNexus.git "$BUILD_DIR"
  cd "$BUILD_DIR"
fi

cd gitnexus-web
npm ci
npx vite build --base /gitnexus-app/

mkdir -p "$PUBLIC_APP"
rm -rf "${PUBLIC_APP:?}"/*
cp -r dist/* "$PUBLIC_APP/"
echo "Done. GitNexus web app is in $PUBLIC_APP"
