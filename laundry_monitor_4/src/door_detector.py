"""
src/door_detector.py  (v3 — YOLO 전적 의존)
=============================================
파인튜닝된 YOLO 세그멘테이션 모델(custom.pt)로
문 열림/닫힘 상태를 직접 판단합니다.

  클래스 매핑:
    0 = Closed (닫힘)  →  is_open = False
    1 = Open   (열림)  →  is_open = True

  detect_all(frame, zones) 흐름:
    1. 전체 프레임에 YOLO 추론 (전체 장면을 한 번에 처리)
    2. 각 존(ZoneDef)의 바운딩박스와 탐지 바운딩박스 IoU 계산
    3. IoU ≥ threshold인 탐지 중 confidence 최대값 선택
    4. 선택된 탐지의 class → 열림/닫힘 결정

  호환성:
    - update_zone_statistic / set_statistics / save_statistics_json /
      load_calibration 메서드는 no-op으로 유지
      (main.py가 보정 분기를 건드리지 않아도 정상 동작)
    - DoorDetector.needs_calibration = False → main.py가 보정 단계 스킵
"""
from __future__ import annotations
import cv2

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from .zone_manager import ZoneManager, Zone_Statistic
from .config import AppConfig

log = logging.getLogger(__name__)

# config의 DetectionConfig에서 환경변수 관리


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────────────────────────────────────

def _iou(box_a: np.ndarray, box_b: np.ndarray) -> float:
    """XYXY 형식 두 박스의 IoU"""
    xa1, ya1, xa2, ya2 = box_a
    xb1, yb1, xb2, yb2 = box_b

    # 각 박스 사이 넓이
    area_a = max(0.0, xa2 - xa1) * max(0.0, ya2 - ya1)  # 박스 A의 넓이
    area_b = max(0.0, xb2 - xb1) * max(0.0, yb2 - yb1)  # 박스 B의 넓이
    
    # 두 박스 사이 교집합 좌표
    ix1, iy1 = max(xa1, xb1), max(ya1, yb1)
    ix2, iy2 = min(xa2, xb2), min(ya2, yb2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)   # 두 박스 사이 교집합 넓이
    if inter == 0.0:
        return 0.0  #교집합 없으면 0 반환
    
    union  = area_a + area_b - inter # 합집합 = 집합 A + 집합 B - 교집합 
    return float(inter / union) if union > 0 else 0.0   # IOU 계산

def _best_detection(
    zone_box: np.ndarray,
    detections: List[dict],
    iou_thr: float,     # iou_thr = _IOU_THRESHOLD
) -> Optional[dict]:
    """
    zone_box와 IoU ≥ iou_thr인 탐지 중 confidence가 가장 높은 탐지를 반환.
    없으면 None.

        "box":     box,
        "conf":    float(conf),
        "cls":     int(cls),
        "is_open": int(cls) == _CLS_OPEN,
    """
    best: Optional[dict] = None
    best_score = -1.0
    for det in detections:
        # detections의 각 대상과 zone_box 사이 IOU 비교
        iou = _iou(zone_box, det["box"])
        if iou >= iou_thr and det["conf"] > best_score:
            best_score = det["conf"]
            best       = {**det, "iou": round(iou, 4)}
    return best

# ──────────────────────────────────────────────────────────────────────────────
# DoorDetector
# ──────────────────────────────────────────────────────────────────────────────

