"""Atributos causais compartilhados pela aplicação e pelos experimentos offline."""
from __future__ import annotations

import math

from .nucleo import MetricasCorpo, SuavizadorMetricas

SCHEMA = 'sts-atributos-v1'
FEATURES = ('joelho_ema', 'quadril_ema', 'tronco_ema', 'altura_quadril_rel',
            'vel_joelho', 'vel_quadril', 'vel_altura')
POINTS = ('ombro', 'quadril', 'joelho', 'tornozelo')
MAX_GAP_S = 1.0


def signed_angle(a, b, c):
    """Graus em coordenadas de imagem, com y crescente para baixo."""
    u, v = (a[0]-b[0], a[1]-b[1]), (c[0]-b[0], c[1]-b[1])
    if math.hypot(*u) == 0 or math.hypot(*v) == 0:
        raise ValueError('Vetor nulo')
    return math.degrees(math.atan2(u[0]*v[1]-u[1]*v[0], u[0]*v[0]+u[1]*v[1]))


class SerieOrientada:
    """Convenção por cadeia: primeira flexão inequívoca positiva; continuidade causal.

    Não é convenção anatômica de rotação. Em extensão quase reta não há âncora
    confiável; exporta None até observar 10 < |ângulo| < 170 graus. A reflexão
    muda o sinal bruto e a âncora, preservando a série normalizada. Trocar de
    lado exige nova série. Esses canais não entram no classificador v1.
    """
    def __init__(self):
        self.sign = None
        self.previous = None
        self.continuous = None

    def update(self, value):
        if self.sign is None:
            if not 10 < abs(value) < 170:
                return None, None
            self.sign = 1 if value > 0 else -1
        normalized = value * self.sign
        if self.previous is None:
            self.continuous = normalized
        else:
            delta = (normalized - self.previous + 180) % 360 - 180
            self.continuous += delta
        self.previous = normalized
        return normalized, self.continuous


class ExtratorAtributos:
    def __init__(self, alpha=0.25):
        if not 0 < alpha <= 1:
            raise ValueError('Alfa fora de (0,1].')
        self.alpha = alpha
        self.reset()

    def reset(self):
        self.smoother = SuavizadorMetricas(self.alpha)
        self.knee = SerieOrientada()
        self.hip = SerieOrientada()
        self.previous = None
        self.height = None
        self.side = None
        self.last_time = None

    def update(self, raw: MetricasCorpo, seconds: float):
        if not math.isfinite(seconds) or (self.last_time is not None and seconds <= self.last_time):
            raise ValueError('Tempo deve crescer estritamente.')
        discontinuity = self.side is not None and (
            self.side != raw.lado or seconds - self.last_time > MAX_GAP_S)
        if discontinuity:
            self.reset()
        p = raw.pontos
        length = math.dist(p['quadril'], p['joelho']) + math.dist(p['joelho'], p['tornozelo'])
        if length <= 0:
            raise ValueError('Comprimento de perna nulo.')
        height = (p['tornozelo'][1] - p['quadril'][1]) / length
        self.height = height if self.height is None else self.alpha*height + (1-self.alpha)*self.height
        smooth = self.smoother.atualizar(raw)
        knee = signed_angle(p['quadril'], p['joelho'], p['tornozelo'])
        hip = signed_angle(p['ombro'], p['quadril'], p['joelho'])
        nk, uk = self.knee.update(knee)
        nh, uh = self.hip.update(hip)
        values = (smooth.angulo_joelho, smooth.angulo_quadril, self.height)
        velocity = (0., 0., 0.) if self.previous is None else tuple(
            (a-b)/(seconds-self.last_time) for a,b in zip(values,self.previous))
        features = dict(zip(FEATURES, (values[0], values[1], smooth.inclinacao_tronco,
                                     values[2], *velocity)))
        if not all(math.isfinite(x) for x in features.values()):
            raise ValueError('Atributo não finito.')
        self.previous, self.side, self.last_time = values, raw.lado, seconds
        return smooth, features, dict(joelho_orientado=knee, quadril_orientado=hip,
            joelho_normalizado=nk, quadril_normalizado=nh,
            joelho_continuo=uk, quadril_continuo=uh), discontinuity


def raw_columns(raw):
    values = dict(lado=raw.lado if raw else '', visibilidade=raw.visibilidade if raw else '',
                  joelho_bruto=raw.angulo_joelho if raw else '',
                  quadril_bruto=raw.angulo_quadril if raw else '',
                  tronco_bruto=raw.inclinacao_tronco if raw else '')
    values.update({f'{p}_{axis}': raw.pontos[p][i] if raw else ''
                   for p in POINTS for i,axis in enumerate(('x','y'))})
    return values


def raw_from_row(row):
    if row.get('lado','') == '':
        return None
    def number(key):
        value = float(str(row[key]).replace(',','.'))
        if not math.isfinite(value):
            raise ValueError(f'Valor não finito: {key}')
        return value
    return MetricasCorpo(row['lado'],number('visibilidade'),number('joelho_bruto'),
        number('quadril_bruto'),number('tronco_bruto'),
        {p:(number(f'{p}_x'),number(f'{p}_y')) for p in POINTS})
