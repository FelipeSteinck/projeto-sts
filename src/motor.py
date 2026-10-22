"""Mesma extração, classificação e contagem para web e processamento offline."""
from __future__ import annotations

from .atributos import ExtratorAtributos, FEATURES
from .nucleo import (Calibracao, FaseMovimento, FiltroPosturaEstavel,
                    Postura, RastreadorRepeticoes)


def cancel_discontinuity(tracker):
    if tracker.fase in (FaseMovimento.LEVANTANDO,FaseMovimento.EM_PE,FaseMovimento.SENTANDO):
        tracker.ciclos_cancelados += 1
    tracker.fase = FaseMovimento.AGUARDANDO
    tracker.armado = False
    tracker.inicio_ciclo = None
    tracker.quadros_ausentes = 0


class MotorSTS:
    def __init__(self, alpha=.25, stable_frames=3, calibration=None, model=None):
        self.extractor=ExtratorAtributos(alpha)
        self.calibration=calibration or Calibracao()
        self.model=model
        self.filter=FiltroPosturaEstavel(stable_frames)
        self.rule_filter=FiltroPosturaEstavel(stable_frames)
        self.tracker=RastreadorRepeticoes()
        self.rule_tracker=RastreadorRepeticoes()
        self.last_metrics=None

    def reset(self):
        self.extractor.reset()
        self.filter.reiniciar()
        self.rule_filter.reiniciar()
        self.tracker.reiniciar()
        self.rule_tracker.reiniciar()
        self.last_metrics=None

    def update(self, raw, seconds):
        smooth=None
        features={key:None for key in FEATURES}
        oriented={key:None for key in ('joelho_orientado','quadril_orientado',
            'joelho_normalizado','quadril_normalizado','joelho_continuo','quadril_continuo')}
        posture=stable=rules=rule_stable=Postura.DESCONHECIDA
        confidence=None
        self.last_metrics=None
        if raw is not None:
            smooth,features,oriented,discontinuity=self.extractor.update(raw,seconds)
            if discontinuity:
                self.filter.reiniciar(); self.rule_filter.reiniciar()
                cancel_discontinuity(self.tracker); cancel_discontinuity(self.rule_tracker)
            self.last_metrics=smooth
            rules=self.calibration.classificar(smooth.angulo_joelho,smooth.angulo_quadril)
            posture,confidence=self.model.predict(features) if self.model else (rules,None)
            stable=self.filter.atualizar(posture)
            rule_stable=self.rule_filter.atualizar(rules)
            feedback,event=self.tracker.atualizar(stable,seconds)
            _,rule_event=self.rule_tracker.atualizar(rule_stable,seconds)
        else:
            feedback,event=self.tracker.registrar_ausencia()
            _,rule_event=self.rule_tracker.registrar_ausencia()
            if self.tracker.quadros_ausentes >= 15:
                self.extractor.reset(); self.filter.reiniciar(); self.rule_filter.reiniciar()
        return dict(smooth=smooth,features=features,oriented=oriented,posture=posture,
            stable=stable,rules=rules,rule_stable=rule_stable,feedback=feedback,event=event,
            rule_event=rule_event,confidence=confidence)
