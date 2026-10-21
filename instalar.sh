#!/usr/bin/env bash
# Prepara el editor: dependencias de Python y modelos de transcripción.
# Se puede ejecutar las veces que haga falta: lo que ya está, se salta.
set -euo pipefail
cd "$(dirname "$0")"

command -v ffmpeg >/dev/null || { echo "Falta ffmpeg (sudo apt install ffmpeg / brew install ffmpeg)"; exit 1; }

python3 -c "import sherpa_onnx, numpy, PIL" 2>/dev/null || \
  python3 -m pip install -q --break-system-packages sherpa-onnx numpy pillow 2>/dev/null || \
  python3 -m pip install -q sherpa-onnx numpy pillow

BASE=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
mkdir -p modelos
if [ ! -f modelos/parakeet/encoder.int8.onnx ]; then
  echo "Descargando modelo de transcripción (640 MB)…"
  curl -sSL --retry 3 -o modelos/p.tar.bz2 "$BASE/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2"
  tar xjf modelos/p.tar.bz2 -C modelos
  rm -rf modelos/parakeet
  mv modelos/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8 modelos/parakeet
  rm -f modelos/p.tar.bz2 && rm -rf modelos/parakeet/test_wavs
fi
[ -f modelos/silero_vad.onnx ] || curl -sSL --retry 3 -o modelos/silero_vad.onnx "$BASE/silero_vad.onnx"
echo "Editor listo."
