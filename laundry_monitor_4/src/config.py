"""
src/config.py
=============
세탁실 모니터링 시스템 전체 설정 클래스
모든 하이퍼파라미터, 경로, 동작 옵션을 중앙 관리
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import torch


# ---------------------------------------------------------------------------
# 하위 설정 클래스들
# ---------------------------------------------------------------------------

# src/config.py
@dataclass
class DetectionConfig:
    """문 상태 감지 파라미터"""
    # ── 열림 닫힘 정수 번호 관리(바꿀 일 없음) ──────────────────────────────────────────
    cls_open: int = 1
    cls_close: int = 0

    # ── IOU와 confidence 변수 관리(바꿀 수 있음) ──────────────────────────────────────────
    confidence_threshold: float = 0.25  # 커질수록 yolo 기반 탐지가 커짐
    iou_threshold: float = 0.15

@dataclass
class TrackingConfig:
    """시계열 상태 추적 파라미터"""

    # ── 슬라이딩 윈도우 다수결 투표 ──────────────────────────────────────────
    state_window: int = 20              # 다수결 윈도우 (프레임 수)
    open_vote_threshold: float = 0.55   # > 55% 열림 투표 → 확정 열림
    min_window_fill: float = 0.4        # 윈도우가 이 비율 이상 채워져야 판단

    # ── 상태 기계 디바운싱 ────────────────────────────────────────────────────
    debounce_frames: int = 4            # 새 상태를 N프레임 연속 감지 후 전환
    transition_hold_frames: int = 8     # TRANSITIONING 상태 유지 프레임

    # ── 신뢰도 ──────────────────────────────────────────────────────────────
    min_confidence: float = 0.25        # 이 미만 신뢰도 → 이전 상태 유지
    uncertain_hold_frames: int = 5      # 불확실 프레임 연속 시 유지


@dataclass
class CalibrationConfig:
    """보정 파라미터"""
    n_frames: int = 40          # 첫 보정에 사용할 프레임 수
    warmup_frames: int = 10     # 처음 N 프레임은 카메라 안정화를 위해 건너뜀
#    recalibrate_interval: int = 0   # N 프레임마다 재보정 (0 = 비활성화)
    assume_closed_on_start: bool = True  # 보정 시 모든 문이 닫혀 있다고 가정


@dataclass
class ZoneLayoutConfig:
    """세탁기 레이아웃 설정"""
    n_floors: int = 2                           # 층 수 (2 = 2층 + 1층)
    machines_per_floor: List[int] = field(
        default_factory=lambda: [2, 2]          # [2층 세탁기 수, 1층 세탁기 수]
    )
    zone_roi_padding: int = 12                  # ROI 확장 패딩 (픽셀)
    COLOR_1F, COLOR_2F = (50, 220, 80), (50, 120, 255)
    COLOR_DRAG = (0, 220, 255)  
    MIN_ROI_SIZE = 20       # interactive_setup 쵝소 ROI 변수 관리


@dataclass
class YOLOConfig:
    """YOLO26n 모델 설정"""
    model_path: str = "yolo26n.pt"              # 기본 사전학습 모델
    custom_model_path: Optional[str] = "models/custom_v1.pt"    # 파인튜닝된 커스텀 모델
    conf: float = 0.40                          # 탐지 신뢰도 임계값
    iou: float = 0.45                           # NMS IoU 임계값 (YOLO26n은 NMS-free)
    imgsz: int = 640                            # 입력 이미지 크기
    use_tracking: bool = True                   # BoT-SORT/ByteTrack 추적 사용
    tracker: str = "bytetrack.yaml"             # 추적기 설정 파일
    # 탐지할 COCO 클래스 ID (None = 전체). 사람만 탐지: [0]
    classes: Optional[List[int]] = field(default_factory=lambda: [0])   # COCO 클래스 이름 (주요 클래스만)
    verbose: bool = False                       # Ultralytics 로그 출력 억제


@dataclass
class VideoConfig:
    """비디오 소스 설정"""

    source: str = "1"               # 카메라 인덱스, RTSP URL, 또는 파일 경로
    # 맥북: 1, 웹캠: 0

    target_fps: int = 30            # 목표 처리 FPS
    frame_skip: int = 1             # N 프레임마다 1회 처리 (1 = 모든 프레임)
    buffer_size: int = 1            # VideoCapture 버퍼 크기 (작을수록 최신 프레임)
    reconnect_delay: float = 2.0    # 연결 끊김 시 재시도 대기 시간 (초)
    max_reconnect: int = 10         # 최대 재연결 시도 횟수


@dataclass
class DisplayConfig:
    """화면 출력 설정"""
    window_name: str = "Laundry Monitor | 세탁실 모니터"
    show_zones: bool = True         # 존 박스 표시
    show_circles: bool = True       # 감지된 원 표시
    show_status_panel: bool = True  # 오른쪽 상태 패널
    show_debug_info: bool = False   # 디버그 수치 표시
    show_yolo_detections: bool = True  # YOLO 탐지 결과 표시
    show_state_history: bool = True    # 상태 이력 그래프

    # ── 색상 (BGR) ──────────────────────────────────────────────────────────
    color_open: Tuple[int, int, int] = (30, 100, 255)       # 주황 → 열림
    color_closed: Tuple[int, int, int] = (50, 220, 80)      # 녹색 → 닫힘
    color_trans: Tuple[int, int, int] = (30, 220, 255)      # 노랑 → 변환중 (0, 220, 255)
    color_unknown: Tuple[int, int, int] = (100, 100, 100)   # 불확실
    color_circle: Tuple[int, int, int] = (255, 200, 50)     # 원 윤곽선
    color_person: Tuple[int, int, int] = (255, 80, 180)     # 사람 바운딩박스

    panel_width: int = 380
    panel_bg_alpha: float = 0.75
    font_scale: float = 0.65
    font_thickness: int = 1


# ---------------------------------------------------------------------------
# 최상위 앱 설정
# ---------------------------------------------------------------------------

@dataclass
class AppConfig:
    """전체 애플리케이션 설정 (기본값으로 바로 사용 가능)"""

    detection: DetectionConfig = field(default_factory=DetectionConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    layout: ZoneLayoutConfig = field(default_factory=ZoneLayoutConfig)
    yolo: YOLOConfig = field(default_factory=YOLOConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)

    # ── 파일 경로 ────────────────────────────────────────────────────────────
    zones_file: str = "configs/zones.json"
    calibration_file: str = "configs/calibration.json"
    log_dir: str = "logs"

    # ── 로깅 ─────────────────────────────────────────────────────────────────
    log_status_interval: int = 30  # N 프레임마다 콘솔에 상태 출력

    def get_device(self) -> str:
        """M5 Pro MPS > CUDA > CPU 순으로 자동 선택"""
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda:0"
        return "cpu"

