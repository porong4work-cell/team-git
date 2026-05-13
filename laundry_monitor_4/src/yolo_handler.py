"""
src/yolo_handler.py
===================
YOLO26n 모델 래퍼

역할:
  1. COCO 사전학습 YOLO26n: 사람 감지 + 씬 컨텍스트 분석
  2. 커스텀 파인튜닝 모델 (선택): 직접 문 상태 분류
     - classes: ["washer_closed", "washer_open"]
  3. BoT-SORT / ByteTrack 기반 객체 추적

M5 Pro 최적화:
  - device="mps" (Metal Performance Shaders)
  - 배치 없이 단일 프레임 처리 (실시간 우선)
  - verbose=False로 불필요한 출력 억제
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import AppConfig

logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Detection 결과 컨테이너
# ---------------------------------------------------------------------------

class Detection:
    """단일 탐지 결과"""
    __slots__ = ["bbox", "conf", "cls_id", "cls_name", "track_id"]

    def __init__(
        self,
        bbox: Tuple[int, int, int, int],  # (x1, y1, x2, y2)
        conf: float,
        cls_id: int,
        cls_name: str,
        track_id: Optional[int] = None,
    ) -> None:
        self.bbox = bbox
        self.conf = conf
        self.cls_id = cls_id
        self.cls_name = cls_name
        self.track_id = track_id

    @property
    def x1(self): return self.bbox[0]
    @property
    def y1(self): return self.bbox[1]
    @property
    def x2(self): return self.bbox[2]
    @property
    def y2(self): return self.bbox[3]
    @property
    def cx(self): return (self.bbox[0] + self.bbox[2]) // 2
    @property
    def cy(self): return (self.bbox[1] + self.bbox[3]) // 2

    def __repr__(self) -> str:
        return (
            f"Detection({self.cls_name}, conf={self.conf:.2f}, "
            f"bbox={self.bbox}, track={self.track_id})"
        )


class YOLOResult:
    """한 프레임의 YOLO 탐지 결과 컨테이너"""

    def __init__(
        self,
        detections: List[Detection],
        frame_shape: Tuple[int, int],   
        # OpenCV에서 frame.shape → (Height,Width,Channels) 이고, frame.shape[0:2]는 (Height,Width)로 슬라이싱한 값
    ) -> None:
        self.detections = detections
        self.frame_shape = frame_shape

    def persons(self) -> List[Detection]:
        return [d for d in self.detections if d.cls_id == 0]


    def __len__(self) -> int:
        return len(self.detections)


# ---------------------------------------------------------------------------
# YOLOHandler
# ---------------------------------------------------------------------------

class YOLOHandler:
    """
    YOLO26n 모델 로드 및 추론 관리.

    모드:
      - pretrained: yolo26n.pt (COCO 80 클래스)
    """

    def __init__(self, config: AppConfig) -> None:
        self.cfg = config.yolo
        self.device = config.get_device()
        self._model = None
        self._use_tracking = config.yolo.use_tracking
        self._frame_count = 0

    # ── 모델 로드 ─────────────────────────────────────────────────────────────

    def load(self) -> None:
        """사전 준비된 YOLOn 모델 로드"""
        try:
            from ultralytics import YOLO
            logger.info(f"{self.cfg.model_path} 로드 중... (device=%s)", self.device)
            self._model = YOLO(self.cfg.model_path)
            # warm-up
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self._model(dummy, device=self.device, verbose=False)
            logger.info("YOLO26n 로드 완료: %s", self.cfg.model_path)
        except Exception as e:
            logger.error("YOLO26n 로드 실패: %s", e)
            self._model = None

    def is_loaded(self) -> bool:
        return self._model is not None

    # ── 추론 ─────────────────────────────────────────────────────────────────

    def infer(self, frame: np.ndarray) -> YOLOResult:
        """
        YOLO26n 추론 (사전학습 모델).
        단일 프레임을 받아 results의 길이는 1임.
        results라고 쓰는게 관례임.
        추적 활성화 시 track_id 포함.
        """
        self._frame_count += 1
        h, w = frame.shape[:2] 

        if self._model is None:
            return YOLOResult([], (h, w))

        try:
            if self._use_tracking:
                results = self._model.track(
                    frame,
                    device=self.device,
                    conf=self.cfg.conf,
                    iou=self.cfg.iou,
                    imgsz=self.cfg.imgsz,
                    classes=self.cfg.classes,
                    tracker=self.cfg.tracker,
                    persist=True,
                    verbose=self.cfg.verbose,
                )
            else:
                results = self._model(
                    frame,
                    device=self.device,
                    conf=self.cfg.conf,
                    iou=self.cfg.iou,
                    imgsz=self.cfg.imgsz,
                    classes=self.cfg.classes,
                    verbose=self.cfg.verbose,
                )
        except Exception as e:
            logger.debug("YOLO 추론 오류: %s", e)
            return YOLOResult([], (h, w))

        return self._parse_results(results, h, w)   # 단일 프레임에대한 추론이니 results[0]으로 반환
    


    def _parse_results(
        self,
        results,
        h: int, w: int,
    ) -> YOLOResult:
        """다른 이유도 많지만 우선 사람만 감지하므로 메모리 절약을 위해 
           Ultralytics Results 객체 → YOLOResult 변환"""
        detections: List[Detection] = []

        if not results:
            return YOLOResult([], (h, w))
        
        result = results[0]

        if result.boxes is None:
            return YOLOResult([], (h, w))

        boxes = result.boxes
        cls_ids = boxes.cls.cpu().numpy().astype(int) if boxes.cls is not None else []
        confs   = boxes.conf.cpu().numpy() if boxes.conf is not None else []
        xyxy    = boxes.xyxy.cpu().numpy().astype(int) if boxes.xyxy is not None else []

        # 추적 ID (없으면 None)
        if self._use_tracking and boxes.id is not None:
            track_ids = boxes.id.cpu().numpy().astype(int)
        else:
            track_ids = [None] * len(cls_ids)

        names = result.names  # {cls_id: class_name}
        
        for i, (cls_id, conf, box) in enumerate(zip(cls_ids, confs, xyxy)):
            cls_name = names.get(int(cls_id), str(cls_id))
            x1, y1, x2, y2 = (
                max(0, box[0]), max(0, box[1]),
                min(w, box[2]), min(h, box[3])
            )
            tid = track_ids[i] if i < len(track_ids) else None
            detections.append(Detection(
                bbox=(x1, y1, x2, y2),
                conf=float(conf),
                cls_id=int(cls_id),
                cls_name=cls_name,
                track_id=int(tid) if tid is not None else None,
            ))

        return YOLOResult(detections, (h, w))


    
