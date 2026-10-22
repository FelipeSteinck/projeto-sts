import copy
import json
import math

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.atributos import FEATURES, ExtratorAtributos, SerieOrientada
from src.modelos import CLASSES, ModeloSTS, export_model
from src.nucleo import MetricasCorpo
from sts_ml.dados import load_dataset, read_intervals, write_csv
from sts_ml.demo import create_demo
from sts_ml.experimento import train, evaluate, match_events


def metrics(mirror=False,side='esquerdo'):
    points={'ombro':(0.,0.),'quadril':(0.,100.),'joelho':(100.,100.),'tornozelo':(100.,200.)}
    if mirror: points={k:(-x,y) for k,(x,y) in points.items()}
    return MetricasCorpo(side,1.,90.,90.,0.,points)


def test_features_are_causal_and_mirror_invariant():
    left,right=ExtratorAtributos(.25),ExtratorAtributos(.25)
    for t in (0.,.1,.2):
        _,a,oa,_=left.update(metrics(),t)
        _,b,ob,_=right.update(metrics(True),t)
        assert a==b
        assert oa['joelho_orientado']==-ob['joelho_orientado']
        assert oa['joelho_continuo']==ob['joelho_continuo']
    assert a['altura_quadril_rel']==.5
    assert a['vel_joelho']==0
    with pytest.raises(ValueError,match='Tempo'): left.update(metrics(),.2)
    _,f,_,reset=left.update(metrics(side='direito'),.3)
    assert reset and f['vel_altura']==0
    _,_,_,reset=left.update(metrics(side='direito'),2.)
    assert reset


def test_oriented_series_unwraps_and_waits_for_bent_anchor():
    series=SerieOrientada()
    assert series.update(180)==(None,None)
    assert series.update(160)==(160,160)
    assert series.update(179)==(179,179)
    assert series.update(-179)==(-179,181)
    mirrored=SerieOrientada()
    assert mirrored.update(-160)==(160,160)
    assert mirrored.update(-179)==(179,179)
    assert mirrored.update(179)==(-179,181)


@pytest.mark.parametrize('method',['logistica','floresta'])
def test_numeric_json_export_agrees_with_sklearn(method):
    rng=np.random.default_rng(7); x=rng.normal(size=(90,len(FEATURES)))
    y=np.asarray([CLASSES[i%3] for i in range(90)])
    estimator=Pipeline([('scale',StandardScaler()),('classifier',LogisticRegression(max_iter=1000))]) if method=='logistica' else RandomForestClassifier(n_estimators=7,max_depth=4,random_state=42)
    estimator.fit(x,y)
    model=ModeloSTS(export_model(estimator,method,{'tipo_dados':'sintetico'}))
    for row,expected,probability in zip(x,estimator.predict(x),estimator.predict_proba(x)):
        label,score=model.predict(dict(zip(FEATURES,row)))
        assert label.value==expected
        assert score==pytest.approx(max(probability),abs=1e-10)


def test_manual_labels_reject_overlap_and_data_kind_mismatch(tmp_path):
    labels=tmp_path/'labels.csv'
    write_csv(labels,[dict(inicio_s=0,fim_s=2,rotulo='SENTADO'),dict(inicio_s=1,fim_s=3,rotulo='EM PÉ')])
    with pytest.raises(ValueError,match='sobrepostos'): read_intervals(labels)
    manifest=create_demo(tmp_path/'dataset')
    spec=json.loads(manifest.read_text('utf-8'));spec['tipo_dados']='real'
    manifest.write_text(json.dumps(spec),encoding='utf-8')
    with pytest.raises(ValueError,match='tipo de dados'): load_dataset(manifest)


def test_participant_groups_must_not_cross_holdout(tmp_path):
    manifest=create_demo(tmp_path)
    spec=json.loads(manifest.read_text('utf-8'));spec['agrupar_por']='participante'
    manifest.write_text(json.dumps(spec),encoding='utf-8')
    with pytest.raises(ValueError,match='compartilhados'): load_dataset(manifest)


def test_event_matching_is_one_to_one():
    result=match_events([1.,3.],[1.1,1.2,3.2],.5)
    assert result['matched']==2 and result['false_events']==1
    assert result['missed_events']==0


def test_reference_count_uses_annotations_even_if_frames_miss_a_phase(tmp_path):
    from sts_ml.experimento import evaluate_sessions
    manifest=create_demo(tmp_path)
    session=load_dataset(manifest).sessions[0]
    session.frames=[f for f in session.frames if f['label']=='SENTADO']
    report,_=evaluate_sessions([session],alpha=1.,stable_frames=1)
    summary=report['sessions'][0]
    assert summary['reference_count']==2
    assert summary['predicted_count']==0
    assert summary['events']['missed_events']==2


@pytest.fixture(scope='module')
def trained_demo(tmp_path_factory):
    root=tmp_path_factory.mktemp('trained')
    manifest=create_demo(root/'data')
    report=train(manifest,root/'models',alphas=(1.,),stabilities=(1,),folds=2)
    return root,manifest,report


def test_training_holdout_and_full_evaluation(trained_demo):
    root,manifest,report=trained_demo
    assert report['test_evaluated'] is False
    assert set(report['training_sessions']).isdisjoint({'S04','S08'})
    for fold in report['folds']:
        assert set(fold['train_groups']).isdisjoint(fold['validation_groups'])
    result=evaluate(manifest,root/'models',root/'evaluation')
    assert result['tipo_dados']=='sintetico'
    assert result['test_sessions']==['S04','S08']
    assert set(result['methods'])=={'regras','logistica','floresta'}
    for method in result['methods']:
        assert (root/'evaluation'/f'confusao_{method}.png').is_file()
        assert all(s['reference_count']==2 for s in result['methods'][method]['sessions'])


def test_test_labels_cannot_change_fitted_models(trained_demo):
    root,manifest,original=trained_demo
    # Muda apenas a referência de teste: o parâmetro e os pesos aprendidos não mudam.
    from sts_ml.dados import read_csv
    spec=json.loads(manifest.read_text('utf-8'))
    labels=manifest.parent/spec['sessoes'][3]['rotulos']
    saved=labels.read_bytes()
    rows=read_csv(labels)
    for row in rows:
        if row['rotulo']=='SENTADO': row['rotulo']='EM PÉ'
    try:
        write_csv(labels,rows)
        changed=train(manifest,root/'changed',alphas=(1.,),stabilities=(1,),folds=2)
        for method in ('logistica','floresta'):
            a=json.loads((root/'models'/f'{method}.json').read_text('utf-8'))
            b=json.loads((root/'changed'/f'{method}.json').read_text('utf-8'))
            assert a['model']==b['model']
            assert original['models'][method]['selected']==changed['models'][method]['selected']
    finally:
        labels.write_bytes(saved)


def test_web_model_selection_and_export(trained_demo,monkeypatch,tmp_path):
    import cv2
    import webapp
    from fastapi.testclient import TestClient
    from test_web import FakePose
    root,_,_=trained_demo
    target=tmp_path/'models'/'demo';target.mkdir(parents=True)
    for method in ('logistica','floresta'):
        (target/f'{method}.json').write_bytes((root/'models'/f'{method}.json').read_bytes())
    monkeypatch.setattr(webapp,'MODELS_DIR',target.parent)
    pose=tmp_path/'pose.task';pose.write_bytes(b'mocked');monkeypatch.setattr(webapp,'MODEL',pose)
    client=TestClient(webapp.app)
    assert len(client.get('/api/models').json()['models'])==2
    assert client.post('/api/sessions',json={'method':'sts/logistica'}).status_code==409
    assert client.post('/api/sessions',json={'method':'demo/logistica'}).status_code==422
    response=client.post('/api/sessions',json={'method':'demo/logistica','alpha':1,'stable_frames':1})
    assert response.status_code==200
    sid=response.json()['id'];session=webapp.SESSIONS[sid];session.landmarker=FakePose()
    _,jpeg=cv2.imencode('.jpg',np.zeros((480,640,3),np.uint8))
    result=client.post(f'/api/sessions/{sid}/frame?timestamp_ms=0',content=jpeg.tobytes()).json()
    assert result['method']=='demo/logistica' and result['model_kind']=='sintetico'
    assert 0 <= result['model_score'] <= 1
    assert client.get('/rotular').status_code==200
    assert client.get(f'/api/sessions/{sid}/config').status_code==409
    assert client.post(f'/api/sessions/{sid}/calibrate/sitting').status_code==200
    session.landmarker.standing=True
    client.post(f'/api/sessions/{sid}/frame?timestamp_ms=1000',content=jpeg.tobytes())
    assert client.post(f'/api/sessions/{sid}/calibrate/standing').json()['calibrated']
    assert client.get(f'/api/sessions/{sid}/config').json()['calibracao']['origem']=='calibracao_individual'
    session.close();webapp.SESSIONS.clear()
