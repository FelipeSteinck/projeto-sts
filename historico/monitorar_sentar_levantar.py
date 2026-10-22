r"""Monitor visual do exercicio sentar-e-levantar (sit-to-stand).

Prototipo academico nao clinico. O programa:

- detecta landmarks corporais com MediaPipe Pose Landmarker;
- escolhe automaticamente o lado corporal mais visivel;
- calcula angulos de joelho, quadril e inclinacao do tronco;
- classifica as fases SENTADO, TRANSICAO e EM_PE;
- usa uma maquina de estados para contar repeticoes completas;
- permite calibracao individual das posturas sentado/em pe;
- registra a sessao em CSV, sem salvar imagens ou video.

Controles:
    1       calibrar postura SENTADO
    2       calibrar postura EM PE
    Q/ESC   encerrar

Uso, a partir da raiz do projeto:
    python .\src\monitorar_sentar_levantar.py

Autoteste sem webcam:
    python .\src\monitorar_sentar_levantar.py --self-test
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "pose_landmarker_lite.task"
CALIBRATION_PATH = PROJECT_ROOT / "data" / "calibracao_sts.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "sessoes"

DEFAULT_MIN_VISIBILITY = 0.60
STABLE_FRAMES = 3
LOST_FRAMES_TO_CANCEL = 15
EMA_ALPHA = 0.25

# Conexoes principais do corpo. Os indices seguem os 33 landmarks do MediaPipe.
POSE_CONNECTIONS = (
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27),
    (27, 29), (29, 31), (27, 31),
    (24, 26), (26, 28),
    (28, 30), (30, 32), (28, 32),
)

SIDE_LANDMARKS = {
    "esquerdo": {
        "shoulder": 11,
        "hip": 23,
        "knee": 25,
        "ankle": 27,
    },
    "direito": {
        "shoulder": 12,
        "hip": 24,
        "knee": 26,
        "ankle": 28,
    },
}


class Posture(str, Enum):
    UNKNOWN = "DESCONHECIDA"
    SITTING = "SENTADO"
    TRANSITION = "TRANSICAO"
    STANDING = "EM_PE"


class MotionPhase(str, Enum):
    WAITING = "AGUARDANDO_SENTADO"
    READY = "PRONTO"
    RISING = "LEVANTANDO"
    STANDING = "EM_PE"
    LOWERING = "SENTANDO"


@dataclass
class BodyMetrics:
    side: str
    visibility: float
    knee_angle: float
    hip_angle: float
    trunk_tilt: float
    points: dict[str, tuple[int, int]]


@dataclass
class Calibration:
    """Extremos pessoais usados apenas para separar fases do movimento."""

    seated_knee: float = 95.0
    seated_hip: float = 95.0
    standing_knee: float = 170.0
    standing_hip: float = 170.0
    source: str = "padrao_ilustrativo"

    @property
    def sitting_knee_limit(self) -> float:
        return self.seated_knee + 0.45 * (
            self.standing_knee - self.seated_knee
        )

    @property
    def sitting_hip_limit(self) -> float:
        return self.seated_hip + 0.45 * (
            self.standing_hip - self.seated_hip
        )

    @property
    def standing_knee_limit(self) -> float:
        return self.seated_knee + 0.75 * (
            self.standing_knee - self.seated_knee
        )

    @property
    def standing_hip_limit(self) -> float:
        return self.seated_hip + 0.75 * (
            self.standing_hip - self.seated_hip
        )

    def is_valid(self) -> bool:
        knee_range = self.standing_knee - self.seated_knee
        hip_range = self.standing_hip - self.seated_hip
        return knee_range >= 20.0 and hip_range >= 20.0

    def classify(self, knee_angle: float, hip_angle: float) -> Posture:
        sitting = (
            knee_angle <= self.sitting_knee_limit
            and hip_angle <= self.sitting_hip_limit
        )
        standing = (
            knee_angle >= self.standing_knee_limit
            and hip_angle >= self.standing_hip_limit
        )

        if sitting:
            return Posture.SITTING
        if standing:
            return Posture.STANDING
        return Posture.TRANSITION

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "seated_knee": self.seated_knee,
            "seated_hip": self.seated_hip,
            "standing_knee": self.standing_knee,
            "standing_hip": self.standing_hip,
            "source": "calibracao_individual",
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "warning": (
                "Limiares operacionais do algoritmo; nao sao prescricao clinica."
            ),
        }
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "Calibration":
        if not path.exists():
            return cls()

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            calibration = cls(
                seated_knee=float(payload["seated_knee"]),
                seated_hip=float(payload["seated_hip"]),
                standing_knee=float(payload["standing_knee"]),
                standing_hip=float(payload["standing_hip"]),
                source="calibracao_salva",
            )
            return calibration if calibration.is_valid() else cls()
        except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
            return cls()


class StablePostureFilter:
    """Exige alguns quadros iguais antes de aceitar uma nova postura."""

    def __init__(self, required_frames: int = STABLE_FRAMES) -> None:
        self.required_frames = required_frames
        self.candidate = Posture.UNKNOWN
        self.candidate_count = 0
        self.stable = Posture.UNKNOWN

    def update(self, posture: Posture) -> Posture:
        if posture == self.candidate:
            self.candidate_count += 1
        else:
            self.candidate = posture
            self.candidate_count = 1

        if self.candidate_count >= self.required_frames:
            self.stable = self.candidate

        return self.stable

    def reset(self) -> None:
        self.candidate = Posture.UNKNOWN
        self.candidate_count = 0
        self.stable = Posture.UNKNOWN


class MetricSmoother:
    """Filtro exponencial para reduzir oscilacao dos angulos."""

    def __init__(self, alpha: float = EMA_ALPHA) -> None:
        self.alpha = alpha
        self.values: dict[str, float] = {}

    def _update_value(self, name: str, value: float) -> float:
        if name not in self.values:
            self.values[name] = value
        else:
            self.values[name] = (
                self.alpha * value
                + (1.0 - self.alpha) * self.values[name]
            )
        return self.values[name]

    def update(self, metrics: BodyMetrics) -> BodyMetrics:
        return BodyMetrics(
            side=metrics.side,
            visibility=metrics.visibility,
            knee_angle=self._update_value("knee", metrics.knee_angle),
            hip_angle=self._update_value("hip", metrics.hip_angle),
            trunk_tilt=self._update_value("trunk", metrics.trunk_tilt),
            points=metrics.points,
        )

    def reset(self) -> None:
        self.values.clear()


class RepetitionTracker:
    """Maquina de estados do ciclo sentado -> em pe -> sentado."""

    def __init__(self) -> None:
        self.phase = MotionPhase.WAITING
        self.armed = False
        self.repetitions = 0
        self.incomplete_attempts = 0
        self.cancelled_attempts = 0
        self.cycle_start: float | None = None
        self.last_duration: float | None = None
        self.missing_frames = 0

    def update(self, posture: Posture, now: float) -> tuple[str, str]:
        self.missing_frames = 0
        event = ""

        if self.phase in (MotionPhase.WAITING, MotionPhase.READY):
            if posture == Posture.SITTING:
                self.phase = MotionPhase.READY
                self.armed = True
                return "Pronto: inicie o movimento", event

            if not self.armed:
                self.phase = MotionPhase.WAITING
                return "Sente-se para iniciar o ciclo", event

            if posture == Posture.TRANSITION:
                self.phase = MotionPhase.RISING
                self.cycle_start = now
                return "Levantando", "inicio_subida"

            if posture == Posture.STANDING:
                self.phase = MotionPhase.STANDING
                self.cycle_start = now
                return "Em pe: retorne com controle", "em_pe_detectado"

        elif self.phase == MotionPhase.RISING:
            if posture == Posture.STANDING:
                self.phase = MotionPhase.STANDING
                return "Em pe: retorne com controle", "em_pe_detectado"
            if posture == Posture.SITTING:
                self.incomplete_attempts += 1
                self.phase = MotionPhase.READY
                self.armed = True
                self.cycle_start = None
                return "Tentativa incompleta: extensao final nao detectada", (
                    "tentativa_incompleta"
                )
            return "Levantando", event

        elif self.phase == MotionPhase.STANDING:
            if posture == Posture.TRANSITION:
                self.phase = MotionPhase.LOWERING
                return "Sentando", "inicio_descida"
            if posture == Posture.SITTING:
                return self._complete(now)
            return "Em pe: retorne com controle", event

        elif self.phase == MotionPhase.LOWERING:
            if posture == Posture.SITTING:
                return self._complete(now)
            if posture == Posture.STANDING:
                self.phase = MotionPhase.STANDING
                return "Em pe: retorne com controle", event
            return "Sentando", event

        return "Movimento em andamento", event

    def _complete(self, now: float) -> tuple[str, str]:
        self.repetitions += 1
        self.last_duration = (
            now - self.cycle_start if self.cycle_start is not None else None
        )
        self.phase = MotionPhase.READY
        self.armed = True
        self.cycle_start = None

        if self.last_duration is None:
            message = f"Repeticao {self.repetitions} concluida"
        else:
            message = (
                f"Repeticao {self.repetitions} concluida "
                f"({self.last_duration:.1f} s)"
            )
        return message, "repeticao_concluida"

    def handle_missing(self) -> tuple[str, str]:
        self.missing_frames += 1

        if (
            self.missing_frames >= LOST_FRAMES_TO_CANCEL
            and self.phase in (
                MotionPhase.RISING,
                MotionPhase.STANDING,
                MotionPhase.LOWERING,
            )
        ):
            self.cancelled_attempts += 1
            self.phase = MotionPhase.WAITING
            self.armed = False
            self.cycle_start = None
            return "Ciclo cancelado: rastreamento perdido", "ciclo_cancelado"

        return "Enquadre o corpo completamente", ""


class SessionLogger:
    """Registra dados numericos; nenhuma imagem ou video e armazenado."""

    FIELDNAMES = (
        "timestamp",
        "elapsed_s",
        "frame",
        "pose_quality",
        "side",
        "visibility",
        "raw_posture",
        "stable_posture",
        "motion_phase",
        "knee_angle_deg",
        "hip_angle_deg",
        "trunk_tilt_deg",
        "repetitions",
        "incomplete_attempts",
        "cancelled_attempts",
        "last_rep_duration_s",
        "event",
    )

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.file: Any = None
        self.writer: csv.DictWriter | None = None
        self.path: Path | None = None
        self.start_time = time.monotonic()
        self.rows_since_flush = 0

        if enabled:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.path = OUTPUT_DIR / f"sessao_sts_{stamp}.csv"
            self.file = self.path.open("w", newline="", encoding="utf-8")
            self.writer = csv.DictWriter(
                self.file,
                fieldnames=self.FIELDNAMES,
            )
            self.writer.writeheader()

    def write(
        self,
        frame_number: int,
        quality: str,
        raw_posture: Posture,
        stable_posture: Posture,
        tracker: RepetitionTracker,
        metrics: BodyMetrics | None,
        event: str,
    ) -> None:
        if not self.enabled or self.writer is None:
            return

        row = {
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "elapsed_s": f"{time.monotonic() - self.start_time:.3f}",
            "frame": frame_number,
            "pose_quality": quality,
            "side": metrics.side if metrics else "",
            "visibility": f"{metrics.visibility:.3f}" if metrics else "",
            "raw_posture": raw_posture.value,
            "stable_posture": stable_posture.value,
            "motion_phase": tracker.phase.value,
            "knee_angle_deg": f"{metrics.knee_angle:.2f}" if metrics else "",
            "hip_angle_deg": f"{metrics.hip_angle:.2f}" if metrics else "",
            "trunk_tilt_deg": f"{metrics.trunk_tilt:.2f}" if metrics else "",
            "repetitions": tracker.repetitions,
            "incomplete_attempts": tracker.incomplete_attempts,
            "cancelled_attempts": tracker.cancelled_attempts,
            "last_rep_duration_s": (
                f"{tracker.last_duration:.3f}"
                if tracker.last_duration is not None
                else ""
            ),
            "event": event,
        }
        self.writer.writerow(row)
        self.rows_since_flush += 1

        if self.rows_since_flush >= 30 or event:
            self.file.flush()
            self.rows_since_flush = 0

    def close(self) -> None:
        if self.file is not None:
            self.file.flush()
            self.file.close()


def calculate_angle(
    point_a: tuple[float, float],
    vertex: tuple[float, float],
    point_c: tuple[float, float],
) -> float:
    """Retorna o menor angulo A-vertice-C no intervalo [0, 180]."""

    vector_a = (point_a[0] - vertex[0], point_a[1] - vertex[1])
    vector_c = (point_c[0] - vertex[0], point_c[1] - vertex[1])
    norm_a = math.hypot(*vector_a)
    norm_c = math.hypot(*vector_c)

    if norm_a == 0.0 or norm_c == 0.0:
        raise ValueError("Nao e possivel calcular angulo com vetor nulo.")

    dot = vector_a[0] * vector_c[0] + vector_a[1] * vector_c[1]
    cross = vector_a[0] * vector_c[1] - vector_a[1] * vector_c[0]
    return abs(math.degrees(math.atan2(cross, dot)))


def calculate_trunk_tilt(
    shoulder: tuple[float, float],
    hip: tuple[float, float],
) -> float:
    """Calcula a inclinacao absoluta do tronco em relacao a vertical."""

    trunk_vector = (shoulder[0] - hip[0], shoulder[1] - hip[1])
    upward_vertical = (0.0, -1.0)
    return calculate_angle(
        (hip[0] + trunk_vector[0], hip[1] + trunk_vector[1]),
        hip,
        (hip[0] + upward_vertical[0], hip[1] + upward_vertical[1]),
    )


def landmark_confidence(landmark: Any) -> float:
    visibility = getattr(landmark, "visibility", 1.0)
    presence = getattr(landmark, "presence", 1.0)
    visibility = 1.0 if visibility is None else float(visibility)
    presence = 1.0 if presence is None else float(presence)
    return min(visibility, presence)


def extract_body_metrics(
    landmarks: list[Any],
    width: int,
    height: int,
    min_visibility: float,
) -> tuple[BodyMetrics | None, str, float]:
    """Seleciona o lado mais visivel e calcula as metricas necessarias."""

    candidates: list[tuple[float, str, dict[str, Any]]] = []

    for side, indices in SIDE_LANDMARKS.items():
        selected = {name: landmarks[index] for name, index in indices.items()}
        confidence = min(landmark_confidence(item) for item in selected.values())
        all_inside = all(
            0.0 <= item.x <= 1.0 and 0.0 <= item.y <= 1.0
            for item in selected.values()
        )
        score = confidence if all_inside else 0.0
        candidates.append((score, side, selected))

    score, side, selected = max(candidates, key=lambda item: item[0])

    if score < min_visibility:
        return None, side, score

    points = {
        name: (int(item.x * width), int(item.y * height))
        for name, item in selected.items()
    }

    metrics = BodyMetrics(
        side=side,
        visibility=score,
        knee_angle=calculate_angle(
            points["hip"], points["knee"], points["ankle"]
        ),
        hip_angle=calculate_angle(
            points["shoulder"], points["hip"], points["knee"]
        ),
        trunk_tilt=calculate_trunk_tilt(
            points["shoulder"], points["hip"]
        ),
        points=points,
    )
    return metrics, side, score


def draw_pose(cv2: Any, frame: Any, landmarks: list[Any]) -> None:
    height, width = frame.shape[:2]
    points: list[tuple[int, int] | None] = []

    for landmark in landmarks:
        x = int(landmark.x * width)
        y = int(landmark.y * height)
        visible = landmark_confidence(landmark) >= 0.35
        inside = 0 <= x < width and 0 <= y < height
        points.append((x, y) if visible and inside else None)

    for start_index, end_index in POSE_CONNECTIONS:
        start = points[start_index]
        end = points[end_index]
        if start is not None and end is not None:
            cv2.line(frame, start, end, (0, 200, 0), 2, cv2.LINE_AA)

    for point in points:
        if point is not None:
            cv2.circle(frame, point, 3, (0, 0, 255), -1, cv2.LINE_AA)


def draw_selected_side(cv2: Any, frame: Any, metrics: BodyMetrics) -> None:
    chain = ("shoulder", "hip", "knee", "ankle")
    for start_name, end_name in zip(chain, chain[1:]):
        cv2.line(
            frame,
            metrics.points[start_name],
            metrics.points[end_name],
            (255, 255, 0),
            4,
            cv2.LINE_AA,
        )

    for point in metrics.points.values():
        cv2.circle(frame, point, 6, (255, 255, 0), -1, cv2.LINE_AA)


def put_text(
    cv2: Any,
    frame: Any,
    text: str,
    position: tuple[int, int],
    color: tuple[int, int, int] = (255, 255, 255),
    scale: float = 0.55,
    thickness: int = 1,
) -> None:
    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def draw_dashboard(
    cv2: Any,
    frame: Any,
    quality: str,
    tracker: RepetitionTracker,
    metrics: BodyMetrics | None,
    feedback: str,
    fps: float,
    calibration: Calibration,
    pending_seated: tuple[float, float] | None,
    pending_standing: tuple[float, float] | None,
) -> None:
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], 205), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.62, frame, 0.38, 0.0, frame)

    quality_color = {
        "POSE COMPLETA": (0, 255, 0),
        "POSE PARCIAL": (0, 165, 255),
        "SEM POSE": (0, 0, 255),
    }.get(quality, (255, 255, 255))

    put_text(cv2, frame, "MONITOR SENTAR-LEVANTAR", (12, 24), scale=0.65, thickness=2)
    put_text(
        cv2,
        frame,
        "PROTOTIPO NAO CLINICO",
        (365, 24),
        color=(0, 165, 255),
        scale=0.48,
        thickness=1,
    )
    put_text(cv2, frame, f"Qualidade: {quality}", (12, 50), quality_color, 0.55, 2)
    put_text(cv2, frame, f"Fase: {tracker.phase.value}", (12, 76), scale=0.55, thickness=2)
    put_text(
        cv2,
        frame,
        f"Repeticoes: {tracker.repetitions} | Incompletas: {tracker.incomplete_attempts}",
        (12, 102),
        scale=0.55,
        thickness=2,
    )

    if metrics is None:
        metrics_line = "Joelho: -- | Quadril: -- | Tronco: --"
        side_line = "Lado usado: --"
    else:
        metrics_line = (
            f"Joelho: {metrics.knee_angle:5.1f} | "
            f"Quadril: {metrics.hip_angle:5.1f} | "
            f"Tronco: {metrics.trunk_tilt:4.1f} graus"
        )
        side_line = (
            f"Lado usado: {metrics.side} | Visibilidade: {metrics.visibility:.2f}"
        )

    put_text(cv2, frame, metrics_line, (12, 128), scale=0.52, thickness=1)
    put_text(cv2, frame, side_line, (12, 152), scale=0.50, thickness=1)
    put_text(cv2, frame, f"Feedback: {feedback}", (12, 177), (255, 255, 0), 0.50, 2)

    calibration_status = (
        "calibracao salva"
        if calibration.source != "padrao_ilustrativo"
        else "limiares padrao - calibre"
    )
    pending = []
    if pending_seated is not None:
        pending.append("sentado OK")
    if pending_standing is not None:
        pending.append("em pe OK")
    pending_text = f" ({', '.join(pending)})" if pending else ""
    put_text(
        cv2,
        frame,
        f"1: sentado | 2: em pe | Q/ESC: sair | FPS {fps:.1f} | {calibration_status}{pending_text}",
        (12, 199),
        (210, 210, 210),
        0.42,
        1,
    )


def open_camera(cv2: Any, camera_index: int, width: int, height: int) -> Any:
    capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not capture.isOpened():
        capture.release()
        capture = cv2.VideoCapture(camera_index)

    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return capture


def try_finalize_calibration(
    pending_seated: tuple[float, float] | None,
    pending_standing: tuple[float, float] | None,
) -> Calibration | None:
    if pending_seated is None or pending_standing is None:
        return None

    calibration = Calibration(
        seated_knee=pending_seated[0],
        seated_hip=pending_seated[1],
        standing_knee=pending_standing[0],
        standing_hip=pending_standing[1],
        source="calibracao_individual",
    )
    return calibration if calibration.is_valid() else None


def load_dependencies() -> tuple[Any, Any, Any, Any]:
    try:
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError as exc:
        raise RuntimeError(
            "Dependencias ausentes. Ative a .venv e instale mediapipe/OpenCV."
        ) from exc

    return cv2, mp, mp_python, vision


def run_application(args: argparse.Namespace) -> int:
    cv2, mp, mp_python, vision = load_dependencies()

    model_path = args.model.resolve()
    if not model_path.exists():
        raise FileNotFoundError(f"Modelo nao encontrado: {model_path}")

    calibration = Calibration.load(CALIBRATION_PATH)
    pending_seated: tuple[float, float] | None = None
    pending_standing: tuple[float, float] | None = None

    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    capture = open_camera(cv2, args.camera, args.width, args.height)
    if not capture.isOpened():
        raise RuntimeError(f"Nao foi possivel abrir a camera {args.camera}.")

    smoother = MetricSmoother()
    posture_filter = StablePostureFilter()
    tracker = RepetitionTracker()
    logger = SessionLogger(enabled=not args.no_log)

    previous_time = time.perf_counter()
    smoothed_fps = 0.0
    last_timestamp_ms = -1
    frame_number = 0
    notice = "Posicione a camera de lado e enquadre o corpo inteiro"
    notice_until = time.monotonic() + 5.0

    try:
        with vision.PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                success, frame = capture.read()
                if not success or frame is None:
                    print("Falha ao capturar um quadro da webcam.")
                    break

                frame_number += 1
                height, width = frame.shape[:2]
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=rgb_frame,
                )

                timestamp_ms = int(time.monotonic() * 1000)
                timestamp_ms = max(timestamp_ms, last_timestamp_ms + 1)
                last_timestamp_ms = timestamp_ms

                result = landmarker.detect_for_video(mp_image, timestamp_ms)
                has_pose = bool(result.pose_landmarks)
                metrics: BodyMetrics | None = None
                raw_posture = Posture.UNKNOWN
                stable_posture = posture_filter.stable
                event = ""

                if has_pose:
                    landmarks = result.pose_landmarks[0]
                    draw_pose(cv2, frame, landmarks)
                    raw_metrics, _side, _score = extract_body_metrics(
                        landmarks,
                        width,
                        height,
                        args.min_visibility,
                    )

                    if raw_metrics is not None:
                        metrics = smoother.update(raw_metrics)
                        draw_selected_side(cv2, frame, metrics)
                        raw_posture = calibration.classify(
                            metrics.knee_angle,
                            metrics.hip_angle,
                        )
                        stable_posture = posture_filter.update(raw_posture)
                        feedback, event = tracker.update(
                            stable_posture,
                            time.monotonic(),
                        )
                        quality = "POSE COMPLETA"
                    else:
                        quality = "POSE PARCIAL"
                        feedback, event = tracker.handle_missing()
                else:
                    quality = "SEM POSE"
                    feedback, event = tracker.handle_missing()

                if tracker.missing_frames >= LOST_FRAMES_TO_CANCEL:
                    posture_filter.reset()
                    smoother.reset()
                    stable_posture = Posture.UNKNOWN

                if event in ("repeticao_concluida", "tentativa_incompleta", "ciclo_cancelado"):
                    notice = feedback
                    notice_until = time.monotonic() + 2.5

                shown_feedback = (
                    notice if time.monotonic() < notice_until else feedback
                )

                current_time = time.perf_counter()
                elapsed = current_time - previous_time
                previous_time = current_time
                instantaneous_fps = 1.0 / elapsed if elapsed > 0.0 else 0.0
                smoothed_fps = (
                    instantaneous_fps
                    if smoothed_fps == 0.0
                    else 0.9 * smoothed_fps + 0.1 * instantaneous_fps
                )

                draw_dashboard(
                    cv2,
                    frame,
                    quality,
                    tracker,
                    metrics,
                    shown_feedback,
                    smoothed_fps,
                    calibration,
                    pending_seated,
                    pending_standing,
                )

                logger.write(
                    frame_number,
                    quality,
                    raw_posture,
                    stable_posture,
                    tracker,
                    metrics,
                    event,
                )

                cv2.imshow("Monitor sentar-levantar", frame)
                key = cv2.waitKey(1) & 0xFF

                if key in (ord("q"), ord("Q"), 27):
                    break

                if key in (ord("1"), ord("2")):
                    if metrics is None:
                        notice = "Calibracao recusada: corpo incompleto"
                        notice_until = time.monotonic() + 2.5
                        continue

                    measured = (metrics.knee_angle, metrics.hip_angle)
                    if key == ord("1"):
                        pending_seated = measured
                        notice = "Postura sentada registrada; agora fique em pe e pressione 2"
                    else:
                        pending_standing = measured
                        notice = "Postura em pe registrada; agora sente-se e pressione 1"
                    notice_until = time.monotonic() + 3.0

                    new_calibration = try_finalize_calibration(
                        pending_seated,
                        pending_standing,
                    )
                    if new_calibration is not None:
                        calibration = new_calibration
                        calibration.save(CALIBRATION_PATH)
                        pending_seated = None
                        pending_standing = None
                        posture_filter.reset()
                        tracker = RepetitionTracker()
                        notice = "Calibracao concluida e salva"
                        notice_until = time.monotonic() + 3.0
                    elif pending_seated is not None and pending_standing is not None:
                        pending_seated = None
                        pending_standing = None
                        notice = "Calibracao invalida: repita as duas posturas"
                        notice_until = time.monotonic() + 3.0

    finally:
        capture.release()
        cv2.destroyAllWindows()
        logger.close()

    if logger.path is not None:
        print(f"Sessao registrada em: {logger.path}")
    print(f"Repeticoes concluidas: {tracker.repetitions}")
    print(f"Tentativas incompletas: {tracker.incomplete_attempts}")
    print(f"Ciclos cancelados: {tracker.cancelled_attempts}")
    return 0


def run_self_test() -> int:
    assert math.isclose(
        calculate_angle((0.0, -1.0), (0.0, 0.0), (0.0, 1.0)),
        180.0,
        abs_tol=1e-9,
    )
    assert math.isclose(
        calculate_angle((0.0, -1.0), (0.0, 0.0), (1.0, 0.0)),
        90.0,
        abs_tol=1e-9,
    )

    calibration = Calibration()
    assert calibration.classify(100.0, 100.0) == Posture.SITTING
    assert calibration.classify(140.0, 140.0) == Posture.TRANSITION
    assert calibration.classify(170.0, 170.0) == Posture.STANDING

    tracker = RepetitionTracker()
    now = 10.0
    sequence = (
        Posture.SITTING,
        Posture.TRANSITION,
        Posture.STANDING,
        Posture.TRANSITION,
        Posture.SITTING,
    )
    for offset, posture in enumerate(sequence):
        tracker.update(posture, now + offset)

    assert tracker.repetitions == 1
    assert tracker.incomplete_attempts == 0
    assert tracker.last_duration is not None

    print("AUTOTESTE OK")
    print("- calculo de angulos: OK")
    print("- classificacao de fases: OK")
    print("- maquina de estados e contagem: OK")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prototipo nao clinico para monitorar o exercicio sentar-e-levantar."
        )
    )
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
    )
    parser.add_argument(
        "--min-visibility",
        type=float,
        default=DEFAULT_MIN_VISIBILITY,
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Nao registrar a sessao em CSV.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Executar testes logicos sem abrir a webcam.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()
    return run_application(args)


if __name__ == "__main__":
    raise SystemExit(main())
