"""Interface grafica em portugues renderizada com Pillow."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .nucleo import Calibracao, FaseMovimento, MetricasCorpo, RastreadorRepeticoes


@dataclass(frozen=True)
class Tema:
    fundo: tuple[int, int, int] = (12, 18, 28)
    painel: tuple[int, int, int] = (20, 29, 43)
    painel_claro: tuple[int, int, int] = (29, 41, 59)
    borda: tuple[int, int, int] = (54, 70, 92)
    texto: tuple[int, int, int] = (239, 244, 250)
    texto_secundario: tuple[int, int, int] = (157, 172, 194)
    azul: tuple[int, int, int] = (57, 189, 248)
    verde: tuple[int, int, int] = (52, 211, 153)
    amarelo: tuple[int, int, int] = (251, 191, 36)
    laranja: tuple[int, int, int] = (251, 146, 60)
    vermelho: tuple[int, int, int] = (248, 113, 113)


class Fontes:
    def __init__(self) -> None:
        self.regular = self._localizar(
            (
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            )
        )
        self.negrito = self._localizar(
            (
                "C:/Windows/Fonts/seguisb.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            )
        )
        self._cache: dict[tuple[str, int], Any] = {}

    @staticmethod
    def _localizar(candidatos: tuple[str, ...]) -> str | None:
        for candidato in candidatos:
            if Path(candidato).exists():
                return candidato
        return None

    def obter(self, tamanho: int, negrito: bool = False) -> Any:
        chave = ("b" if negrito else "r", tamanho)
        if chave not in self._cache:
            caminho = self.negrito if negrito else self.regular
            self._cache[chave] = (
                ImageFont.truetype(caminho, tamanho)
                if caminho
                else ImageFont.load_default()
            )
        return self._cache[chave]


class InterfaceMonitor:
    """Compoe video e painel lateral em uma unica janela escalavel."""

    def __init__(self, largura: int = 1280, altura: int = 720) -> None:
        if largura < 1050 or altura < 700:
            raise ValueError("A interface requer no minimo 1050 x 700 pixels.")
        self.largura = largura
        self.altura = altura
        self.tema = Tema()
        self.fontes = Fontes()

    def _texto(
        self,
        desenho: ImageDraw.ImageDraw,
        xy: tuple[int, int],
        texto: str,
        tamanho: int,
        cor: tuple[int, int, int] | None = None,
        negrito: bool = False,
        ancora: str | None = None,
    ) -> None:
        desenho.text(
            xy,
            texto,
            font=self.fontes.obter(tamanho, negrito),
            fill=cor or self.tema.texto,
            anchor=ancora,
        )

    def _cartao(
        self,
        desenho: ImageDraw.ImageDraw,
        caixa: tuple[int, int, int, int],
        preenchimento: tuple[int, int, int] | None = None,
        raio: int = 14,
    ) -> None:
        desenho.rounded_rectangle(
            caixa,
            radius=raio,
            fill=preenchimento or self.tema.painel,
            outline=self.tema.borda,
            width=1,
        )

    @staticmethod
    def _cor_fase(fase: FaseMovimento, tema: Tema) -> tuple[int, int, int]:
        return {
            FaseMovimento.AGUARDANDO: tema.texto_secundario,
            FaseMovimento.PRONTO: tema.azul,
            FaseMovimento.LEVANTANDO: tema.amarelo,
            FaseMovimento.EM_PE: tema.verde,
            FaseMovimento.SENTANDO: tema.laranja,
        }[fase]

    def _preparar_video(
        self,
        quadro_bgr: np.ndarray | None,
        tamanho: tuple[int, int],
    ) -> Image.Image:
        largura, altura = tamanho
        if quadro_bgr is None:
            imagem = Image.new("RGB", tamanho, (9, 14, 22))
            desenho = ImageDraw.Draw(imagem)
            for y in range(altura):
                tom = int(14 + 18 * y / max(1, altura - 1))
                desenho.line((0, y, largura, y), fill=(9, tom, tom + 8))
            self._desenhar_silhueta(desenho, largura, altura)
            return imagem

        rgb = np.ascontiguousarray(quadro_bgr[:, :, ::-1])
        origem = Image.fromarray(rgb)
        escala = min(largura / origem.width, altura / origem.height)
        novo = (
            max(1, int(origem.width * escala)),
            max(1, int(origem.height * escala)),
        )
        origem = origem.resize(novo, Image.Resampling.LANCZOS)
        destino = Image.new("RGB", tamanho, (5, 9, 15))
        destino.paste(origem, ((largura - novo[0]) // 2, (altura - novo[1]) // 2))
        return destino

    def _desenhar_silhueta(
        self, desenho: ImageDraw.ImageDraw, largura: int, altura: int
    ) -> None:
        cx = int(largura * 0.50)
        cor = (54, 211, 153)
        sombra = (22, 101, 84)
        pontos = {
            "cabeca": (cx, int(altura * 0.17)),
            "ombro": (cx - 18, int(altura * 0.29)),
            "quadril": (cx + 18, int(altura * 0.49)),
            "joelho": (cx + 85, int(altura * 0.62)),
            "tornozelo": (cx + 42, int(altura * 0.82)),
        }
        desenho.ellipse(
            (
                pontos["cabeca"][0] - 22,
                pontos["cabeca"][1] - 22,
                pontos["cabeca"][0] + 22,
                pontos["cabeca"][1] + 22,
            ),
            outline=cor,
            width=5,
        )
        cadeia = ("ombro", "quadril", "joelho", "tornozelo")
        for inicio, fim in zip(cadeia, cadeia[1:]):
            desenho.line((pontos[inicio], pontos[fim]), fill=sombra, width=10)
            desenho.line((pontos[inicio], pontos[fim]), fill=cor, width=4)
        for ponto in cadeia:
            x, y = pontos[ponto]
            desenho.ellipse((x - 8, y - 8, x + 8, y + 8), fill=cor)

    def renderizar(
        self,
        quadro_bgr: np.ndarray | None,
        qualidade: str,
        rastreador: RastreadorRepeticoes,
        metricas: MetricasCorpo | None,
        mensagem: str,
        fps: float,
        calibracao: Calibracao,
        sentado_pendente: tuple[float, float] | None,
        em_pe_pendente: tuple[float, float] | None,
        pausado: bool = False,
        espelhado: bool = True,
        landmarks_visiveis: bool = True,
    ) -> np.ndarray:
        t = self.tema
        tela = Image.new("RGB", (self.largura, self.altura), t.fundo)
        desenho = ImageDraw.Draw(tela)

        margem = 18
        rodape_h = 46
        espaco = 16
        conteudo_h = self.altura - 2 * margem - rodape_h - 10
        video_w = int(self.largura * 0.65)
        painel_x = margem + video_w + espaco
        painel_w = self.largura - painel_x - margem

        video = self._preparar_video(quadro_bgr, (video_w, conteudo_h))
        tela.paste(video, (margem, margem))
        desenho.rounded_rectangle(
            (margem, margem, margem + video_w, margem + conteudo_h),
            radius=16,
            outline=t.borda,
            width=2,
        )

        # Cabecalho sobre o video.
        desenho.rounded_rectangle(
            (margem + 12, margem + 12, margem + video_w - 12, margem + 72),
            radius=12,
            fill=(9, 16, 26),
        )
        self._texto(
            desenho,
            (margem + 30, margem + 25),
            "MONITOR DE SENTAR E LEVANTAR",
            21,
            negrito=True,
        )
        self._texto(
            desenho,
            (margem + 30, margem + 50),
            "Protótipo acadêmico - não clínico",
            13,
            t.texto_secundario,
        )

        cor_qualidade = (
            t.verde
            if qualidade == "POSTURA COMPLETA"
            else t.amarelo
            if qualidade == "POSTURA PARCIAL"
            else t.vermelho
        )
        largura_selo = 196
        desenho.rounded_rectangle(
            (
                margem + video_w - largura_selo - 28,
                margem + 27,
                margem + video_w - 28,
                margem + 57,
            ),
            radius=15,
            fill=tuple(max(0, c // 4) for c in cor_qualidade),
            outline=cor_qualidade,
            width=1,
        )
        self._texto(
            desenho,
            (margem + video_w - largura_selo / 2 - 28, margem + 42),
            qualidade,
            12,
            cor_qualidade,
            negrito=True,
            ancora="mm",
        )

        if pausado:
            desenho.rounded_rectangle(
                (
                    margem + video_w // 2 - 105,
                    margem + conteudo_h // 2 - 40,
                    margem + video_w // 2 + 105,
                    margem + conteudo_h // 2 + 40,
                ),
                radius=16,
                fill=(10, 18, 29),
                outline=t.amarelo,
                width=2,
            )
            self._texto(
                desenho,
                (margem + video_w // 2, margem + conteudo_h // 2),
                "ANÁLISE PAUSADA",
                22,
                t.amarelo,
                negrito=True,
                ancora="mm",
            )

        # Painel lateral.
        self._cartao(
            desenho,
            (painel_x, margem, painel_x + painel_w, margem + conteudo_h),
        )
        x = painel_x + 18
        largura_interna = painel_w - 36
        cor_fase = self._cor_fase(rastreador.fase, t)

        self._texto(desenho, (x, margem + 17), "ESTADO ATUAL", 12, t.texto_secundario)
        desenho.rounded_rectangle(
            (x, margem + 38, x + largura_interna, margem + 82),
            radius=12,
            fill=tuple(max(0, c // 5) for c in cor_fase),
            outline=cor_fase,
            width=1,
        )
        self._texto(
            desenho,
            (x + largura_interna // 2, margem + 60),
            rastreador.fase.value,
            21,
            cor_fase,
            negrito=True,
            ancora="mm",
        )

        y_rep = margem + 94
        self._cartao(
            desenho,
            (x, y_rep, x + largura_interna, y_rep + 112),
            t.painel_claro,
        )
        self._texto(desenho, (x + 16, y_rep + 13), "REPETIÇÕES", 12, t.texto_secundario)
        self._texto(
            desenho,
            (x + 22, y_rep + 48),
            str(rastreador.repeticoes),
            50,
            t.azul,
            negrito=True,
        )
        self._texto(
            desenho,
            (x + 126, y_rep + 49),
            f"Incompletas  {rastreador.tentativas_incompletas}",
            14,
            t.texto,
        )
        duracao = rastreador.duracao_ultima_repeticao
        duracao_texto = "--" if duracao is None else f"{duracao:.1f} s"
        self._texto(
            desenho,
            (x + 126, y_rep + 76),
            f"Última duração  {duracao_texto}",
            13,
            t.texto_secundario,
        )

        y_prog = y_rep + 126
        self._texto(desenho, (x, y_prog), "PROGRESSO DO CICLO", 12, t.texto_secundario)
        trilho_y = y_prog + 31
        desenho.rounded_rectangle(
            (x, trilho_y, x + largura_interna, trilho_y + 10),
            radius=5,
            fill=(42, 54, 72),
        )
        desenho.rounded_rectangle(
            (
                x,
                trilho_y,
                x + max(10, int(largura_interna * rastreador.progresso)),
                trilho_y + 10,
            ),
            radius=5,
            fill=cor_fase,
        )
        self._texto(desenho, (x, trilho_y + 17), "sentado", 11, t.texto_secundario)
        self._texto(
            desenho,
            (x + largura_interna // 2, trilho_y + 17),
            "em pé",
            11,
            t.texto_secundario,
            ancora="ma",
        )
        self._texto(
            desenho,
            (x + largura_interna, trilho_y + 17),
            "sentado",
            11,
            t.texto_secundario,
            ancora="ra",
        )

        y_met = y_prog + 76
        self._texto(desenho, (x, y_met), "MEDIDAS EM TEMPO REAL", 12, t.texto_secundario)
        valores = (
            ("Joelho", None if metricas is None else metricas.angulo_joelho),
            ("Quadril", None if metricas is None else metricas.angulo_quadril),
            ("Tronco", None if metricas is None else metricas.inclinacao_tronco),
        )
        largura_metrica = (largura_interna - 16) // 3
        for indice, (rotulo, valor) in enumerate(valores):
            mx = x + indice * (largura_metrica + 8)
            self._cartao(
                desenho,
                (mx, y_met + 23, mx + largura_metrica, y_met + 94),
                t.painel_claro,
                10,
            )
            self._texto(desenho, (mx + 10, y_met + 33), rotulo, 11, t.texto_secundario)
            exibido = "--" if valor is None else f"{valor:.1f}°"
            self._texto(
                desenho,
                (mx + largura_metrica // 2, y_met + 68),
                exibido,
                18,
                t.texto,
                negrito=True,
                ancora="mm",
            )

        y_info = y_met + 107
        lado = "--" if metricas is None else metricas.lado.capitalize()
        visibilidade = "--" if metricas is None else f"{metricas.visibilidade * 100:.0f}%"
        self._texto(
            desenho,
            (x, y_info),
            f"Lado rastreado: {lado}",
            12,
            t.texto_secundario,
        )
        self._texto(
            desenho,
            (x + largura_interna, y_info),
            f"Visibilidade: {visibilidade}",
            12,
            t.texto_secundario,
            ancora="ra",
        )

        y_cal = y_info + 28
        status_cal = "CALIBRADO" if calibracao.esta_calibrada else "CALIBRAÇÃO PENDENTE"
        cor_cal = t.verde if calibracao.esta_calibrada else t.amarelo
        self._cartao(
            desenho,
            (x, y_cal, x + largura_interna, y_cal + 66),
            t.painel_claro,
            10,
        )
        self._texto(desenho, (x + 12, y_cal + 10), status_cal, 11, cor_cal, negrito=True)
        sent_ok = "✓" if sentado_pendente is not None else "1"
        pe_ok = "✓" if em_pe_pendente is not None else "2"
        self._texto(
            desenho,
            (x + 12, y_cal + 36),
            f"{sent_ok}  Registrar sentado",
            12,
            t.texto,
        )
        self._texto(
            desenho,
            (x + largura_interna - 12, y_cal + 36),
            f"{pe_ok}  Registrar em pé",
            12,
            t.texto,
            ancora="ra",
        )

        y_feedback = y_cal + 78
        altura_feedback = margem + conteudo_h - y_feedback - 14
        self._cartao(
            desenho,
            (x, y_feedback, x + largura_interna, y_feedback + altura_feedback),
            (18, 48, 59),
            10,
        )
        self._texto(desenho, (x + 12, y_feedback + 10), "ORIENTAÇÃO", 11, t.azul, negrito=True)
        largura_aprox = max(28, largura_interna // 8)
        linhas = textwrap.wrap(mensagem, width=largura_aprox)[:3]
        for indice, linha in enumerate(linhas):
            self._texto(
                desenho,
                (x + 12, y_feedback + 32 + 18 * indice),
                linha,
                13,
                t.texto,
                negrito=indice == 0,
            )

        # Rodape de comandos.
        y_rodape = margem + conteudo_h + 10
        self._cartao(
            desenho,
            (margem, y_rodape, self.largura - margem, self.altura - margem),
            (15, 23, 35),
            11,
        )
        controles = "1 Sentado   2 Em pé   P Pausar   R Reiniciar   M Espelho   L Esqueleto   Q Sair"
        self._texto(
            desenho,
            (margem + 16, y_rodape + 15),
            controles,
            12,
            t.texto_secundario,
        )
        indicadores = (
            f"FPS {fps:.1f}  |  Espelho {'sim' if espelhado else 'não'}"
            f"  |  Esqueleto {'sim' if landmarks_visiveis else 'não'}"
        )
        self._texto(
            desenho,
            (self.largura - margem - 16, y_rodape + 15),
            indicadores,
            11,
            t.texto_secundario,
            ancora="ra",
        )

        rgb = np.asarray(tela)
        return np.ascontiguousarray(rgb[:, :, ::-1])


def gerar_demonstracao_interface(caminho: Path) -> Path:
    """Gera uma pre-visualizacao da interface sem camera nem MediaPipe."""

    rastreador = RastreadorRepeticoes()
    rastreador.fase = FaseMovimento.LEVANTANDO
    rastreador.armado = True
    rastreador.repeticoes = 3
    rastreador.tentativas_incompletas = 1
    rastreador.duracao_ultima_repeticao = 4.2
    metricas = MetricasCorpo(
        lado="direito",
        visibilidade=0.93,
        angulo_joelho=131.4,
        angulo_quadril=124.8,
        inclinacao_tronco=16.2,
        pontos={},
    )
    interface = InterfaceMonitor()
    bgr = interface.renderizar(
        quadro_bgr=None,
        qualidade="POSTURA COMPLETA",
        rastreador=rastreador,
        metricas=metricas,
        mensagem="Movimento de subida detectado. Continue até a posição em pé.",
        fps=28.7,
        calibracao=Calibracao(origem="calibracao_salva"),
        sentado_pendente=None,
        em_pe_pendente=None,
    )
    caminho.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(bgr[:, :, ::-1]).save(caminho)
    return caminho