class DoorDetector_By_Custom_Model:
    """
    파인튜닝된 YOLO 모델 기반 세탁기 문 상태 감지기.

    Parameters
    ----------
    config     : AppConfig 인스턴스
    model_path : custom_v1.pt 경로 (비어있으면 config.yolo.custom_model_path 사용)
    iou_thr    : 존-탐지 매칭 IoU 임계값 (기본 0.15)
    conf_thr   : YOLO 추론 confidence 임계값 (기본 0.25)
    """

    # YOLO 기반이므로 보정 불필요
    needs_calibration: bool = False

    # ── 변수 초기화 ────────────────────────────────────────────────────────

    def __init__(
        self,
        config: AppConfig,
    ) -> None:
        self.cfg        = config.detection
        self.iou_thr    = config.detection.iou_threshold
        self.conf_thr   = config.detection.confidence_threshold
        self.model_path = (
            getattr(config.yolo, "custom_model_path", config.yolo.model_path)
        )
        self._model = None   # lazy load (첫 detect_all 호출 시 로드)

    # ── 모델 lazy load ────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._model:     # detect_all 반복 호출해도 단 1번만 로드
            return

        if not self.model_path:
            raise RuntimeError(
                "[DoorDetector] 모델 경로가 설정되지 않았습니다.\n"
                "  main.py 실행 시 --custom 옵션을 추가하세요:\n"
                "    python main.py --custom models/yolo26n.pt"
            )

        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError(
                "[DoorDetector] ultralytics 패키지가 없습니다.\n"
                "  pip install ultralytics"
            )

        path = Path(self.model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"[DoorDetector] 모델 파일을 찾을 수 없습니다: {path.resolve()}\n"
                "  custom_v1.pt 경로를 확인해주세요."
            )

        log.info("[DoorDetector] 모델 로드 중: %s", path)
        self._model = YOLO(str(path))
        log.info("[DoorDetector] 모델 로드 완료")

    # ── 메인 추론: 전체 프레임 ────────────────────────────────────────────────

    def detect_all(
        self,
        frame: np.ndarray,
        zones,
        zone_stat=None,          # ← 기본값 None (보정값 없어도 호출 가능)
    ) -> Dict[int, Tuple[bool, float, dict]]:

        if frame is None or (hasattr(frame, "size") and frame.size == 0):
            return {
                z.zone_id: (False, 0.0, {"error": "빈 프레임"})
                for z in zones
            }

        self._load()

        # ── YOLO 추론 ────────────────────────────────────────────────────────
        results = self._model(frame, conf=self.conf_thr, verbose=False)[0]

        detections: List[dict] = []
        if results.boxes is not None and len(results.boxes):
            boxes = results.boxes.xyxy.cpu().numpy()
            confs = results.boxes.conf.cpu().numpy()
            clses = results.boxes.cls.cpu().numpy()
            for box, conf, cls in zip(boxes, confs, clses):
                detections.append({
                    "box":     box,
                    "conf":    float(conf),
                    "cls":     int(cls),
                    "is_open": int(cls) == self.cfg.cls_open,
                })

        n_det = len(detections)

        # ── 통계 사용 가능 여부 판단 ─────────────────────────────────────────
        # zone_stat이 없거나, 보정이 완료되지 않았으면 통계 검증 비활성화
        stat_ready = (
            zone_stat is not None
            and getattr(zone_stat, "is_finalized", False)
            and bool(getattr(zone_stat, "zone_statistics", {}))
        )

        # ── 존별 IoU 매칭 ────────────────────────────────────────────────────
        output: Dict[int, Tuple[bool, float, dict]] = {}

        for zone in zones:
            zone_box = np.array([zone.x1, zone.y1, zone.x2, zone.y2], dtype=float)
            best_detection = _best_detection(zone_box, detections, iou_thr=self.iou_thr)
            # ── 통계 계산 (보정값 있을 때만) ─────────────────────────────────
            if stat_ready:
                roi = zone.extract_roi(frame)
                roi_mean = float(roi.mean())
                # stats.trim_mean(roi.flatten(), proportiontocut=0.05)
                # float(roi.std())

                try:
                    pixel_normal = zone_stat.is_pixel_normal(zone.zone_id, roi)
                except (RuntimeError, KeyError):
                    # 해당 존의 통계가 없는 경우 방어
                    pixel_normal = None
            else:
                roi_mean = None
                pixel_normal = None  # None = 통계 없음, 판단 보류

            # ── 존별 판단 ────────────────────────────────────────────────────
            if best_detection is None:
                if pixel_normal is False:
                    # YOLO 미탐지 + 픽셀 비정상 → 열림으로 보완
                    is_open, conf_out = True, 0.0
                    cls_name = "Open(stat)"
                else:
                    # 통계 없음 or 정상 → 기본값 닫힘
                    is_open, conf_out = False, 0.0
                    cls_name = "Closed"

                debug = {
                    "matched":      False,
                    "is_open":      is_open,
                    "conf":         conf_out,
                    "iou":          0.0,
                    "cls":          self.cfg.cls_close,
                    "cls_name":     cls_name,
                    "n_detections": n_det,
                    "roi_mean":     roi_mean,
                    "pixel_normal": pixel_normal,
                    "stat_used":    stat_ready,   # 통계 사용 여부 로깅
                }
                output[zone.zone_id] = (is_open, conf_out, debug)

            else:
                is_open = best_detection["is_open"]
                conf    = best_detection["conf"]

                # 통계 있을 때만 신뢰도 보정
                if pixel_normal is not None:
                    if is_open and pixel_normal:
                        conf *= 0.5      # YOLO 열림 + 픽셀 정상 → 의심
                    elif not is_open and not pixel_normal:
                        conf *= 0.5      # YOLO 닫힘 + 픽셀 비정상 → 의심

                cls_name = "Open" if is_open else "Closed"
                debug = {
                    "matched":      True,
                    "is_open":      is_open,
                    "conf":         round(conf, 4),
                    "iou":          best_detection["iou"],
                    "cls":          best_detection["cls"],
                    "cls_name":     cls_name,
                    "box":          best_detection["box"].tolist(),
                    "n_detections": n_det,
                    "roi_mean":     roi_mean,
                    "pixel_normal": pixel_normal,
                    "stat_used":    stat_ready,
                }
                output[zone.zone_id] = (is_open, conf, debug)

        return output

    # ── 보정 메서드 (no-op: YOLO 모델은 보정 불필요) ─────────────────────
    @staticmethod
    def run_calibration(
        cap: cv2.VideoCapture,
        zone_mgr: ZoneManager,
        zone_stat:Zone_Statistic,
        config: AppConfig,
    ) -> bool:  # 성공 여부를 반환하도록 변경 (None -> bool)
        """
        초기 보정: N 프레임 동안 각 존의 특징 기준값 수집.
        보정 중에는 모든 문이 닫혀 있다고 가정.
        """
        CalibrationConfig = config.calibration
        warmup = CalibrationConfig.warmup_frames
        n_cal = CalibrationConfig.n_frames

        frame_count = 0
        cal_count = 0
        success = False

        zones = zone_mgr.get_zones()

        print(f"\n[보정] 초기화 중 (워밍업 {warmup}프레임 + 보정 {n_cal}프레임)...")
        print("  ※ 보정 동안 모든 세탁기 문이 닫혀 있는지 확인하세요.\n")

        win_name = "Calibration... (Please close all doors)"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

        while cal_count < n_cal:
            ret, frame = cap.read()
            if not ret:
                print("[경고] 보정 중 프레임 읽기 실패. 카메라 연결을 확인하세요.")
                break

            frame_count += 1
            
            # 1. 워밍업 단계 (카메라 밝기/초점 자동 조절 대기)
            if frame_count <= warmup:
                disp = frame.copy()
                msg = f"Warmup {frame_count}/{warmup}"
                cv2.putText(disp, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                cv2.imshow(win_name, disp)
                cv2.waitKey(1)
                continue

            # 2. 실제 보정 단계 (데이터 수집)
            cal_count += 1
            progress = int(cal_count / n_cal * 100)

            # [핵심 추가] 각 존(Zone)별로 현재 프레임의 이미지를 누적!
            for zone in zones:
                roi = zone.extract_roi(frame) # 세탁기 영역만 크롭
                # 이전 설계했던 update_zone_statistic 함수 호출
                zone_stat.update_zone_statistic(zone.zone_id,roi)
            
            # 시각화 (프로그레스 바)
            disp = frame.copy()
            progress = float(cal_count / n_cal)
            progress_bar_width = int(frame.shape[1] * progress)
            msg = f"Recalibration ... [{cal_count}/{n_cal}]: {progress*100:.2f}%"
            cv2.rectangle(disp, (0, frame.shape[0] - 18), (progress_bar_width, frame.shape[0]), (50, 200, 50), -1)
            cv2.putText(disp, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 255), 2)
            cv2.imshow(win_name, disp)

            # q 또는 ESC 누르면 강제 종료
            if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
                print("[경고] 사용자에 의해 보정이 중단되었습니다.")
                break

        # 창 닫기 (오류 방지를 위해 try-except로 감싸는 것이 좋음)
        try:
            cv2.destroyWindow(win_name)
        except cv2.error:
            pass

        # 3. 보정 완료 및 최종 연산 처리
        if cal_count == n_cal:
            # [핵심 추가] 수집된 이미지들의 평균값을 내어 최종 배경 이미지 확정
            zone_stat.set_statistics()
            zone_stat.save_statistics_json()
            print(f"[보정] 성공적으로 완료되었습니다! ({cal_count}프레임 수집)\n")
            success = True
        else:
            print(f"[보정] 실패! 데이터가 충분하지 않습니다.\n")
            # 실패 시 초기화 (찌꺼기 데이터 제거)
            zone_stat.reset_statistics

        return success