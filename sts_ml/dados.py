"""Leitura estrita de sessões e rótulos manuais. Nunca usa predição como rótulo."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from src.atributos import SCHEMA, raw_from_row
from src.modelos import CLASSES
from src.motor import MotorSTS
from src.nucleo import Calibracao


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as handle:
        return list(csv.DictReader(handle,delimiter=';'))


def write_csv(path, rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:
        raise ValueError('Nenhuma linha para exportar.')
    with path.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),delimiter=';')
        writer.writeheader(); writer.writerows(rows)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_intervals(path):
    intervals=[]
    for row in read_csv(path):
        start,end=float(row['inicio_s']),float(row['fim_s'])
        label=row['rotulo'].strip().upper()
        usage=row.get('uso','avaliacao').strip().lower()
        if label == 'TRANSICAO': label='TRANSIÇÃO'
        if label not in (*CLASSES,'INVALIDO') or usage not in ('avaliacao','calibracao'):
            raise ValueError(f'Rótulo/uso inválido em {path}: {row}')
        if not math.isfinite(start+end) or start < 0 or end <= start:
            raise ValueError('Intervalos precisam ter 0 <= início < fim finitos.')
        intervals.append((start,end,label,usage))
    intervals.sort()
    if not intervals or any(a[1] > b[0] for a,b in zip(intervals,intervals[1:])):
        raise ValueError('Rótulos vazios ou intervalos sobrepostos.')
    eval_starts=[a for a,b,c,d in intervals if d=='avaliacao']
    calibration_ends=[b for a,b,c,d in intervals if d=='calibracao']
    if not eval_starts or (calibration_ends and max(calibration_ends) > min(eval_starts)):
        raise ValueError('A calibração deve preceder a avaliação.')
    return intervals


@dataclass
class Sessao:
    id: str
    participant: str
    partition: str
    frames: list
    calibration: Calibracao
    group: str
    intervals: list


@dataclass
class Dataset:
    kind: str
    grouping: str
    sessions: list[Sessao]
    hashes: dict


def load_dataset(manifest):
    manifest=Path(manifest)
    spec=json.loads(manifest.read_text(encoding='utf-8'))
    kind,grouping=spec['tipo_dados'],spec.get('agrupar_por','sessao')
    if kind not in ('real','sintetico') or grouping not in ('sessao','participante'):
        raise ValueError('Tipo de dados ou agrupamento inválido.')
    sessions=[]; ids=set(); hashes={'manifesto':digest(manifest)}
    for item in spec['sessoes']:
        sid=item['id']; participant=item['participante']; partition=item['particao']
        if not sid or not participant or sid in ids or partition not in ('treino','teste'):
            raise ValueError('Sessão duplicada, identificador vazio ou partição inválida.')
        ids.add(sid)
        raw_path=manifest.parent/item['quadros']; label_path=manifest.parent/item['rotulos']
        hashes[sid]={'quadros':digest(raw_path),'rotulos':digest(label_path)}
        intervals=read_intervals(label_path)
        cal=item.get('calibracao')
        if isinstance(cal,str):
            calibration_path=manifest.parent/cal
            hashes[sid]['calibracao']=digest(calibration_path)
            calibration_json=json.loads(calibration_path.read_text(encoding='utf-8-sig'))
            cal=calibration_json.get('calibracao',calibration_json)
        if not isinstance(cal,dict):
            raise ValueError(f'{sid}: declare calibração independente dos rótulos de avaliação.')
        calibration=Calibracao(**cal)
        if not calibration.valida():
            raise ValueError(f'{sid}: amplitude de calibração insuficiente.')
        frames=[]; previous=-1.; interval_index=0
        for row in read_csv(raw_path):
            if row.get('schema_atributos') != SCHEMA or row.get('tipo_dados') != kind:
                raise ValueError(f'{sid}: schema/tipo de dados incompatível; reextraia o vídeo.')
            if row.get('sessao') != sid or row.get('participante') != participant:
                raise ValueError(f'{sid}: identificação do CSV difere do manifesto.')
            seconds=float(row['tempo_fonte_s'])
            if not math.isfinite(seconds) or seconds <= previous or seconds < 0:
                raise ValueError(f'{sid}: timestamps precisam crescer estritamente.')
            previous=seconds
            while interval_index < len(intervals) and seconds >= intervals[interval_index][1]:
                interval_index+=1
            label=None; usage='fora'
            if interval_index < len(intervals):
                start,end,candidate,usage_candidate=intervals[interval_index]
                if start <= seconds < end:
                    label,usage=candidate,usage_candidate
            frames.append(dict(time=seconds,raw=raw_from_row(row),label=label,usage=usage))
        if not frames or not any(f['usage']=='avaliacao' and f['label'] in CLASSES for f in frames):
            raise ValueError(f'{sid}: nenhum quadro de avaliação rotulado.')
        group=sid if grouping=='sessao' else participant
        sessions.append(Sessao(sid,participant,partition,frames,calibration,group,intervals))
    train={s.group for s in sessions if s.partition=='treino'}
    test={s.group for s in sessions if s.partition=='teste'}
    if not train or not test or train & test:
        raise ValueError('Treino/teste ausentes ou grupos compartilhados entre as partições.')
    return Dataset(kind,grouping,sessions,hashes)


def session_features(session, alpha):
    engine=MotorSTS(alpha=alpha,stable_frames=1,calibration=session.calibration)
    start=min(f['time'] for f in session.frames if f['usage']=='avaliacao')
    records=[]
    for frame in session.frames:
        if frame['time'] < start:
            continue
        result=engine.update(frame['raw'],frame['time'])
        records.append(dict(frame,features=result['features'] if result['smooth'] else None))
    return records
