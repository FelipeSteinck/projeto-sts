"""Inferência de modelos próprios em JSON. Não desserializa pickle/joblib."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .atributos import FEATURES, SCHEMA
from .nucleo import Postura

CLASSES = (Postura.SENTADO.value, Postura.TRANSICAO.value, Postura.EM_PE.value)
METHODS = {'logistica':'Regressão Logística', 'floresta':'Floresta Aleatória'}


class ModeloSTS:
    def __init__(self, artifact):
        self.artifact = artifact
        if artifact.get('schema') != SCHEMA or artifact.get('features') != list(FEATURES):
            raise ValueError('Modelo e atributos incompatíveis.')
        if set(artifact['classes']) != set(CLASSES):
            raise ValueError('O modelo precisa das três classes STS.')
        if artifact['metodo'] not in METHODS or artifact['tipo_dados'] not in ('real','sintetico'):
            raise ValueError('Metadados do modelo inválidos.')
        self.classes = artifact['classes']

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))

    def predict(self, features):
        x = np.asarray([features[k] for k in FEATURES],dtype=float)
        if not np.isfinite(x).all():
            raise ValueError('Atributos inválidos para predição.')
        model = self.artifact['model']
        if self.artifact['metodo'] == 'logistica':
            z = (x - np.asarray(model['mean'])) / np.asarray(model['scale'])
            scores = np.asarray(model['coef']) @ z + np.asarray(model['intercept'])
            scores = np.exp(scores-scores.max())
            scores /= scores.sum()
        else:
            # scikit-learn converte a entrada das árvores para float32.
            x = x.astype(np.float32)
            scores = np.zeros(len(self.classes))
            for tree in model['trees']:
                node = 0
                while tree['left'][node] != -1:
                    node = tree['left'][node] if x[tree['feature'][node]] <= tree['threshold'][node] else tree['right'][node]
                votes = np.asarray(tree['value'][node],dtype=float)
                scores += votes / votes.sum()
            scores /= len(model['trees'])
        index = int(np.argmax(scores))
        return Postura(self.classes[index]), float(scores[index])


def export_model(estimator, method, metadata):
    """Exporta apenas parâmetros numéricos para inferência portátil."""
    artifact = dict(metadata, schema=SCHEMA, features=list(FEATURES), metodo=method)
    if method == 'logistica':
        scale, classifier = estimator.named_steps['scale'], estimator.named_steps['classifier']
        artifact['model'] = dict(mean=scale.mean_.tolist(),scale=scale.scale_.tolist(),
            coef=classifier.coef_.tolist(),intercept=classifier.intercept_.tolist())
    else:
        classifier = estimator
        artifact['model'] = {'trees':[dict(left=e.tree_.children_left.tolist(),
            right=e.tree_.children_right.tolist(),feature=e.tree_.feature.tolist(),
            threshold=e.tree_.threshold.tolist(),value=e.tree_.value[:,0,:].tolist())
            for e in classifier.estimators_]}
    artifact['classes'] = classifier.classes_.tolist()
    return artifact


def model_catalog(root):
    result=[]
    for model_set,kind in (('sts','real'),('demo','sintetico')):
        for method,label in METHODS.items():
            path=Path(root)/model_set/f'{method}.json'
            if not path.exists():
                continue
            model=ModeloSTS.load(path)
            if model.artifact['tipo_dados'] != kind:
                raise ValueError('Tipo de dados incompatível com o diretório do modelo.')
            result.append(dict(id=f'{model_set}/{method}',name=label,
                data_kind=kind,alpha=model.artifact['alpha'],
                stable_frames=model.artifact['stable_frames']))
    return result
