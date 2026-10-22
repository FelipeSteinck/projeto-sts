"""Percorre todos os quadros, sem reprodução em tempo real ou saltos por rede."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from src.aplicacao import extrair_metricas_corpo
from src.atributos import SCHEMA, raw_columns
from .dados import digest


def extract_video(video, output, session, participant, model, mirrored=False, data_kind='real'):
    video,model,output=Path(video),Path(model),Path(output)
    if not video.is_file() or not model.is_file():
        raise ValueError('Vídeo ou modelo MediaPipe não encontrado.')
    if data_kind not in ('real','sintetico'):
        raise ValueError('Tipo de dados inválido.')
    output.parent.mkdir(parents=True,exist_ok=True)
    capture=cv2.VideoCapture(str(video))
    fps=capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or not 0<fps<=240:
        capture.release(); raise ValueError('Vídeo sem taxa nominal utilizável.')
    options=vision.PoseLandmarkerOptions(base_options=python.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.VIDEO,num_poses=1,min_pose_detection_confidence=.5,
        min_pose_presence_confidence=.5,min_tracking_confidence=.5)
    index=0
    try:
        with vision.PoseLandmarker.create_from_options(options) as landmarker, output.open('w',encoding='utf-8-sig',newline='') as handle:
            writer=None
            while True:
                ok,image=capture.read()
                if not ok: break
                if mirrored: image=cv2.flip(image,1)
                h,w=image.shape[:2]
                milliseconds=round(index*1000/fps)
                result=landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)),milliseconds)
                raw=None
                if result.pose_landmarks:
                    try: raw,_,_=extrair_metricas_corpo(result.pose_landmarks[0],w,h,.60)
                    except ValueError: pass
                row=dict(schema_atributos=SCHEMA,tipo_dados=data_kind,sessao=session,participante=participant,
                    quadro=index+1,tempo_fonte_s=index/fps,espelhado=mirrored,**raw_columns(raw))
                if writer is None:
                    writer=csv.DictWriter(handle,fieldnames=list(row),delimiter=';'); writer.writeheader()
                writer.writerow(row); index+=1
    finally:
        capture.release()
    if not index: raise ValueError('Nenhum quadro decodificado.')
    metadata=dict(video_sha256=digest(video),model_sha256=digest(model),frames=index,
        fps_nominal=fps,tempo='indice/fps_nominal',tipo_dados=data_kind,espelhado=mirrored,
        aviso='Usar vídeo com taxa constante. Para VFR, converter com procedimento documentado antes da extração.')
    output.with_suffix('.meta.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    return metadata
