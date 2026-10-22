"""Adaptador web do prototipo STS. Video fica em memoria durante a inferencia."""
from __future__ import annotations

import asyncio
import csv
import io
import math
import threading
import time
import uuid
from pathlib import Path
from dataclasses import asdict

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.nucleo import Calibracao, FiltroPosturaEstavel, Postura, RastreadorRepeticoes, SuavizadorMetricas, finalizar_calibracao
from src.aplicacao import extrair_metricas_corpo

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'models/pose_landmarker_lite.task'
app = FastAPI(title='Monitor STS', docs_url=None, redoc_url=None)
app.mount('/static', StaticFiles(directory=ROOT / 'web'), name='static')
SESSIONS: dict[str, Session] = {}
SESSIONS_LOCK = threading.Lock()


class SessionConfig(BaseModel):
    source: str = Field(default='camera', pattern='^(camera|video)$')
    alpha: float = Field(default=0.25, gt=0, le=1)
    stable_frames: int = Field(default=3, ge=1, le=30)
    mirrored: bool = False


def signed_angle(a, b, c):
    """Graus orientados em coordenadas de imagem (y crescente para baixo)."""
    u, v = (a[0]-b[0], a[1]-b[1]), (c[0]-b[0], c[1]-b[1])
    if math.hypot(*u) == 0 or math.hypot(*v) == 0:
        raise ValueError('Vetor nulo')
    return math.degrees(math.atan2(u[0]*v[1]-u[1]*v[0], u[0]*v[0]+u[1]*v[1]))


class Session:
    def __init__(self, config):
        self.config = config
        self.lock = threading.Lock()
        self.calibration = Calibracao()
        self.smoother = SuavizadorMetricas(config.alpha)
        self.filter = FiltroPosturaEstavel(config.stable_frames)
        self.tracker = RastreadorRepeticoes()
        self.rows = []
        self.last_metrics = None
        self.pending = {}
        self.last_ms = -1
        self.side = None
        self.landmarker = None
        self.closed = False

    def close(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None
        self.closed = True

    def process(self, payload, timestamp_ms):
        if self.closed:
            raise ValueError('Sessão encerrada. Crie uma nova sessão.')
        if timestamp_ms <= self.last_ms:
            raise ValueError('Os timestamps precisam crescer. Crie nova sessão ao reiniciar um vídeo.')
        if len(self.rows) >= 100000:
            raise ValueError('Limite de quadros da sessão atingido. Exporte o CSV e inicie outra sessão.')
        image = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('Quadro JPEG inválido.')
        h, w = image.shape[:2]
        if max(h, w) > 1920:
            raise ValueError('Reduza o quadro para até 1920 pixels por dimensão.')
        if not MODEL.exists():
            raise FileNotFoundError('Execute python scripts/download_model.py para obter o modelo.')
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        if self.landmarker is None:
            self.landmarker = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(MODEL)),
                running_mode=vision.RunningMode.VIDEO, num_poses=1,
                min_pose_detection_confidence=0.5, min_pose_presence_confidence=0.5, min_tracking_confidence=0.5))
        started = time.perf_counter()
        result = self.landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB)), timestamp_ms)
        self.last_ms = timestamp_ms
        self.last_metrics = None
        raw = smooth = None
        posture = stable = Postura.DESCONHECIDA
        event = ''
        signed_knee = signed_hip = None
        quality = 'SEM POSTURA'
        if result.pose_landmarks:
            raw, _, _ = extrair_metricas_corpo(result.pose_landmarks[0], w, h, 0.60)
        if raw is not None:
            if self.side is not None and self.side != raw.lado:
                self.smoother.reiniciar()
                self.filter.reiniciar()
            self.side = raw.lado
            p = raw.pontos
            signed_knee = signed_angle(p['quadril'], p['joelho'], p['tornozelo'])
            signed_hip = signed_angle(p['ombro'], p['quadril'], p['joelho'])
            smooth = self.smoother.atualizar(raw)
            self.last_metrics = smooth
            posture = self.calibration.classificar(smooth.angulo_joelho, smooth.angulo_quadril)
            stable = self.filter.atualizar(posture)
            feedback, event = self.tracker.atualizar(stable, timestamp_ms/1000)
            quality = 'POSTURA COMPLETA'
        else:
            if result.pose_landmarks:
                quality = 'POSTURA PARCIAL'
            feedback, event = self.tracker.registrar_ausencia()
            if self.tracker.quadros_ausentes >= 15:
                self.smoother.reiniciar()
                self.filter.reiniciar()
        processing = round((time.perf_counter()-started)*1000, 2)
        row = dict(quadro=len(self.rows)+1, tempo_fonte_s=timestamp_ms/1000,
                   fonte=self.config.source, espelhado=self.config.mirrored,
                   alfa=self.config.alpha, quadros_estaveis=self.config.stable_frames,
                   lado=raw.lado if raw else '', visibilidade=raw.visibilidade if raw else '',
                   joelho_bruto=raw.angulo_joelho if raw else '', quadril_bruto=raw.angulo_quadril if raw else '',
                   joelho_orientado=signed_knee, quadril_orientado=signed_hip,
                   joelho_ema=smooth.angulo_joelho if smooth else '', quadril_ema=smooth.angulo_quadril if smooth else '',
                   postura_antes_estabilidade=posture.value, postura_estavel=stable.value,
                   fase=self.tracker.fase.value, repeticoes=self.tracker.repeticoes,
                   incompletas=self.tracker.tentativas_incompletas, canceladas=self.tracker.ciclos_cancelados,
                   duracao_ultima_s=self.tracker.duracao_ultima_repeticao, evento=event, processamento_ms=processing)
        self.rows.append(row)
        return dict(quality=quality, phase=self.tracker.fase.value, repetitions=self.tracker.repeticoes,
                    incomplete=self.tracker.tentativas_incompletas, cancelled=self.tracker.ciclos_cancelados,
                    calibrated=self.calibration.esta_calibrada, feedback=feedback, processing_ms=processing,
                    metrics=asdict(smooth) if smooth else None,
                    landmarks=[{'x':p.x,'y':p.y,'visibility':p.visibility} for p in result.pose_landmarks[0]] if result.pose_landmarks else [])


