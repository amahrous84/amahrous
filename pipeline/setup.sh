#!/usr/bin/env bash
# One-time setup for make_short.py in a fresh container.
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -q kokoro-onnx soundfile pillow numpy
mkdir -p .kokoro
base=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s ".kokoro/$f" ] || curl -sSfL -o ".kokoro/$f" "$base/$f"
done
command -v ffmpeg >/dev/null || { echo "ffmpeg is missing"; exit 1; }
echo "ready"
