"""Baixa o modelo oficial do Google; nao inclui modelos da referencia externa."""
from pathlib import Path
from urllib.request import urlopen
import hashlib
import os

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'
SHA256 = '59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a'

def main():
    target = ROOT / 'models/pose_landmarker_lite.task'
    target.parent.mkdir(exist_ok=True)
    if not target.exists():
        with urlopen(URL, timeout=90) as response:
            payload = response.read()
        if len(payload) != 5777746 or hashlib.sha256(payload).hexdigest() != SHA256:
            raise RuntimeError('Tamanho ou hash inesperado do modelo oficial. Verifique a origem antes de prosseguir.')
        temporary = target.with_suffix('.download')
        temporary.write_bytes(payload)
        os.replace(temporary, target)
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual != SHA256:
        raise RuntimeError('O modelo existente difere do modelo oficial verificado.')
    print(f'Modelo: {target.name}; bytes={target.stat().st_size}; SHA256={actual}')

if __name__ == '__main__':
    main()
