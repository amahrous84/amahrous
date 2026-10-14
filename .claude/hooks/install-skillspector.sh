#!/bin/bash
# Installs the SkillSpector CLI in cloud sessions so the skill-inspector skill can run scans.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if command -v skillspector >/dev/null 2>&1; then
  exit 0
fi

uv tool install --python 3.13 "git+https://github.com/NVIDIA/skillspector.git@v2.12.0" >/dev/null 2>&1

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"$(uv tool dir --bin):\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi
