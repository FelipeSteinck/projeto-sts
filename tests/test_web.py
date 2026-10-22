from types import SimpleNamespace
import csv
import io
import math

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

import webapp


@pytest.fixture(autouse=True)
def clean_sessions():
    webapp.SESSIONS.clear()
    yield
    for session in webapp.SESSIONS.values():
        session.close()
    webapp.SESSIONS.clear()


client = TestClient(webapp.app)


def new_session(**config):
    response = client.post('/api/sessions',json=config)
    assert response.status_code == 200
    return response.json()['id']


def test_oriented_angles_preserve_magnitude_and_mirror_sign():
    a,b,c=(0,-1),(0,0),(1,0)
    angle=webapp.signed_angle(a,b,c)
    mirror=lambda p:(-p[0],p[1])
    assert math.isclose(abs(angle),90)
    assert math.isclose(webapp.signed_angle(mirror(a),mirror(b),mirror(c)),-angle)
    with pytest.raises(ValueError):
        webapp.signed_angle(b,b,c)


def test_validation_and_sessions_are_isolated():
    assert client.post('/api/sessions',json={'alpha':0}).status_code == 422
    assert client.post('/api/sessions',json={'stable_frames':0}).status_code == 422
    first,second=new_session(),new_session()
    assert first != second
    assert webapp.SESSIONS[first].tracker is not webapp.SESSIONS[second].tracker
    assert client.post(f'/api/sessions/{first}/calibrate/sitting').status_code == 409
    assert client.get(f'/api/sessions/{first}/csv').status_code == 409


class FakePose:
    def __init__(self):
        self.standing=False
        self.missing=False
    def close(self):
        pass
    def detect_for_video(self,image,timestamp):
        if self.missing:
            return SimpleNamespace(pose_landmarks=[])
        points=[SimpleNamespace(x=.5,y=.5,visibility=0.,presence=0.) for _ in range(33)]
        coordinates=[(.4,.15),(.4,.4),(.4,.65),(.4,.9)] if self.standing else [(.4,.15),(.4,.4),(.7,.4),(.7,.8)]
        for index,(x,y) in zip([11,23,25,27],coordinates):
            points[index]=SimpleNamespace(x=x,y=y,visibility=1.,presence=1.)
        return SimpleNamespace(pose_landmarks=[points])


def test_frame_pipeline_counts_cycle_exports_raw_and_rejects_time_reversal(monkeypatch,tmp_path):
    model=tmp_path/'model.task';model.write_bytes(b'mocked')
    monkeypatch.setattr(webapp,'MODEL',model)
    sid=new_session(alpha=1,stable_frames=1)
    fake=FakePose();webapp.SESSIONS[sid].landmarker=fake
    _,jpeg=cv2.imencode('.jpg',np.zeros((480,640,3),np.uint8))
    def frame(t):
        return client.post(f'/api/sessions/{sid}/frame?timestamp_ms={t}',content=jpeg.tobytes())
    assert frame(0).json()['repetitions'] == 0
    fake.standing=True
    assert frame(1000).json()['repetitions'] == 0
    fake.standing=False
    assert frame(2000).json()['repetitions'] == 1
    assert frame(1500).status_code == 422
    response=client.get(f'/api/sessions/{sid}/csv')
    rows=list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig')),delimiter=';'))
    assert len(rows)==3
    assert float(rows[0]['joelho_bruto']) == abs(float(rows[0]['joelho_orientado']))
    assert float(rows[-1]['duracao_ultima_s']) == 1
    assert client.post(f'/api/sessions/{sid}/stop').status_code == 200
    assert frame(3000).status_code == 422


def test_loss_cancels_without_counting(monkeypatch,tmp_path):
    model=tmp_path/'model.task';model.write_bytes(b'mocked')
    monkeypatch.setattr(webapp,'MODEL',model)
    s=webapp.Session(webapp.SessionConfig(alpha=1,stable_frames=1))
    fake=FakePose();s.landmarker=fake
    _,jpeg=cv2.imencode('.jpg',np.zeros((480,640,3),np.uint8))
    s.process(jpeg.tobytes(),0)
    fake.standing=True;s.process(jpeg.tobytes(),1000)
    fake.missing=True
    for i in range(15):
        result=s.process(jpeg.tobytes(),2000+100*i)
    assert result['repetitions']==0
    assert result['cancelled']==1
    assert result['phase']=='AGUARDANDO'
    s.close()


def test_index_and_health():
    assert client.get('/').status_code == 200
    assert client.get('/api/health').json()['method']=='regras geométricas'
    assert client.get('/api/sessions/missing/csv').status_code == 404
