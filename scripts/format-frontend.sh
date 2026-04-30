#!/usr/bin/env bash
set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

echo "Formatting frontend files..."
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

npm run format
echo "Frontend formatting complete."
