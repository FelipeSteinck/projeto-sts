"""Aplicacao de webcam do monitor sentar-e-levantar."""

from __future__ import annotations

import argparse
import math
import time
from pathlib import Path
from typing import Any

from .interface import InterfaceMonitor, gerar_demonstracao_interface
from .nucleo import (
    CAMINHO_CALIBRACAO,
    RAIZ_PROJETO,
    Calibracao,
    FiltroPosturaEstavel,
    MetricasCorpo,
    Postura,
    RastreadorRepeticoes,
    RegistroSessao,
    SuavizadorMetricas,
    calcular_angulo,
    calcular_inclinacao_tronco,
    finalizar_calibracao,
)


CAMINHO_MODELO_PADRAO = RAIZ_PROJETO / "models" / "pose_landmarker_lite.task"
VISIBILIDADE_MINIMA_PADRAO = 0.60

CONEXOES_POSE = (
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (11, 23),
    (12, 24),
    (23, 24),
    (23, 25),
    (25, 27),
    (27, 29),
    (29, 31),
    (27, 31),
    (24, 26),
    (26, 28),
    (28, 30),
    (30, 32),
    (28, 32),
)

LANDMARKS_POR_LADO = {
    "esquerdo": {"ombro": 11, "quadril": 23, "joelho": 25, "tornozelo": 27},
    "direito": {"ombro": 12, "quadril": 24, "joelho": 26, "tornozelo": 28},
}


def confianca_landmark(landmark: Any) -> float:
    visibilidade = getattr(landmark, "visibility", 1.0)
    presenca = getattr(landmark, "presence", 1.0)
    visibilidade = 1.0 if visibilidade is None else float(visibilidade)
    presenca = 1.0 if presenca is None else float(presenca)
    return min(visibilidade, presenca)


def extrair_metricas_corpo(
    landmarks: list[Any],
    largura: int,
    altura: int,
    visibilidade_minima: float,
) -> tuple[MetricasCorpo | None, str, float]:
    candidatos: list[tuple[float, str, dict[str, Any]]] = []

    for lado, indices in LANDMARKS_POR_LADO.items():
        selecionados = {nome: landmarks[indice] for nome, indice in indices.items()}
        confianca = min(confianca_landmark(item) for item in selecionados.values())
        todos_dentro = all(
            0.0 <= item.x <= 1.0 and 0.0 <= item.y <= 1.0
            for item in selecionados.values()
        )
        candidatos.append((confianca if todos_dentro else 0.0, lado, selecionados))

    confianca, lado, selecionados = max(candidatos, key=lambda item: item[0])
    if confianca < visibilidade_minima:
        return None, lado, confianca

    pontos = {
        nome: (int(item.x * largura), int(item.y * altura))
        for nome, item in selecionados.items()
    }
    metricas = MetricasCorpo(
        lado=lado,
        visibilidade=confianca,
        angulo_joelho=calcular_angulo(
            pontos["quadril"], pontos["joelho"], pontos["tornozelo"]
        ),
        angulo_quadril=calcular_angulo(
            pontos["ombro"], pontos["quadril"], pontos["joelho"]
        ),
        inclinacao_tronco=calcular_inclinacao_tronco(
            pontos["ombro"], pontos["quadril"]
        ),
        pontos=pontos,
    )
    return metricas, lado, confianca


def desenhar_pose(cv2: Any, quadro: Any, landmarks: list[Any]) -> None:
    altura, largura = quadro.shape[:2]
    pontos: list[tuple[int, int] | None] = []
    for landmark in landmarks:
        x = int(landmark.x * largura)
        y = int(landmark.y * altura)
        visivel = confianca_landmark(landmark) >= 0.35
        dentro = 0 <= x < largura and 0 <= y < altura
        pontos.append((x, y) if visivel and dentro else None)

    for inicio, fim in CONEXOES_POSE:
        ponto_inicio = pontos[inicio]
        ponto_fim = pontos[fim]
        if ponto_inicio is not None and ponto_fim is not None:
            cv2.line(quadro, ponto_inicio, ponto_fim, (153, 211, 52), 2, cv2.LINE_AA)
    for ponto in pontos:
        if ponto is not None:
            cv2.circle(quadro, ponto, 3, (248, 189, 57), -1, cv2.LINE_AA)


