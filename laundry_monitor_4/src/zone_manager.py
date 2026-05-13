"""
src/zone_manager.py
===================
세탁기 존(Zone) 구성 관리 모듈

- ZoneDef: 개별 세탁기 존 데이터 클래스
- ZoneManager: 존 저장/로드/자동감지/시각적 설정 도구
"""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, List, Optional, Tuple
from datetime import datetime, timezone

import math
import os
import cv2
import numpy as np

from .config import AppConfig


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass
class ZoneDef:
    """개별 세탁기 존 정의"""
    zone_id: int            # 고유 ID (0부터 순서대로)
    floor: int              # 1 또는 2 (1층/2층)
    position: int           # 해당 층에서 왼쪽부터 0-indexed
    x1: int                 # ROI 좌상단 x
    y1: int                 # ROI 좌상단 y
    x2: int                 # ROI 우하단 x
    y2: int                 # ROI 우하단 y
    label: str = ""         # 표시 라벨 (예: "2F-1")

    @property
    def cx(self) -> int:
        return (self.x1 + self.x2) // 2

    @property
    def cy(self) -> int:
        return (self.y1 + self.y2) // 2

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def extract_roi(self, frame: np.ndarray, pad: int = 0) -> np.ndarray:
        """프레임에서 ROI 영역 추출 (패딩 포함)"""
        h, w = frame.shape[:2]
        x1 = max(0, self.x1 - pad)
        y1 = max(0, self.y1 - pad)
        x2 = min(w, self.x2 + pad)
        y2 = min(h, self.y2 + pad)
        return frame[y1:y2, x1:x2].copy()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ZoneDef:
        return cls(**d)


# ---------------------------------------------------------------------------
# ZoneManager
# ---------------------------------------------------------------------------

