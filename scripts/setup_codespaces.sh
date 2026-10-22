#!/usr/bin/env bash
set -euo pipefail
if ! python -c "import ctypes; ctypes.CDLL('libGL.so.1'); ctypes.CDLL('libglib-2.0.so.0')" 2>/dev/null; then
  # Usa o repositorio Debian da imagem; repositorios opcionais de Yarn nao sao necessarios.
  apt_sources=()
  if [ -f /etc/apt/sources.list.d/debian.sources ]; then
    apt_sources=(-o Dir::Etc::sourceparts=- -o Dir::Etc::sourcelist=sources.list.d/debian.sources)
  fi
  sudo apt-get "${apt_sources[@]}" update -qq
  sudo apt-get "${apt_sources[@]}" install -y --no-install-recommends libgl1 libglib2.0-0
fi
python -m pip install -r requirements.txt
python scripts/download_model.py
python -m pytest -q
