"""Adaptador web do prototipo STS. Video fica em memoria durante a inferencia."""
from __future__ import annotations

import asyncio
import csv
import io
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

from src.nucleo import finalizar_calibracao
from src.aplicacao import extrair_metricas_corpo
from src.atributos import SCHEMA, raw_columns, signed_angle
from src.modelos import ModeloSTS, model_catalog
from src.motor import MotorSTS

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'models/pose_landmarker_lite.task'
MODELS_DIR = ROOT / 'models'
app = FastAPI(title='Monitor STS', docs_url=None, redoc_url=None)
app.mount('/static', StaticFiles(directory=ROOT / 'web'), name='static')
SESSIONS: dict[str, Session] = {}
SESSIONS_LOCK = threading.Lock()


class SessionConfig(BaseModel):
    source: str = Field(default='camera', pattern='^(camera|video)$')
    alpha: float = Field(default=0.25, gt=0, le=1)
    stable_frames: int = Field(default=3, ge=1, le=30)
    mirrored: bool = False
    method: str = Field(default='regras', pattern='^(regras|sts/logistica|sts/floresta|demo/logistica|demo/floresta)$')
    session_id: str = Field(default='S01',pattern='^[A-Za-z0-9_-]{1,40}$')
    participant_id: str = Field(default='P01',pattern='^[A-Za-z0-9_-]{1,40}$')


class Session:
    def __init__(self, config):
        self.config = config
        self.lock = threading.Lock()
        classifier=None
        if config.method != 'regras':
            classifier=ModeloSTS.load(MODELS_DIR/f'{config.method}.json')
            expected_kind='sintetico' if config.method.startswith('demo/') else 'real'
            if classifier.artifact['tipo_dados'] != expected_kind:
                raise ValueError('Modelo com tipo de dados incorreto.')
            if config.alpha != classifier.artifact['alpha'] or config.stable_frames != classifier.artifact['stable_frames']:
                raise ValueError('Use alfa e estabilidade registrados no modelo treinado.')
        self.engine=MotorSTS(config.alpha,config.stable_frames,model=classifier)
        self.calibration=self.engine.calibration
        self.tracker=self.engine.tracker
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
        raw = None
        quality = 'SEM POSTURA'
        if result.pose_landmarks:
            try: raw, _, _ = extrair_metricas_corpo(result.pose_landmarks[0], w, h, 0.60)
            except ValueError: pass
        processed=self.engine.update(raw,timestamp_ms/1000)
        smooth=processed['smooth']
        self.last_metrics=smooth
        posture,stable=processed['posture'],processed['stable']
        event,feedback=processed['event'],processed['feedback']
        quality='POSTURA COMPLETA' if raw else 'POSTURA PARCIAL' if result.pose_landmarks else 'SEM POSTURA'
        processing = round((time.perf_counter()-started)*1000, 2)
        row = dict(schema_atributos=SCHEMA,tipo_dados='real',sessao=self.config.session_id,
                   participante=self.config.participant_id,metodo=self.config.method,
                   tipo_modelo=self.engine.model.artifact['tipo_dados'] if self.engine.model else 'regras',
                   quadro=len(self.rows)+1, tempo_fonte_s=timestamp_ms/1000,
                   fonte=self.config.source, espelhado=self.config.mirrored,
                   alfa=self.config.alpha, quadros_estaveis=self.config.stable_frames,
                   **raw_columns(raw),**processed['oriented'],**processed['features'],
                   postura_regras=processed['rule_stable'].value,
                   repeticoes_regras=self.engine.rule_tracker.repeticoes,
                   pontuacao_modelo=processed['confidence'],calibrado=self.calibration.esta_calibrada,
                   postura_antes_estabilidade=posture.value, postura_estavel=stable.value,
                   fase=self.tracker.fase.value, repeticoes=self.tracker.repeticoes,
                   incompletas=self.tracker.tentativas_incompletas, canceladas=self.tracker.ciclos_cancelados,
                   duracao_ultima_s=self.tracker.duracao_ultima_repeticao, evento=event, processamento_ms=processing)
        self.rows.append(row)
        return dict(quality=quality, phase=self.tracker.fase.value, repetitions=self.tracker.repeticoes,
                    incomplete=self.tracker.tentativas_incompletas, cancelled=self.tracker.ciclos_cancelados,
                    calibrated=self.calibration.esta_calibrada, feedback=feedback, processing_ms=processing,
                    method=self.config.method,model_kind=self.engine.model.artifact['tipo_dados'] if self.engine.model else 'regras',
                    model_score=processed['confidence'],rule_repetitions=self.engine.rule_tracker.repeticoes,
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


@app.get('/api/models')
def available_models():
    return {'models':model_catalog(MODELS_DIR)}


@app.post('/api/sessions')
def new_session(config: SessionConfig):
    with SESSIONS_LOCK:
        if len(SESSIONS) >= 32:
            raise HTTPException(409, 'Exporte os CSVs e reinicie o servidor para iniciar outras sessões.')
        sid = uuid.uuid4().hex
        try:
            SESSIONS[sid] = Session(config)
        except FileNotFoundError as exc:
            raise HTTPException(409,'Modelo indisponível. Execute o treinamento antes de selecioná-lo.') from exc
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
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
            session.engine.calibration=calibration
            session.engine.reset()
        return {'calibrated':session.calibration.esta_calibrada,'registered':posture}


@app.post('/api/sessions/{sid}/stop')
def stop(sid: str):
    session = get_session(sid)
    with session.lock:
        session.close()
    return {'status':'stopped'}


@app.get('/api/sessions/{sid}/config')
def download_config(sid: str):
    session=get_session(sid)
    with session.lock:
        if not session.calibration.esta_calibrada:
            raise HTTPException(409,'Registre as duas posturas antes de exportar a calibração.')
        import json
        content=json.dumps(dict(schema=SCHEMA,config=session.config.model_dump(),
            calibracao=asdict(session.calibration)),ensure_ascii=False,indent=2)
    return Response(content,media_type='application/json',headers={
        'Content-Disposition':f'attachment; filename="calibracao_{session.config.session_id}.json"'})


@app.get('/rotular')
def annotation_page():
    return FileResponse(ROOT/'web/rotular.html')


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
