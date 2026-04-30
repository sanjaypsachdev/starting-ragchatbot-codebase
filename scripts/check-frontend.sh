#!/usr/bin/env bash
set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

echo "Running frontend quality checks..."
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

echo "Checking formatting with Prettier..."
npm run format:check

echo "Linting JavaScript with ESLint..."
npm run lint

echo "All frontend quality checks passed."
