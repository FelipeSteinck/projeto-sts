"""Treino com CV agrupada; teste reservado em comando separado."""
from __future__ import annotations

import json
import math
import platform
import statistics
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, recall_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.atributos import FEATURES, SCHEMA
from src.modelos import CLASSES, ModeloSTS, export_model
from src.motor import MotorSTS
from .dados import load_dataset, session_features, write_csv


def dump(path, obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def reference_events(frames):
    """Extremos anotados em ordem; independente do classificador e do seu FSM."""
    armed=standing=False; events=[]
    for f in frames:
        if f['usage']!='avaliacao' or f['label'] not in CLASSES:
            armed=standing=False
        elif f['label']=='SENTADO':
            if armed and standing: events.append(f['time'])
            armed=True; standing=False
        elif f['label']=='EM PÉ' and armed:
            standing=True
    return events


def match_events(reference, predicted, tolerance):
    candidates=sorted((abs(p-r),pi,ri,p-r) for pi,p in enumerate(predicted)
                      for ri,r in enumerate(reference) if abs(p-r)<=tolerance)
    used_p=set(); used_r=set(); latencies=[]
    for _,pi,ri,latency in candidates:
        if pi not in used_p and ri not in used_r:
            used_p.add(pi); used_r.add(ri); latencies.append(latency)
    return dict(matched=len(latencies),false_events=len(predicted)-len(used_p),
        missed_events=len(reference)-len(used_r),latency_s=latencies)


def classification_metrics(truth, predicted):
    if not truth:
        raise ValueError('Nenhum quadro rotulado para avaliar.')
    return dict(f1_macro=float(f1_score(truth,predicted,labels=list(CLASSES),average='macro',zero_division=0)),
        balanced_accuracy=float(recall_score(truth,predicted,labels=list(CLASSES),average='macro',zero_division=0)),
        support={c:truth.count(c) for c in CLASSES},
        confusion=confusion_matrix(truth,predicted,labels=[*CLASSES,'DESCONHECIDA']).tolist()[:3],
        confusion_rows=list(CLASSES),confusion_columns=[*CLASSES,'DESCONHECIDA'])


def evaluate_sessions(sessions, model=None, alpha=.25, stable_frames=3, tolerance=1.):
    truth=[]; predicted=[]; per_session=[]; exported=[]; all_latency=[]
    for session in sessions:
        engine=MotorSTS(alpha,stable_frames,session.calibration,model)
        intervals=[i for i in session.intervals if i[3]=='avaliacao']
        start,end=intervals[0][0],intervals[-1][1]
        considered=[f for f in session.frames if start <= f['time'] < end]
        count_available=(all(i[2] in CLASSES for i in intervals) and
            all(abs(a[1]-b[0])<1e-8 for a,b in zip(intervals,intervals[1:])))
        observed=[]; local_truth=[]; local_pred=[]; valid=0
        for frame in considered:
            result=engine.update(frame['raw'],frame['time'])
            if result['event']=='repeticao_concluida': observed.append(frame['time'])
            if frame['usage']!='avaliacao' or frame['label'] not in CLASSES:
                continue
            prediction=result['stable'].value
            local_truth.append(frame['label']); local_pred.append(prediction)
            valid+=result['smooth'] is not None
            exported.append(dict(sessao=session.id,tempo_fonte_s=frame['time'],
                referencia=frame['label'],predicao=prediction,repeticoes=engine.tracker.repeticoes,
                evento=result['event']))
        # A referência usa os intervalos manuais, mesmo se um extremo não foi
        # amostrado em nenhum quadro. Não reconstruir verdade a partir da pose.
        actual=reference_events([dict(time=a,label=c,usage=d) for a,b,c,d in intervals])
        events=match_events(actual,observed,tolerance) if count_available else None
        error=abs(len(actual)-len(observed)) if count_available else None
        if events: all_latency.extend(events['latency_s'])
        summary=dict(sessao=session.id,participante=session.participant,grupo=session.group,
            frames=len(local_truth),valid_pose_frames=valid,coverage=valid/len(local_truth),
            reference_count=len(actual) if count_available else None,
            predicted_count=len(observed),absolute_count_error=error,
            error_per_10=(10*error/len(actual)) if count_available and actual else None,
            events=events,classification=classification_metrics(local_truth,local_pred))
        if not count_available:
            summary['count_note']='Referência descontínua/inválida: contagem não avaliada.'
        per_session.append(summary); truth.extend(local_truth); predicted.extend(local_pred)
    errors=[s['absolute_count_error'] for s in per_session if s['absolute_count_error'] is not None]
    normalized=[s['error_per_10'] for s in per_session if s['error_per_10'] is not None]
    summary=dict(classification=classification_metrics(truth,predicted),sessions=per_session,
        mean_session_f1=statistics.mean(s['classification']['f1_macro'] for s in per_session),
        count_mae=statistics.mean(errors) if errors else None,
        mean_error_per_10=statistics.mean(normalized) if normalized else None,
        event_tolerance_s=tolerance,event_latency_median_s=statistics.median(all_latency) if all_latency else None,
        event_latency_mae_s=statistics.mean(abs(x) for x in all_latency) if all_latency else None)
    return summary,exported


def build_estimator(method, parameter):
    if method=='logistica':
        return Pipeline([('scale',StandardScaler()),('classifier',LogisticRegression(
            C=parameter,max_iter=2000,class_weight='balanced',random_state=42))])
    return RandomForestClassifier(n_estimators=80,max_depth=parameter,min_samples_leaf=2,
                                  class_weight='balanced',random_state=42,n_jobs=1)


def training_matrix(sessions, alpha, cache):
    x=[]; y=[]
    for s in sessions:
        key=(s.id,alpha)
        if key not in cache: cache[key]=session_features(s,alpha)
        for row in cache[key]:
            if row['usage']=='avaliacao' and row['label'] in CLASSES and row['features'] is not None:
                x.append([row['features'][k] for k in FEATURES]); y.append(row['label'])
    if set(y)!=set(CLASSES):
        raise ValueError('Cada treino de CV precisa conter as três classes com pose válida.')
    return np.asarray(x),np.asarray(y)


def train(manifest, output, alphas=(.25,1.), stabilities=(1,3), folds=3):
    dataset=load_dataset(manifest)
    sessions=[s for s in dataset.sessions if s.partition=='treino']
    groups=[s.group for s in sessions]
    if len(set(groups))<folds or folds<2:
        raise ValueError('Grupos de treino insuficientes para a CV solicitada.')
    if not alphas or any(not 0<a<=1 for a in alphas) or not stabilities or any(n<1 or n>30 for n in stabilities):
        raise ValueError('Grade de alfa/estabilidade inválida.')
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    metadata=dict(tipo_dados=dataset.kind,python=platform.python_version(),sklearn=sklearn.__version__,
        training_sessions=[s.id for s in sessions],training_participants=sorted({s.participant for s in sessions}),
        grouping=dataset.grouping,input_hashes=dataset.hashes,
        note='DADOS SINTÉTICOS: verificação de software, sem validação humana.' if dataset.kind=='sintetico' else 'Dados reais; consultar protocolo e limites amostrais.')
    splitter=list(GroupKFold(n_splits=folds).split(sessions,groups=groups))
    cache={}; report=dict(metadata,folds=[],models={})
    for train_idx,val_idx in splitter:
        report['folds'].append(dict(train=[sessions[i].id for i in train_idx],
            validation=[sessions[i].id for i in val_idx],
            train_groups=sorted({groups[i] for i in train_idx}),validation_groups=sorted({groups[i] for i in val_idx})))
    for method,parameters in (('logistica',(.1,1.,10.)),('floresta',(5,None))):
        candidates=[]
        for alpha in alphas:
            for parameter in parameters:
                estimates=[]
                for train_idx,val_idx in splitter:
                    fold_train=[sessions[i] for i in train_idx]; fold_val=[sessions[i] for i in val_idx]
                    x,y=training_matrix(fold_train,alpha,cache)
                    estimator=build_estimator(method,parameter).fit(x,y)
                    estimates.append((fold_val,ModeloSTS(export_model(estimator,method,dict(metadata,alpha=alpha,stable_frames=1)))))
                for stable in stabilities:
                    fold_metrics=[evaluate_sessions(s,model,alpha,stable)[0] for s,model in estimates]
                    candidates.append(dict(alpha=alpha,stable_frames=stable,parameter=parameter,
                        cv_f1=statistics.mean(m['mean_session_f1'] for m in fold_metrics),
                        cv_count_mae=statistics.mean(m['count_mae'] for m in fold_metrics if m['count_mae'] is not None)
                            if any(m['count_mae'] is not None for m in fold_metrics) else None,
                        cv_latency_mae=statistics.mean(m['event_latency_mae_s'] for m in fold_metrics if m['event_latency_mae_s'] is not None)
                            if any(m['event_latency_mae_s'] is not None for m in fold_metrics) else None))
        def ranking(candidate):
            return (candidate['cv_f1'], -(candidate['cv_count_mae'] if candidate['cv_count_mae'] is not None else math.inf),
                    -(candidate['cv_latency_mae'] if candidate['cv_latency_mae'] is not None else math.inf))
        best=max(candidates,key=ranking)
        x,y=training_matrix(sessions,best['alpha'],cache)
        estimator=build_estimator(method,best['parameter']).fit(x,y)
        artifact=export_model(estimator,method,dict(metadata,alpha=best['alpha'],
            stable_frames=best['stable_frames'],selection=best))
        dump(output/f'{method}.json',artifact)
        report['models'][method]=dict(selected=best,candidates=candidates)
    report['selection_rule']='Maior F1 médio por sessão na CV; desempate por MAE de contagem e latência absoluta. Sem consultar métricas de teste.'
    baseline=[]
    for alpha in alphas:
        for stable in stabilities:
            metrics=[evaluate_sessions([sessions[i] for i in val],alpha=alpha,stable_frames=stable)[0]
                     for _,val in splitter]
            baseline.append(dict(alpha=alpha,stable_frames=stable,
                cv_f1=statistics.mean(m['mean_session_f1'] for m in metrics),
                cv_count_mae=statistics.mean(m['count_mae'] for m in metrics if m['count_mae'] is not None)
                    if any(m['count_mae'] is not None for m in metrics) else None,
                cv_latency_mae=statistics.mean(m['event_latency_mae_s'] for m in metrics if m['event_latency_mae_s'] is not None)
                    if any(m['event_latency_mae_s'] is not None for m in metrics) else None))
    report['baseline']=dict(selected=max(baseline,key=ranking),candidates=baseline)
    report['test_evaluated']=False
    dump(output/'treinamento.json',report)
    return report


def evaluate(manifest, models, output, tolerance=1.):
    if tolerance<=0: raise ValueError('Tolerância precisa ser positiva.')
    dataset=load_dataset(manifest)
    test=[s for s in dataset.sessions if s.partition=='teste']
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    report=dict(tipo_dados=dataset.kind,input_hashes=dataset.hashes,test_sessions=[s.id for s in test],
        note='RESULTADOS SINTÉTICOS: não representam desempenho em pessoas.' if dataset.kind=='sintetico' else 'Avaliação no teste reservado; não selecionar parâmetros com este resultado.',methods={})
    training=json.loads((Path(models)/'treinamento.json').read_text(encoding='utf-8'))
    if training['input_hashes'] != dataset.hashes:
        raise ValueError('Treinamento e manifesto congelado diferem.')
    baseline=training['baseline']['selected']
    settings=[('regras',None,baseline['alpha'],baseline['stable_frames'])]
    for method in ('logistica','floresta'):
        model=ModeloSTS.load(Path(models)/f'{method}.json')
        meta=model.artifact
        if meta['tipo_dados']!=dataset.kind or meta['input_hashes']!=dataset.hashes:
            raise ValueError('Modelo e conjunto de dados diferem do manifesto congelado.')
        if set(meta['training_sessions']) & {s.id for s in test}:
            raise ValueError('Sessões de teste usadas no treinamento.')
        if dataset.grouping=='participante' and set(meta['training_participants']) & {s.participant for s in test}:
            raise ValueError('Participantes de teste usados no treinamento.')
        settings.append((method,model,meta['alpha'],meta['stable_frames']))
    for method,model,alpha,stable in settings:
        metrics,rows=evaluate_sessions(test,model,alpha,stable,tolerance)
        metrics.update(alpha=alpha,stable_frames=stable)
        report['methods'][method]=metrics
        write_csv(output/f'predicoes_{method}.csv',rows)
    dump(output/'avaliacao.json',report)
    make_figures(report,output)
    return report


def make_figures(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for method,metrics in report['methods'].items():
        fig,ax=plt.subplots(figsize=(7,4.5),layout='constrained')
        matrix=np.asarray(metrics['classification']['confusion'])
        ax.imshow(matrix,cmap='Blues')
        for (i,j),v in np.ndenumerate(matrix):
            ax.text(j,i,str(v),ha='center',va='center',color='white' if matrix.max() and v>matrix.max()/2 else 'black')
        ax.set_xticks(range(4),[*CLASSES,'SEM POSE'],rotation=20)
        ax.set_yticks(range(3),CLASSES)
        ax.set_xlabel('Predição estável'); ax.set_ylabel('Referência manual')
        ax.set_title(f'{method} - {report["tipo_dados"].upper()}\nMatriz de confusão no teste reservado')
        fig.savefig(Path(output)/f'confusao_{method}.png',dpi=160); plt.close(fig)