def destacar_lado(cv2: Any, quadro: Any, metricas: MetricasCorpo) -> None:
    cadeia = ("ombro", "quadril", "joelho", "tornozelo")
    for inicio, fim in zip(cadeia, cadeia[1:]):
        cv2.line(
            quadro,
            metricas.pontos[inicio],
            metricas.pontos[fim],
            (248, 189, 57),
            4,
            cv2.LINE_AA,
        )
    for ponto in metricas.pontos.values():
        cv2.circle(quadro, ponto, 6, (153, 211, 52), -1, cv2.LINE_AA)


def abrir_camera(cv2: Any, indice: int, largura: int, altura: int) -> Any:
    captura = cv2.VideoCapture(indice, cv2.CAP_DSHOW)
    if not captura.isOpened():
        captura.release()
        captura = cv2.VideoCapture(indice)
    captura.set(cv2.CAP_PROP_FRAME_WIDTH, largura)
    captura.set(cv2.CAP_PROP_FRAME_HEIGHT, altura)
    return captura


def carregar_dependencias() -> tuple[Any, Any, Any, Any]:
    try:
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError as erro:
        raise RuntimeError(
            "Dependências ausentes. Ative a .venv e execute "
            "'python -m pip install -r requirements.txt'."
        ) from erro
    return cv2, mp, mp_python, vision