def get_session(sid):
    with SESSIONS_LOCK:
        session = SESSIONS.get(sid)
    if session is None:
        raise HTTPException(404, 'Sessão não encontrada.')
    return session


@app.get('/')
def index():
    return FileResponse(ROOT/'web/index.html')


@app.get('/api/health')
def health():
    return {'status':'ok', 'model_ready':MODEL.exists(), 'method':'regras geométricas', 'clinical_validation':False}


@app.post('/api/sessions')
def new_session(config: SessionConfig):
    with SESSIONS_LOCK:
        if len(SESSIONS) >= 32:
            raise HTTPException(409, 'Exporte os CSVs e reinicie o servidor para iniciar outras sessões.')
        sid = uuid.uuid4().hex
        SESSIONS[sid] = Session(config)
    return {'id':sid}


@app.post('/api/sessions/{sid}/frame')
async def frame(sid: str, request: Request, timestamp_ms: int):
    if timestamp_ms < 0:
        raise HTTPException(422, 'Timestamp negativo.')
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > 2000000:
            raise HTTPException(413, 'Quadro acima de 2 MB.')
    session = get_session(sid)
    def work():
        with session.lock:
            return session.process(bytes(payload), timestamp_ms)
    try:
        return await asyncio.to_thread(work)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post('/api/sessions/{sid}/calibrate/{posture}')
def calibrate(sid: str, posture: str):
    session = get_session(sid)
    with session.lock:
        if posture not in ('sitting','standing'):
            raise HTTPException(422, 'Postura inválida.')
        if session.closed or session.last_metrics is None:
            raise HTTPException(409, 'Enquadre o corpo inteiro durante uma sessão ativa.')
        m = session.last_metrics
        session.pending[posture] = (m.angulo_joelho,m.angulo_quadril)
        if len(session.pending) == 2:
            calibration = finalizar_calibracao(session.pending['sitting'],session.pending['standing'])
            session.pending.clear()
            if calibration is None:
                raise HTTPException(422, 'Amplitude insuficiente. Registre novamente as duas posturas.')
            session.calibration = calibration
            session.smoother.reiniciar()
            session.filter.reiniciar()
            session.tracker.reiniciar()
        return {'calibrated':session.calibration.esta_calibrada,'registered':posture}


@app.post('/api/sessions/{sid}/stop')
def stop(sid: str):
    session = get_session(sid)
    with session.lock:
        session.close()
    return {'status':'stopped'}


@app.get('/api/sessions/{sid}/csv')
def download_csv(sid: str):
    session = get_session(sid)
    with session.lock:
        if not session.rows:
            raise HTTPException(409, 'A sessão ainda não possui quadros.')
        out = io.StringIO(newline='')
        writer = csv.DictWriter(out,fieldnames=list(session.rows[0]),delimiter=';')
        writer.writeheader()
        writer.writerows(session.rows)
    return Response(out.getvalue().encode('utf-8-sig'),media_type='text/csv',
                    headers={'Content-Disposition':f'attachment; filename="sts_{sid[:8]}.csv"'})
