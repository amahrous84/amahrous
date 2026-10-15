#!/bin/sh
# Launches the Qwen Max MCP server, installing and building it on first run.
# npm output goes to stderr so it never corrupts the MCP stdio stream.
set -e
cd "$(dirname "$0")"
if [ ! -d node_modules ]; then npm ci --ignore-scripts >&2; fi
if [ ! -f build/index.js ] || [ src/index.ts -nt build/index.js ]; then npm run build >&2; fi
exec node build/index.js
