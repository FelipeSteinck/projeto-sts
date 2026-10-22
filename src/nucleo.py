"""Nucleo independente de camera do monitor sentar-e-levantar.

Este modulo concentra a geometria, a calibracao, a filtragem temporal,
a maquina de estados e o registro da sessao. Ele nao importa OpenCV nem
MediaPipe, o que permite testar a logica sem webcam.
"""

from __future__ import annotations

import csv
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CAMINHO_CALIBRACAO = RAIZ_PROJETO / "data" / "calibracao_sts.json"
PASTA_SESSOES = RAIZ_PROJETO / "outputs" / "sessoes"

QUADROS_ESTAVEIS = 3
QUADROS_PERDIDOS_PARA_CANCELAR = 15
ALFA_EMA = 0.25


class Postura(str, Enum):
    DESCONHECIDA = "DESCONHECIDA"
    SENTADO = "SENTADO"
    TRANSICAO = "TRANSIÇÃO"
    EM_PE = "EM PÉ"


class FaseMovimento(str, Enum):
    AGUARDANDO = "AGUARDANDO"
    PRONTO = "PRONTO"
    LEVANTANDO = "LEVANTANDO"
    EM_PE = "EM PÉ"
    SENTANDO = "SENTANDO"


@dataclass
class MetricasCorpo:
    lado: str
    visibilidade: float
    angulo_joelho: float
    angulo_quadril: float
    inclinacao_tronco: float
    pontos: dict[str, tuple[int, int]]