def executar_aplicacao(args: argparse.Namespace) -> int:
    cv2, mp, mp_python, vision = carregar_dependencias()
    caminho_modelo = args.modelo.resolve()
    if not caminho_modelo.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado: {caminho_modelo}\n"
            "Copie pose_landmarker_lite.task para a pasta models."
        )

    calibracao = Calibracao.carregar(CAMINHO_CALIBRACAO)
    sentado_pendente: tuple[float, float] | None = None
    em_pe_pendente: tuple[float, float] | None = None

    opcoes = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(caminho_modelo)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    captura = abrir_camera(cv2, args.camera, args.largura_camera, args.altura_camera)
    if not captura.isOpened():
        raise RuntimeError(f"Não foi possível abrir a câmera {args.camera}.")

    suavizador = SuavizadorMetricas()
    filtro_postura = FiltroPosturaEstavel()
    rastreador = RastreadorRepeticoes()
    registro = RegistroSessao(habilitado=not args.sem_registro)
    interface = InterfaceMonitor(args.largura_interface, args.altura_interface)

    instante_anterior = time.perf_counter()
    fps_suavizado = 0.0
    ultimo_timestamp_ms = -1
    numero_quadro = 0
    aviso = "Posicione a câmera de lado e enquadre o corpo inteiro."
    aviso_ate = time.monotonic() + 5.0
    pausado = False
    espelhado = not args.sem_espelho
    landmarks_visiveis = True
    ultimo_estado = {
        "qualidade": "SEM POSTURA",
        "metricas": None,
        "feedback": aviso,
    }

    nome_janela = "Monitor de sentar e levantar"
    cv2.namedWindow(nome_janela, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(nome_janela, args.largura_interface, args.altura_interface)

    try:
        with vision.PoseLandmarker.create_from_options(opcoes) as landmarker:
            while True:
                sucesso, quadro = captura.read()
                if not sucesso or quadro is None:
                    print("Falha ao capturar um quadro da webcam.")
                    break

                if espelhado:
                    quadro = cv2.flip(quadro, 1)

                if not pausado:
                    numero_quadro += 1
                    altura, largura = quadro.shape[:2]
                    rgb = cv2.cvtColor(quadro, cv2.COLOR_BGR2RGB)
                    imagem_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    timestamp_ms = int(time.monotonic() * 1000)
                    timestamp_ms = max(timestamp_ms, ultimo_timestamp_ms + 1)
                    ultimo_timestamp_ms = timestamp_ms
                    resultado = landmarker.detect_for_video(imagem_mp, timestamp_ms)

                    metricas: MetricasCorpo | None = None
                    postura_bruta = Postura.DESCONHECIDA
                    postura_estavel = filtro_postura.estavel
                    evento = ""

                    if resultado.pose_landmarks:
                        landmarks = resultado.pose_landmarks[0]
                        metricas_brutas, _lado, _confianca = extrair_metricas_corpo(
                            landmarks,
                            largura,
                            altura,
                            args.visibilidade_minima,
                        )
                        if landmarks_visiveis:
                            desenhar_pose(cv2, quadro, landmarks)

                        if metricas_brutas is not None:
                            metricas = suavizador.atualizar(metricas_brutas)
                            if landmarks_visiveis:
                                destacar_lado(cv2, quadro, metricas)
                            postura_bruta = calibracao.classificar(
                                metricas.angulo_joelho,
                                metricas.angulo_quadril,
                            )
                            postura_estavel = filtro_postura.atualizar(postura_bruta)
                            feedback, evento = rastreador.atualizar(
                                postura_estavel, time.monotonic()
                            )
                            qualidade = "POSTURA COMPLETA"
                        else:
                            qualidade = "POSTURA PARCIAL"
                            feedback, evento = rastreador.registrar_ausencia()
                    else:
                        qualidade = "SEM POSTURA"
                        feedback, evento = rastreador.registrar_ausencia()

                    if rastreador.quadros_ausentes >= 15:
                        filtro_postura.reiniciar()
                        suavizador.reiniciar()
                        postura_estavel = Postura.DESCONHECIDA

                    if evento in (
                        "repeticao_concluida",
                        "tentativa_incompleta",
                        "ciclo_cancelado",
                    ):
                        aviso = feedback
                        aviso_ate = time.monotonic() + 2.8

                    mensagem_exibida = aviso if time.monotonic() < aviso_ate else feedback
                    registro.escrever(
                        numero_quadro,
                        qualidade,
                        postura_bruta,
                        postura_estavel,
                        rastreador,
                        metricas,
                        evento,
                    )
                    ultimo_estado = {
                        "qualidade": qualidade,
                        "metricas": metricas,
                        "feedback": mensagem_exibida,
                    }

                instante_atual = time.perf_counter()
                intervalo = instante_atual - instante_anterior
                instante_anterior = instante_atual
                fps_instantaneo = 1.0 / intervalo if intervalo > 0.0 else 0.0
                fps_suavizado = (
                    fps_instantaneo
                    if fps_suavizado == 0.0
                    else 0.9 * fps_suavizado + 0.1 * fps_instantaneo
                )

                tela = interface.renderizar(
                    quadro,
                    qualidade=str(ultimo_estado["qualidade"]),
                    rastreador=rastreador,
                    metricas=ultimo_estado["metricas"],
                    mensagem=(
                        "Análise pausada. Pressione P para continuar."
                        if pausado
                        else str(ultimo_estado["feedback"])
                    ),
                    fps=fps_suavizado,
                    calibracao=calibracao,
                    sentado_pendente=sentado_pendente,
                    em_pe_pendente=em_pe_pendente,
                    pausado=pausado,
                    espelhado=espelhado,
                    landmarks_visiveis=landmarks_visiveis,
                )
                cv2.imshow(nome_janela, tela)
                tecla = cv2.waitKey(1) & 0xFF

                if tecla in (ord("q"), ord("Q"), 27):
                    break
                if tecla in (ord("p"), ord("P")):
                    pausado = not pausado
                    continue
                if tecla in (ord("m"), ord("M")):
                    espelhado = not espelhado
                    filtro_postura.reiniciar()
                    suavizador.reiniciar()
                    aviso = "Modo espelho alterado. Reposicione-se se necessário."
                    aviso_ate = time.monotonic() + 2.5
                    continue
                if tecla in (ord("l"), ord("L")):
                    landmarks_visiveis = not landmarks_visiveis
                    continue
                if tecla in (ord("r"), ord("R")):
                    rastreador.reiniciar()
                    filtro_postura.reiniciar()
                    suavizador.reiniciar()
                    aviso = "Contadores e estado do movimento reiniciados."
                    aviso_ate = time.monotonic() + 2.5
                    continue

                if tecla in (ord("1"), ord("2")):
                    metricas_atual = ultimo_estado["metricas"]
                    if pausado:
                        aviso = "Retome a análise antes de calibrar."
                        aviso_ate = time.monotonic() + 2.5
                        continue
                    if not isinstance(metricas_atual, MetricasCorpo):
                        aviso = "Calibração recusada: o corpo não está completamente visível."
                        aviso_ate = time.monotonic() + 3.0
                        continue

                    medicao = (
                        metricas_atual.angulo_joelho,
                        metricas_atual.angulo_quadril,
                    )
                    if tecla == ord("1"):
                        sentado_pendente = medicao
                        aviso = "Postura sentada registrada. Fique em pé e pressione 2."
                    else:
                        em_pe_pendente = medicao
                        aviso = "Postura em pé registrada. Sente-se e pressione 1."
                    aviso_ate = time.monotonic() + 3.5

                    nova = finalizar_calibracao(sentado_pendente, em_pe_pendente)
                    if nova is not None:
                        calibracao = nova
                        calibracao.salvar(CAMINHO_CALIBRACAO)
                        sentado_pendente = None
                        em_pe_pendente = None
                        filtro_postura.reiniciar()
                        suavizador.reiniciar()
                        rastreador.reiniciar()
                        aviso = "Calibração concluída e salva. Sente-se para iniciar."
                        aviso_ate = time.monotonic() + 4.0
                    elif sentado_pendente is not None and em_pe_pendente is not None:
                        sentado_pendente = None
                        em_pe_pendente = None
                        aviso = "Calibração inválida. Repita as duas posturas com maior amplitude."
                        aviso_ate = time.monotonic() + 4.0

    finally:
        captura.release()
        cv2.destroyAllWindows()
        registro.fechar()

    if registro.caminho is not None:
        print(f"Sessão registrada em: {registro.caminho}")
    print(f"Repetições concluídas: {rastreador.repeticoes}")
    print(f"Tentativas incompletas: {rastreador.tentativas_incompletas}")
    print(f"Ciclos cancelados: {rastreador.ciclos_cancelados}")
    return 0


def executar_autoteste() -> int:
    assert math.isclose(
        calcular_angulo((0.0, -1.0), (0.0, 0.0), (0.0, 1.0)),
        180.0,
        abs_tol=1e-9,
    )
    assert math.isclose(
        calcular_angulo((0.0, -1.0), (0.0, 0.0), (1.0, 0.0)),
        90.0,
        abs_tol=1e-9,
    )

    calibracao = Calibracao()
    assert calibracao.classificar(100.0, 100.0) == Postura.SENTADO
    assert calibracao.classificar(140.0, 140.0) == Postura.TRANSICAO
    assert calibracao.classificar(170.0, 170.0) == Postura.EM_PE

    filtro = FiltroPosturaEstavel(quadros_necessarios=3)
    assert filtro.atualizar(Postura.SENTADO) == Postura.DESCONHECIDA
    assert filtro.atualizar(Postura.SENTADO) == Postura.DESCONHECIDA
    assert filtro.atualizar(Postura.SENTADO) == Postura.SENTADO

    rastreador = RastreadorRepeticoes()
    sequencia = (
        Postura.SENTADO,
        Postura.TRANSICAO,
        Postura.EM_PE,
        Postura.TRANSICAO,
        Postura.SENTADO,
    )
    for indice, postura in enumerate(sequencia):
        rastreador.atualizar(postura, 10.0 + indice)
    assert rastreador.repeticoes == 1
    assert rastreador.tentativas_incompletas == 0
    assert rastreador.duracao_ultima_repeticao is not None

    caminho_teste = RAIZ_PROJETO / "docs" / "preview_interface.png"
    gerar_demonstracao_interface(caminho_teste)
    assert caminho_teste.exists() and caminho_teste.stat().st_size > 10_000

    print("AUTOTESTE OK")
    print("- cálculo de ângulos: OK")
    print("- classificação calibrável: OK")
    print("- filtro temporal: OK")
    print("- máquina de estados e contagem: OK")
    print("- renderização da interface em português: OK")
    print(f"- prévia gerada em: {caminho_teste}")
    return 0


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor em português do movimento de sentar e levantar."
    )
    parser.add_argument("--camera", type=int, default=0, help="Índice da webcam.")
    parser.add_argument("--largura-camera", type=int, default=640)
    parser.add_argument("--altura-camera", type=int, default=480)
    parser.add_argument("--largura-interface", type=int, default=1280)
    parser.add_argument("--altura-interface", type=int, default=720)
    parser.add_argument("--modelo", type=Path, default=CAMINHO_MODELO_PADRAO)
    parser.add_argument(
        "--visibilidade-minima",
        type=float,
        default=VISIBILIDADE_MINIMA_PADRAO,
    )
    parser.add_argument(
        "--sem-registro",
        action="store_true",
        help="Não salvar os dados da sessão em CSV.",
    )
    parser.add_argument(
        "--sem-espelho",
        action="store_true",
        help="Não espelhar a imagem da webcam.",
    )
    parser.add_argument(
        "--autoteste",
        "--self-test",
        action="store_true",
        help="Testar a lógica e a interface sem abrir a webcam.",
    )
    parser.add_argument(
        "--demonstrar-interface",
        type=Path,
        metavar="ARQUIVO_PNG",
        help="Gerar uma prévia PNG da interface e encerrar.",
    )
    return parser


def main() -> int:
    args = criar_parser().parse_args()
    if args.autoteste:
        return executar_autoteste()
    if args.demonstrar_interface:
        caminho = gerar_demonstracao_interface(args.demonstrar_interface.resolve())
        print(f"Prévia da interface gerada em: {caminho}")
        return 0
    return executar_aplicacao(args)