class ZoneManager:
    """
    존 구성 관리자.
    - 존 파일(JSON) 저장/로드
    - 마우스 클릭 기반 인터랙티브 설정
    - Hough Circle 기반 자동 감지
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.zones: List[ZoneDef] = []
        self._zones_path = Path(config.zones_file)

    # ── 로드 / 저장 ─────────────────────────────────────────────────────────

    def load(self) -> bool:
        """저장된 존 JSON을 로드. 성공 시 True 반환."""
        if not self._zones_path.exists():
            logger.warning("존 설정 파일 없음: %s", self._zones_path)
            return False
        try:
            data = json.loads(self._zones_path.read_text(encoding="utf-8"))
            self.zones = [ZoneDef.from_dict(z) for z in data["zones"]]
            logger.info("존 %d개 로드 완료: %s", len(self.zones), self._zones_path)
            return True
        except Exception as e:
            logger.error("존 로드 실패: %s", e)
            return False

    def save(self) -> None:
        """현재 존 설정을 JSON으로 저장."""
        self._zones_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"zones": [z.to_dict() for z in self.zones]}
        self._zones_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("존 %d개 저장 완료: %s", len(self.zones), self._zones_path)

    # ── 존 목록 접근 ─────────────────────────────────────────────────────────

    def get_zones(self) -> List[ZoneDef]:
        return self.zones

    def get_zones_by_floor(self, floor: int) -> List[ZoneDef]:
        """지정 층의 존 목록을 위치 순서대로 반환"""
        return sorted(
            [z for z in self.zones if z.floor == floor],
            key=lambda z: z.position
        )

    def get_status_array(
        self, states: dict[int, bool]
    ) -> List[List[Optional[bool]]]:
        """
        states: {zone_id: is_open}
        반환값: [[2층 세탁기 상태], [1층 세탁기 상태]]
                 True = 문 열림, False = 문 닫힘

        구조 예시 (3x3):
        [[2F_L, 2F_M, 2F_R],
         [1F_L, 1F_M, 1F_R]]
        """
        result = []
        # 층 번호 내림차순 (2층 먼저, 1층 나중)
        for floor in sorted(
            set(z.floor for z in self.zones), reverse=True
        ):
            row = []
            for zone in self.get_zones_by_floor(floor):
                row.append(states.get(zone.zone_id, None))
            result.append(row)
        return result

    # ── 인터랙티브 마우스 설정 ────────────────────────────────────────────────

    def interactive_setup(self, frame: np.ndarray) -> bool:
        MIN_ROI_SIZE = self.config.layout.MIN_ROI_SIZE
        cfg_layout = self.config.layout
        machines_per_floor = cfg_layout.machines_per_floor
        total = sum(machines_per_floor)
        floors = range(cfg_layout.n_floors, 0, -1)
        floor_sequence = [
            (floor, pos)
            for fi, floor in enumerate(floors)
            for pos in range(machines_per_floor[fi])
        ]

        collected: List[Tuple[int, int, int, int]] = []
        drag_start: Optional[Tuple[int, int]] = None
        drag_current: Optional[Tuple[int, int]] = None
        is_dragging = False

        h, w = frame.shape[:2]  # ← w를 클램프에 활용

        def clamp_point(x: int, y: int) -> Tuple[int, int]:
            """좌표를 프레임 경계 내로 제한."""
            return (
                max(0, min(x, w - 1)),
                max(0, min(y, h - 1)),
            )

        def mouse_cb(event, x, y, flags, _param): 
            # _cb 는 _callback의 약자 이벤트 발생시 호출되는 함수에 붙이는 수식어.
            # flags와 _param 들은 나중에 유용한 기능을 추가할 수 있어 유지함.
            nonlocal drag_start, drag_current, is_dragging
            cx, cy = clamp_point(x, y)  # ← 클램프 적용
            if event == cv2.EVENT_LBUTTONDOWN:
                drag_start = (cx, cy)
                is_dragging = True
            elif event == cv2.EVENT_MOUSEMOVE and is_dragging:
                drag_current = (cx, cy)
            elif event == cv2.EVENT_LBUTTONUP and is_dragging:
                if drag_start:
                    x1 = min(drag_start[0], cx)
                    y1 = min(drag_start[1], cy)
                    x2 = max(drag_start[0], cx)
                    y2 = max(drag_start[1], cy)
                    if (x2 - x1) > MIN_ROI_SIZE and (y2 - y1) > MIN_ROI_SIZE:
                        collected.append((x1, y1, x2, y2))
                drag_start = None
                drag_current = None
                is_dragging = False
            elif event == cv2.EVENT_RBUTTONDOWN:
                if collected:
                    collected.pop()

        win = "존 설정 (드래그로 ROI 지정 | 우클릭: 취소 | Enter/q: 완료)"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(win, mouse_cb)

        while True:
            disp = frame.copy()
            idx = len(collected)

            for i, (x1, y1, x2, y2) in enumerate(collected):
                floor, pos = floor_sequence[i]
                color = self.config.layout.COLOR_1F if floor == 1 else self.config.layout.COLOR_2F
                cv2.rectangle(disp, (x1, y1), (x2, y2), color, 2)
                lbl = f"{floor}F-{pos + 1}"
                cv2.putText(disp, lbl, (x1 + 4, y1 + 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

            if is_dragging and drag_start and drag_current:
                cv2.rectangle(disp, drag_start, drag_current, self.config.layout.COLOR_DRAG, 1)

            if idx < total:
                floor, pos = floor_sequence[idx]
                guide = (
                    f"[{idx + 1}/{total}] {floor}층 {pos + 1}번 세탁기 ROI 드래그 | 우클릭: 취소 | Enter/q: 완료"
                )
            else:
                guide = "모든 존 지정 완료. Enter 또는 q 로 저장."
            cv2.putText(disp, guide, (10, h - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.config.layout.COLOR_DRAG, 1)

            cv2.imshow(win, disp)
            key = cv2.waitKey(20) & 0xFF
            KEY_ENTER = 13 # 코드 번호
            if key == KEY_ENTER and len(collected) == total: # Enter는 모두 완료되었을 때만 작동
                break
            elif key == ord('q'): # q는 언제든 강제 종료
                break
            
            if key == ord('r'):
                collected.clear()

        cv2.destroyWindow(win)

        if len(collected) != total:
            msg = f"[WARNING] src.zone_manager: 존 지정 불완전: 전체 {total}개 중 {len(collected)}개"
            raise RuntimeError(msg)

        self.zones = []
        for zone_id, ((x1, y1, x2, y2), (floor, pos)) in enumerate(
            zip(collected, floor_sequence)
        ):
            self.zones.append(ZoneDef(
                zone_id=zone_id,
                floor=floor,
                position=pos,
                x1=x1, y1=y1, x2=x2, y2=y2,
                label=f"{floor}F-{pos + 1}",
            ))
        self.save()
        return True

@dataclass # 하나의 존에 대한 정규분포 통계량 제공
class _Zone_NormalDistribution:
    samples: int = 0
    total_pixels: int = 0
    pixel_sum: float = 0.0
    pixel_sum_sq: float = 0.0
    min_value: float = math.inf # 양의 무한대
    max_value: float = -math.inf # 음의 무한대
    last_shape: Optional[tuple[int, ...]] = None


    def update(self, roi: np.ndarray) -> None:
        # roi는 Zone 영역만 크롭된 픽셀 배열이다.
        arr = np.asarray(roi)
        if arr.size == 0:
            raise ValueError("roi must not be empty.")

        values = arr.astype(np.float64, copy=False).reshape(-1)
        # astype은 넘파이의 타입 변환자
        # __.reshape(row,col)은 n by m 차원 행렬을 원하는 행(row)과 열(col)의 수로 재배열
        # __.reshape(-1)은 1차워 축약

        self.samples += 1
        self.total_pixels += int(values.size)
        self.pixel_sum += float(values.sum())
        self.pixel_sum_sq += float(np.dot(values, values))

        # 재귀의 원리를 이용한 정의
        self.min_value = min(self.min_value, float(values.min()))
        self.max_value = max(self.max_value, float(values.max()))

        self.last_shape = tuple(arr.shape)

    # 하나의 존의 통계량 구함. 
    def compute_statistic(self, zone_id: int) -> dict[str, Any]:
        if self.total_pixels == 0:
            raise RuntimeError(f"Zone {zone_id} has no accumulated pixels.")

        # 평균
        mean = self.pixel_sum / self.total_pixels
        # 분산
        variance = max((self.pixel_sum_sq / self.total_pixels) - (mean * mean), 0.0)
        #표준편차
        standard = math.sqrt(variance)

        return {
            "zone_id": zone_id,
            "samples": self.samples,
            "total_pixels": self.total_pixels,

            # 평균, 표준편차, 최솟값, 최댓값
            "mean": mean,
            "std": standard,
            "min": self.min_value,
            "max": self.max_value,

            # 정규분포는 (평균 - 3*표준편차)와 (평균 + 3*표준편차) 사이에 데이터의 99.7%가 들어 있다.
            "lower_bound": mean - (3.0 * standard),
            "upper_bound": mean + (3.0 * standard),

            "shape": list(self.last_shape) if self.last_shape is not None else None,
        }

class Zone_Statistic:
    def __init__(self, zone_statistics_path: str | Path = "/Users/kimjiwon/Documents/개발/laundry_monitor_4/configs/zones_copy.json") -> None:
        self.zone_statistics_path = Path(zone_statistics_path)
        self._zone_Archive: dict[int, _Zone_NormalDistribution] = {}  # 존 아이디에 ROI 픽셀 분석 정보 저장
        self.zone_statistics: dict[int, dict[str, Any]] = {} # 존 아이디와 통계를 딕셔너리로 매핑 
        
        self.saved_at: Optional[str] = None # 마지막 보정이 언제인지 관리
        self.is_finalized: bool = False

        self.zone_manager = ZoneManager(AppConfig())
        self.zone_manager.load()

    def _get_zone_def(self, zone_id: int) -> ZoneDef:
        """ZoneManager에서 zone_id에 해당하는 ZoneDef를 찾아 반환."""
        for z in self.zone_manager.get_zones():
            if z.zone_id == zone_id:
                return z
        raise KeyError(f"zone_id={zone_id} 가 ZoneManager에 없습니다.")
    
    # 보정 기록 초기화
    def reset_statistics(self) -> None:
        self._zone_Archive.clear()
        self.zone_statistics.clear()
        self.saved_at = None
        self.is_finalized = False

    # 딕셔너리에서 모든 존을 관리하면서, 원하는 존을 개별적으로 update하는 기능
    def update_zone_statistic(self, zone_id: int, roi: np.ndarray) -> None:
        """Accumulate ROI statistics for one zone."""
        if self.is_finalized:
            print("Calibration is already finalized. Call reset_statistics()")
            self.reset_statistics()
        
        
         # zone_id가 ZoneManager에 실제로 존재하는지 검증
        self._get_zone_def(zone_id)

        arr = np.asarray(roi)
        if arr.ndim not in (2, 3):
            raise ValueError("roi must be a 2D grayscale or 3D color array.")
        if arr.size == 0:
            raise ValueError("roi must not be empty.")
        if not np.issubdtype(arr.dtype, np.number):
            raise TypeError("roi must contain numeric values.")

        self._zone_Archive.setdefault(zone_id, _Zone_NormalDistribution()).update(arr)    

    # 보정행위가 아니라 update가 끝난 각 존에 대해 통계치 계산한 후 zone_id와 연결하는 딕셔너리를 생성
    def set_statistics(self) -> None:
        """Compute final reference statistics for every accumulated zone."""
        if not self._zone_Archive:
            raise RuntimeError("No calibration samples have been accumulated.")

        self.zone_statistics = {
            zone_id: self._zone_Archive[zone_id].compute_statistic(zone_id)
            for zone_id in sorted(self._zone_Archive)
        }

        self.saved_at = datetime.now(timezone.utc).isoformat() # 국제 표준: 2026-05-03T05:07:10.123456+00:00
        self.is_finalized = True

    # 딕셔너리에서 모든 존에 대한 통계치를 json 파일을 만들어 저장
    def save_statistics_json(self) -> None:
        """Save final reference statistics data to disk."""
        if not self.is_finalized:
            raise RuntimeError("statistics must be finalized before saving1.")
        if not self.zone_statistics:
            raise RuntimeError("statistics must be finalized before saving2.")
        
        # 전송의 목적이 되는 실제 데이터가 payload다.
        payload = {
            "version": 1,
            "saved_at": self.saved_at,
            "zones": {str(zone_id): statistic for zone_id, statistic in self.zone_statistics.items()},
        }

        self.zone_statistics_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.zone_statistics_path.with_suffix(self.zone_statistics_path.suffix + ".tmp")

        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)

        os.replace(temp_path, self.zone_statistics_path)

    def load_statistics(self) -> bool:
        """
        Load calibration data from disk.

        Returns:
            bool: True if loading succeeded, False otherwise.
        """
        if not self.zone_statistics_path.exists():
            return False
        
        required_keys = {
            "zone_id", "samples", "total_pixels",
            "mean", "std", "min", "max",
            "lower_bound", "upper_bound", "shape",
        }

        try:
            with self.zone_statistics_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)

            if payload.get("version") != 1:
                return False

            raw_zones = payload.get("zones")
            if not isinstance(raw_zones, dict) or not raw_zones:
                return False

            loaded: dict[int, dict[str, Any]] = {}

            for zone_key, stats in raw_zones.items():
                if not isinstance(stats, dict) or not required_keys.issubset(stats):
                    return False
                zone_id = int(zone_key)
                loaded[zone_id] = {
                    "zone_id": int(stats["zone_id"]),
                    "samples": int(stats["samples"]),
                    "total_pixels": int(stats["total_pixels"]),
                    "mean": float(stats["mean"]),
                    "std": float(stats["std"]),
                    "min": float(stats["min"]),
                    "max": float(stats["max"]),
                    "lower_bound": float(stats["lower_bound"]),
                    "upper_bound": float(stats["upper_bound"]),
                    "shape": list(stats["shape"]) if stats["shape"] is not None else None,
                }

        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False

        self._zone_Archive.clear()
        self.zone_statistics = loaded
        self.saved_at = payload.get("saved_at")
        self.is_finalized = True
        return True
    
    # ── 편의 접근자 ──────────────────────────────────────────────────────────
    def get_zone_statistic(self, zone_id: int) -> Optional[dict[str, Any]]:
        """단일 Zone의 통계 반환. 캘리브레이션 미완료 시 None."""
        return self.zone_statistics.get(zone_id)

    ## 아직 활용 사례 수정중.
    def is_pixel_normal(self, zone_id: int, roi: np.ndarray) -> bool:
        """
        pixel_value 스칼라 대신 ROI 배열 전체를 받아서
        평균과 std를 동시에 검증
        """
        stats = self.get_zone_statistic(zone_id)
        if stats is None:
            raise RuntimeError(f"zone_id={zone_id} 캘리브레이션 데이터 없음.")

        current_mean = float(roi.mean())
        current_std  = float(roi.std())

        mean_normal = stats["lower_bound"] <= current_mean <= stats["upper_bound"]

        # std도 캘리브레이션 기준값의 절반~2배 범위 내면 정상
        # 너무 균일(어둠)하거나 너무 복잡(격렬한 움직임)하면 비정상
        cal_std = stats["std"]
        std_normal = (cal_std * 0.3) <= current_std <= (cal_std * 3.0)

        return mean_normal and std_normal