@dataclass
class Calibracao:
    """Extremos pessoais usados somente para separar as fases do movimento."""

    joelho_sentado: float = 95.0
    quadril_sentado: float = 95.0
    joelho_em_pe: float = 170.0
    quadril_em_pe: float = 170.0
    origem: str = "padrao_ilustrativo"

    @property
    def limite_joelho_sentado(self) -> float:
        return self.joelho_sentado + 0.45 * (
            self.joelho_em_pe - self.joelho_sentado
        )

    @property
    def limite_quadril_sentado(self) -> float:
        return self.quadril_sentado + 0.45 * (
            self.quadril_em_pe - self.quadril_sentado
        )

    @property
    def limite_joelho_em_pe(self) -> float:
        return self.joelho_sentado + 0.75 * (
            self.joelho_em_pe - self.joelho_sentado
        )

    @property
    def limite_quadril_em_pe(self) -> float:
        return self.quadril_sentado + 0.75 * (
            self.quadril_em_pe - self.quadril_sentado
        )

    @property
    def esta_calibrada(self) -> bool:
        return self.origem != "padrao_ilustrativo"

    def valida(self) -> bool:
        amplitude_joelho = self.joelho_em_pe - self.joelho_sentado
        amplitude_quadril = self.quadril_em_pe - self.quadril_sentado
        return amplitude_joelho >= 20.0 and amplitude_quadril >= 20.0

    def classificar(self, angulo_joelho: float, angulo_quadril: float) -> Postura:
        sentado = (
            angulo_joelho <= self.limite_joelho_sentado
            and angulo_quadril <= self.limite_quadril_sentado
        )
        em_pe = (
            angulo_joelho >= self.limite_joelho_em_pe
            and angulo_quadril >= self.limite_quadril_em_pe
        )

        if sentado:
            return Postura.SENTADO
        if em_pe:
            return Postura.EM_PE
        return Postura.TRANSICAO

    def salvar(self, caminho: Path = CAMINHO_CALIBRACAO) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        conteudo = {
            "joelho_sentado": self.joelho_sentado,
            "quadril_sentado": self.quadril_sentado,
            "joelho_em_pe": self.joelho_em_pe,
            "quadril_em_pe": self.quadril_em_pe,
            "origem": "calibracao_individual",
            "salvo_em": datetime.now().isoformat(timespec="seconds"),
            "aviso": (
                "Limiares operacionais do algoritmo; nao sao prescricao clinica."
            ),
        }
        caminho.write_text(
            json.dumps(conteudo, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def carregar(cls, caminho: Path = CAMINHO_CALIBRACAO) -> "Calibracao":
        if not caminho.exists():
            return cls()

        try:
            conteudo = json.loads(caminho.read_text(encoding="utf-8"))
            calibracao = cls(
                joelho_sentado=float(conteudo["joelho_sentado"]),
                quadril_sentado=float(conteudo["quadril_sentado"]),
                joelho_em_pe=float(conteudo["joelho_em_pe"]),
                quadril_em_pe=float(conteudo["quadril_em_pe"]),
                origem="calibracao_salva",
            )
            return calibracao if calibracao.valida() else cls()
        except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
            return cls()


class FiltroPosturaEstavel:
    """Aceita uma postura apenas depois de alguns quadros consecutivos."""

    def __init__(self, quadros_necessarios: int = QUADROS_ESTAVEIS) -> None:
        self.quadros_necessarios = quadros_necessarios
        self.candidata = Postura.DESCONHECIDA
        self.contagem_candidata = 0
        self.estavel = Postura.DESCONHECIDA

    def atualizar(self, postura: Postura) -> Postura:
        if postura == self.candidata:
            self.contagem_candidata += 1
        else:
            self.candidata = postura
            self.contagem_candidata = 1

        if self.contagem_candidata >= self.quadros_necessarios:
            self.estavel = self.candidata
        return self.estavel

    def reiniciar(self) -> None:
        self.candidata = Postura.DESCONHECIDA
        self.contagem_candidata = 0
        self.estavel = Postura.DESCONHECIDA


class SuavizadorMetricas:
    """Media movel exponencial para reduzir a oscilacao dos angulos."""

    def __init__(self, alfa: float = ALFA_EMA) -> None:
        self.alfa = alfa
        self.valores: dict[str, float] = {}

    def _atualizar_valor(self, nome: str, valor: float) -> float:
        if nome not in self.valores:
            self.valores[nome] = valor
        else:
            self.valores[nome] = (
                self.alfa * valor + (1.0 - self.alfa) * self.valores[nome]
            )
        return self.valores[nome]

    def atualizar(self, metricas: MetricasCorpo) -> MetricasCorpo:
        return MetricasCorpo(
            lado=metricas.lado,
            visibilidade=metricas.visibilidade,
            angulo_joelho=self._atualizar_valor(
                "joelho", metricas.angulo_joelho
            ),
            angulo_quadril=self._atualizar_valor(
                "quadril", metricas.angulo_quadril
            ),
            inclinacao_tronco=self._atualizar_valor(
                "tronco", metricas.inclinacao_tronco
            ),
            pontos=metricas.pontos,
        )

    def reiniciar(self) -> None:
        self.valores.clear()


class RastreadorRepeticoes:
    """Maquina de estados do ciclo sentado -> em pe -> sentado."""

    def __init__(self) -> None:
        self.reiniciar()

    def reiniciar(self) -> None:
        self.fase = FaseMovimento.AGUARDANDO
        self.armado = False
        self.repeticoes = 0
        self.tentativas_incompletas = 0
        self.ciclos_cancelados = 0
        self.inicio_ciclo: float | None = None
        self.duracao_ultima_repeticao: float | None = None
        self.quadros_ausentes = 0

    @property
    def progresso(self) -> float:
        return {
            FaseMovimento.AGUARDANDO: 0.00,
            FaseMovimento.PRONTO: 0.05,
            FaseMovimento.LEVANTANDO: 0.35,
            FaseMovimento.EM_PE: 0.65,
            FaseMovimento.SENTANDO: 0.85,
        }[self.fase]

    def atualizar(self, postura: Postura, agora: float) -> tuple[str, str]:
        self.quadros_ausentes = 0
        evento = ""

        if self.fase in (FaseMovimento.AGUARDANDO, FaseMovimento.PRONTO):
            if postura == Postura.SENTADO:
                self.fase = FaseMovimento.PRONTO
                self.armado = True
                return "Pronto. Inicie o movimento.", evento

            if not self.armado:
                self.fase = FaseMovimento.AGUARDANDO
                return "Sente-se para iniciar o ciclo.", evento

            if postura == Postura.TRANSICAO:
                self.fase = FaseMovimento.LEVANTANDO
                self.inicio_ciclo = agora
                return "Movimento de subida detectado.", "inicio_subida"

            if postura == Postura.EM_PE:
                self.fase = FaseMovimento.EM_PE
                self.inicio_ciclo = agora
                return "Em pé. Agora retorne com controle.", "em_pe_detectado"

        elif self.fase == FaseMovimento.LEVANTANDO:
            if postura == Postura.EM_PE:
                self.fase = FaseMovimento.EM_PE
                return "Em pé. Agora retorne com controle.", "em_pe_detectado"
            if postura == Postura.SENTADO:
                self.tentativas_incompletas += 1
                self.fase = FaseMovimento.PRONTO
                self.armado = True
                self.inicio_ciclo = None
                return (
                    "Tentativa incompleta: posição em pé não foi detectada.",
                    "tentativa_incompleta",
                )
            return "Movimento de subida em andamento.", evento

        elif self.fase == FaseMovimento.EM_PE:
            if postura == Postura.TRANSICAO:
                self.fase = FaseMovimento.SENTANDO
                return "Movimento de descida detectado.", "inicio_descida"
            if postura == Postura.SENTADO:
                return self._concluir(agora)
            return "Em pé. Agora retorne com controle.", evento

        elif self.fase == FaseMovimento.SENTANDO:
            if postura == Postura.SENTADO:
                return self._concluir(agora)
            if postura == Postura.EM_PE:
                self.fase = FaseMovimento.EM_PE
                return "Em pé. Agora retorne com controle.", evento
            return "Movimento de descida em andamento.", evento

        return "Movimento em andamento.", evento

    def _concluir(self, agora: float) -> tuple[str, str]:
        self.repeticoes += 1
        self.duracao_ultima_repeticao = (
            agora - self.inicio_ciclo if self.inicio_ciclo is not None else None
        )
        self.fase = FaseMovimento.PRONTO
        self.armado = True
        self.inicio_ciclo = None

        if self.duracao_ultima_repeticao is None:
            mensagem = f"Repetição {self.repeticoes} concluída."
        else:
            mensagem = (
                f"Repetição {self.repeticoes} concluída em "
                f"{self.duracao_ultima_repeticao:.1f} s."
            )
        return mensagem, "repeticao_concluida"

    def registrar_ausencia(self) -> tuple[str, str]:
        self.quadros_ausentes += 1

        if (
            self.quadros_ausentes >= QUADROS_PERDIDOS_PARA_CANCELAR
            and self.fase
            in (
                FaseMovimento.LEVANTANDO,
                FaseMovimento.EM_PE,
                FaseMovimento.SENTANDO,
            )
        ):
            self.ciclos_cancelados += 1
            self.fase = FaseMovimento.AGUARDANDO
            self.armado = False
            self.inicio_ciclo = None
            return "Ciclo cancelado: rastreamento perdido.", "ciclo_cancelado"

        return "Enquadre ombro, quadril, joelho e tornozelo.", ""


class RegistroSessao:
    """Salva somente dados numericos em CSV compativel com Excel em pt-BR."""

    CAMPOS = (
        "instante",
        "tempo_decorrido_s",
        "quadro",
        "qualidade_pose",
        "lado_rastreado",
        "visibilidade",
        "postura_bruta",
        "postura_estavel",
        "fase_movimento",
        "angulo_joelho_graus",
        "angulo_quadril_graus",
        "inclinacao_tronco_graus",
        "repeticoes",
        "tentativas_incompletas",
        "ciclos_cancelados",
        "duracao_ultima_repeticao_s",
        "evento",
    )

    def __init__(self, habilitado: bool = True) -> None:
        self.habilitado = habilitado
        self.arquivo: Any = None
        self.escritor: csv.DictWriter | None = None
        self.caminho: Path | None = None
        self.inicio = time.monotonic()
        self.linhas_desde_flush = 0

        if habilitado:
            PASTA_SESSOES.mkdir(parents=True, exist_ok=True)
            marca = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.caminho = PASTA_SESSOES / f"sessao_sentar_levantar_{marca}.csv"
            self.arquivo = self.caminho.open(
                "w", newline="", encoding="utf-8-sig"
            )
            self.escritor = csv.DictWriter(
                self.arquivo,
                fieldnames=self.CAMPOS,
                delimiter=";",
            )
            self.escritor.writeheader()

    @staticmethod
    def _numero(valor: float | None, casas: int) -> str:
        if valor is None:
            return ""
        return f"{valor:.{casas}f}".replace(".", ",")

    def escrever(
        self,
        numero_quadro: int,
        qualidade: str,
        postura_bruta: Postura,
        postura_estavel: Postura,
        rastreador: RastreadorRepeticoes,
        metricas: MetricasCorpo | None,
        evento: str,
    ) -> None:
        if not self.habilitado or self.escritor is None:
            return

        linha = {
            "instante": datetime.now().isoformat(timespec="milliseconds"),
            "tempo_decorrido_s": self._numero(
                time.monotonic() - self.inicio, 3
            ),
            "quadro": numero_quadro,
            "qualidade_pose": qualidade,
            "lado_rastreado": metricas.lado if metricas else "",
            "visibilidade": self._numero(
                metricas.visibilidade if metricas else None, 3
            ),
            "postura_bruta": postura_bruta.value,
            "postura_estavel": postura_estavel.value,
            "fase_movimento": rastreador.fase.value,
            "angulo_joelho_graus": self._numero(
                metricas.angulo_joelho if metricas else None, 2
            ),
            "angulo_quadril_graus": self._numero(
                metricas.angulo_quadril if metricas else None, 2
            ),
            "inclinacao_tronco_graus": self._numero(
                metricas.inclinacao_tronco if metricas else None, 2
            ),
            "repeticoes": rastreador.repeticoes,
            "tentativas_incompletas": rastreador.tentativas_incompletas,
            "ciclos_cancelados": rastreador.ciclos_cancelados,
            "duracao_ultima_repeticao_s": self._numero(
                rastreador.duracao_ultima_repeticao, 3
            ),
            "evento": evento,
        }
        self.escritor.writerow(linha)
        self.linhas_desde_flush += 1

        if self.linhas_desde_flush >= 30 or evento:
            self.arquivo.flush()
            self.linhas_desde_flush = 0

    def fechar(self) -> None:
        if self.arquivo is not None:
            self.arquivo.flush()
            self.arquivo.close()


def calcular_angulo(
    ponto_a: tuple[float, float],
    vertice: tuple[float, float],
    ponto_c: tuple[float, float],
) -> float:
    """Retorna o menor angulo A-vertice-C no intervalo [0, 180]."""

    vetor_a = (ponto_a[0] - vertice[0], ponto_a[1] - vertice[1])
    vetor_c = (ponto_c[0] - vertice[0], ponto_c[1] - vertice[1])
    norma_a = math.hypot(*vetor_a)
    norma_c = math.hypot(*vetor_c)

    if norma_a == 0.0 or norma_c == 0.0:
        raise ValueError("Nao e possivel calcular angulo com vetor nulo.")

    produto_escalar = vetor_a[0] * vetor_c[0] + vetor_a[1] * vetor_c[1]
    produto_vetorial = vetor_a[0] * vetor_c[1] - vetor_a[1] * vetor_c[0]
    return abs(math.degrees(math.atan2(produto_vetorial, produto_escalar)))


def calcular_inclinacao_tronco(
    ombro: tuple[float, float],
    quadril: tuple[float, float],
) -> float:
    """Calcula a inclinacao absoluta do tronco em relacao a vertical."""

    vetor_tronco = (ombro[0] - quadril[0], ombro[1] - quadril[1])
    return calcular_angulo(
        (quadril[0] + vetor_tronco[0], quadril[1] + vetor_tronco[1]),
        quadril,
        (quadril[0], quadril[1] - 1.0),
    )


def finalizar_calibracao(
    sentado: tuple[float, float] | None,
    em_pe: tuple[float, float] | None,
) -> Calibracao | None:
    if sentado is None or em_pe is None:
        return None

    calibracao = Calibracao(
        joelho_sentado=sentado[0],
        quadril_sentado=sentado[1],
        joelho_em_pe=em_pe[0],
        quadril_em_pe=em_pe[1],
        origem="calibracao_individual",
    )
    return calibracao if calibracao.valida() else None
