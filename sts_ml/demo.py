"""Dados artificiais para integração. Nenhuma imagem/pessoa ou métrica clínica."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from src.atributos import SCHEMA, raw_columns
from src.nucleo import MetricasCorpo, calcular_angulo, calcular_inclinacao_tronco
from .dados import write_csv
from .experimento import dump, train, evaluate


def create_demo(root):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(42); sessions=[]
    for i in range(8):
        sid=f'S{i+1:02d}'; participant='P01' if i<4 else 'P02'
        length=145+3*i; torso=160+2*i
        time=0.; rows=[]; labels=[]; dt=1/15
        phases=[('SENTADO',1.2)]
        for _ in range(2):
            phases += [('SUBIDA',1.4),('EM PÉ',1.2),('DESCIDA',1.4),('SENTADO',1.2)]
        for phase,duration in phases:
            start=time; steps=round(duration/dt)
            for k in range(steps):
                fraction=(k+1)/steps
                beta=math.pi/2 if phase=='SENTADO' else 0 if phase=='EM PÉ' else (1-fraction)*math.pi/2 if phase=='SUBIDA' else fraction*math.pi/2
                hip=(200.,500-length-length*math.cos(beta))
                knee=(200+length*math.sin(beta),500-length)
                ankle=(knee[0],500.)
                shoulder=(hip[0]+.12*torso*math.sin(beta),hip[1]-torso)
                points={p:tuple(np.asarray(v)+rng.normal(0,.35,2)) for p,v in zip(
                    ('ombro','quadril','joelho','tornozelo'),(shoulder,hip,knee,ankle))}
                raw=MetricasCorpo('esquerdo',1.,calcular_angulo(points['quadril'],points['joelho'],points['tornozelo']),
                    calcular_angulo(points['ombro'],points['quadril'],points['joelho']),
                    calcular_inclinacao_tronco(points['ombro'],points['quadril']),points)
                rows.append(dict(schema_atributos=SCHEMA,tipo_dados='sintetico',sessao=sid,participante=participant,
                    quadro=len(rows)+1,tempo_fonte_s=round(time,6),espelhado=False,**raw_columns(raw)))
                time+=dt
            labels.append(dict(inicio_s=round(start,6),fim_s=round(time,6),
                rotulo='TRANSIÇÃO' if phase in ('SUBIDA','DESCIDA') else phase,uso='avaliacao'))
        write_csv(root/f'{sid}_quadros.csv',rows); write_csv(root/f'{sid}_rotulos.csv',labels)
        sessions.append(dict(id=sid,participante=participant,particao='teste' if i in (3,7) else 'treino',
            quadros=f'{sid}_quadros.csv',rotulos=f'{sid}_rotulos.csv',
            calibracao=dict(joelho_sentado=90.,quadril_sentado=83.,joelho_em_pe=180.,quadril_em_pe=180.,origem='demonstracao_sintetica')))
    manifest=root/'manifesto.json'
    dump(manifest,dict(tipo_dados='sintetico',agrupar_por='sessao',sessoes=sessions))
    return manifest


def run_demo(data, models, results):
    manifest=create_demo(data)
    train(manifest,models,alphas=(.25,1.),stabilities=(1,3))
    return evaluate(manifest,models,results)
