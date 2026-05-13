"""
src/visualizer.py
=================
OpenCV 기반 실시간 시각화 모듈

렌더링 요소:
  - 세탁기 존 테두리 + 라벨 + 상태 색상
  - Hough 원 감지 결과 표시
  - YOLO26n 사람 탐지 바운딩 박스
  - 오른쪽 상태 패널: 2D 배열 + 층별 요약
  - 상태 히스토리 막대 그래프 (mini 스파크라인)
  - FPS 및 장치 정보 표시
"""

from __future__ import annotations
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from .config import AppConfig, DisplayConfig
from .state_tracker import DoorState, MachineDoorTracker
from .yolo_handler import YOLOResult
from .zone_manager import ZoneDef


# ---------------------------------------------------------------------------
# 색상 팔레트 (BGR)
# ---------------------------------------------------------------------------
class _C:
    DC = DisplayConfig
    WHITE  = (255, 255, 255)
    BLACK  = (0, 0, 0)
    GRAY   = (120, 120, 120)
    D_GRAY = (50, 50, 50)

    OPEN   = DC.color_open    # 주황 → 열림
    CLOSED = DC.color_closed     # 녹색 → 닫힘
    TRANS  = DC.color_trans    # 노랑 → 전환 중
    UNKNOWN = DC.color_unknown   # 회색 → 불명
    CIRCLE = DC.color_circle    # 원 윤곽선 색
    PERSON = DC.color_person    # 사람 탐지


def _state_color(state: DoorState) -> Tuple[int, int, int]:
    if state == DoorState.OPEN:
        return _C.OPEN
    if state == DoorState.CLOSED:
        return _C.CLOSED
    if state in (DoorState.OPENING, DoorState.CLOSING):
        return _C.TRANS
    return _C.UNKNOWN


def _state_label(state: DoorState) -> str:
    return {
        DoorState.OPEN:    "OPEN",
        DoorState.CLOSED:  "CLOSE",
        DoorState.OPENING: "OPENING",
        DoorState.CLOSING: "CLOSING",
        DoorState.UNKNOWN: "UNKNOWN",
    }.get(state, "UNKNOWN")


# ---------------------------------------------------------------------------
# 투명 오버레이 유틸
# ---------------------------------------------------------------------------

def _alpha_rect(
    canvas: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    color: Tuple[int, int, int],
    alpha: float,
) -> None:
    """반투명 직사각형 그리기"""
    h, w = canvas.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x1 >= x2 or y1 >= y2:
        return
    overlay = canvas[y1:y2, x1:x2].copy()
    overlay[:] = color
    cv2.addWeighted(overlay, alpha, canvas[y1:y2, x1:x2], 1 - alpha, 0,
                    canvas[y1:y2, x1:x2])


def _put_text_bg(
    canvas: np.ndarray,
    text: str,
    x: int, y: int,
    font=cv2.FONT_HERSHEY_SIMPLEX,
    scale: float = 0.55,
    color: Tuple[int, int, int] = _C.WHITE,
    thickness: int = 1,
    bg_color: Optional[Tuple[int, int, int]] = (0, 0, 0),
    bg_alpha: float = 0.55,
) -> None:
    """배경 박스가 있는 텍스트 렌더링"""
    (tw, th), bl = cv2.getTextSize(text, font, scale, thickness)
    pad = 3
    if bg_color is not None:
        _alpha_rect(canvas, x - pad, y - th - pad, x + tw + pad, y + bl + pad,
                    bg_color, bg_alpha)
    cv2.putText(canvas, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Visualizer
# ---------------------------------------------------------------------------

class Visualizer:
    """실시간 화면 렌더러"""

    FONT = cv2.FONT_HERSHEY_SIMPLEX

    def __init__(self, config: AppConfig) -> None:
        self.dcfg = config.display
        self._fps_buf: deque[float] = deque(maxlen=30)
        self._last_ts: float = time.time()
        self._device: str = config.get_device()

    # ── 메인 렌더 함수 ────────────────────────────────────────────────────────

    def render(
        self,
        frame: np.ndarray,
        zones: List[ZoneDef],
        states: Dict[int, DoorState],
        trackers: Dict[int, MachineDoorTracker],
        yolo_result: Optional[YOLOResult],
        debug_map: Optional[Dict[int, dict]],
        status_array: List[List[Optional[bool]]],
    ) -> np.ndarray:
        """
        모든 시각 요소를 합성한 최종 프레임 반환.
        원본 frame을 수정하지 않음 (복사본 사용).
        """
        canvas = frame.copy()
        cfg = self.dcfg

        # 1. YOLO 사람 탐지 박스
        if yolo_result and cfg.show_yolo_detections:
            self._draw_persons(canvas, yolo_result)

        # 2. 세탁기 존 박스 + 상태 레이블
        if cfg.show_zones:
            self._draw_zones(canvas, zones, states, debug_map, trackers)

        # 3. FPS / 장치 정보
        self._draw_fps(canvas)

        # 4. 상태 패널 (오른쪽)
        if cfg.show_status_panel:
            canvas = self._draw_status_panel(canvas, status_array, states,
                                              trackers, zones)

        return canvas

    # ── YOLO 탐지 ────────────────────────────────────────────────────────────

    def _draw_persons(self, canvas: np.ndarray, result: YOLOResult) -> None:
        for det in result.persons():
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(canvas, (x1, y1), (x2, y2), _C.PERSON, 2)
            lbl = f"Person"
            if det.track_id is not None:
                lbl += f" #{det.track_id}"
            _put_text_bg(canvas, lbl, x1 + 3, y1 - 6,
                         scale=0.50, color=_C.WHITE, bg_color=(120, 20, 100))

    # ── 세탁기 존 ────────────────────────────────────────────────────────────

    def _draw_zones(
        self,
        canvas: np.ndarray,
        zones: List[ZoneDef],
        states: Dict[int, DoorState],
        debug_map: Optional[Dict[int, dict]],
        trackers: Dict[int, MachineDoorTracker],
    ) -> None:
        for zone in zones:
            state = states.get(zone.zone_id, DoorState.UNKNOWN)
            color = _state_color(state)
            thick = 3 if state in (DoorState.OPEN, DoorState.CLOSED) else 2

            # 존 테두리
            cv2.rectangle(canvas, (zone.x1, zone.y1), (zone.x2, zone.y2),
                          color, thick)

            # 존 ID 라벨
            lbl = f"{zone.label}: {_state_label(state)}"
            _put_text_bg(canvas, lbl, zone.x1 + 4, zone.y1 + 20,
                         scale=self.dcfg.font_scale, color=color,
                         bg_color=_C.D_GRAY, bg_alpha=0.70)

            # 상태 히스토리 스파크라인
            tracker = trackers.get(zone.zone_id)
            if tracker and self.dcfg.show_state_history:
                self._draw_sparkline(canvas, tracker, zone)

            # 디버그 수치
            if self.dcfg.show_debug_info and debug_map:
                dbg = debug_map.get(zone.zone_id, {})
                if dbg:
                    self._draw_debug_overlay(canvas, dbg, zone)

            # Hough 원 표시
            if self.dcfg.show_circles and debug_map:
                dbg = debug_map.get(zone.zone_id, {})
                circle = dbg.get("circle") if dbg else None
                if circle is not None:
                    cx, cy, r = circle
                    # 존 로컬 좌표 → 전체 프레임 좌표 변환
                    # (도어 검출은 리사이즈된 220x220에서 수행됨)
                    proc_w, proc_h = 220, 220
                    zone_w = zone.x2 - zone.x1
                    zone_h = zone.y2 - zone.y1
                    scale_x = zone_w / proc_w
                    scale_y = zone_h / proc_h
                    global_cx = zone.x1 + int(cx * scale_x)
                    global_cy = zone.y1 + int(cy * scale_y)
                    global_r  = int(r * (scale_x + scale_y) / 2)
                    cv2.circle(canvas,
                               (global_cx, global_cy), global_r,
                               _C.CIRCLE, 1, cv2.LINE_AA)

    def _draw_sparkline(
        self,
        canvas: np.ndarray,
        tracker: MachineDoorTracker,
        zone: ZoneDef,
    ) -> None:
        """존 하단에 미니 히스토리 바 그래프"""
        history = tracker.get_history()
        if not history:
            return
        n = len(history)
        bar_h = 6
        bar_w = zone.x2 - zone.x1
        seg_w = max(1, bar_w // n)
        base_y = zone.y2 - 2
        for i, val in enumerate(history):
            color = _C.OPEN if val else _C.CLOSED
            bx1 = zone.x1 + i * seg_w
            bx2 = bx1 + seg_w
            cv2.rectangle(canvas, (bx1, base_y - bar_h), (bx2, base_y),
                          color, -1)

    def _draw_debug_overlay(
        self,
        canvas: np.ndarray,
        dbg: dict,
        zone: ZoneDef,
    ) -> None:
        """존 내부에 디버그 수치 표시 (v3 YOLO 키 기준)"""
        matched  = dbg.get("matched", False)
        cls_name = dbg.get("cls_name", "Closed")
        conf     = dbg.get("conf", 0.0)
        iou      = dbg.get("iou", 0.0)
        n_det    = dbg.get("n_detections", 0)

        lines = [
            f"{cls_name}" + (" ✓" if matched else " —"),  # 클래스명
            f"conf:{conf:.2f}",                               # YOLO confidence
            f"iou:{iou:.2f}",                                 # 존-박스 IoU
            f"det:{n_det}",                                   # 탐지된 총 개수
        ]
        # 열림이면 주황, 닫힘이면 초록으로 첫 줄 강조
        first_color = _C.OPEN if cls_name == "Open" else _C.CLOSED

        for i, line in enumerate(lines):
            y = zone.y1 + 38 + i * 16
            color = first_color if i == 0 else _C.WHITE
            _put_text_bg(canvas, line, zone.x1 + 4, y,
                         scale=0.42, color=color, bg_alpha=0.55)

    # ── FPS ─────────────────────────────────────────────────────────────────

    def _draw_fps(self, canvas: np.ndarray) -> None:
        now = time.time()
        dt = now - self._last_ts
        self._last_ts = now
        if dt > 0:
            self._fps_buf.append(1.0 / dt)
        fps = float(np.mean(self._fps_buf)) if self._fps_buf else 0.0
        h = canvas.shape[0]
        text = f"FPS: {fps:.1f}  [{self._device.upper()}]"
        _put_text_bg(canvas, text, 10, h - 12,
                     scale=0.55, color=_C.WHITE, bg_color=_C.D_GRAY)

    # ── 상태 패널 ────────────────────────────────────────────────────────────

    def _draw_status_panel(
        self,
        canvas: np.ndarray,
        status_array: List[List[Optional[bool]]],
        states: Dict[int, DoorState],
        trackers: Dict[int, MachineDoorTracker],
        zones: List[ZoneDef],
    ) -> np.ndarray:
        """
        오른쪽에 반투명 상태 패널 렌더링.
        2D 배열 시각화 + 층별 요약 포함.
        """
        h, w = canvas.shape[:2]
        pw = self.dcfg.panel_width

        # 캔버스 확장
        extended = np.zeros((h, w + pw, 3), dtype=np.uint8)
        extended[:, :w] = canvas
        panel = extended[:, w:]
        panel[:] = (28, 28, 32)

        # ── 패널 헤더 ──────────────────────────────────────────────────────
        y = 30
        cv2.putText(panel, "LAUNDRY STATUS", (10, y),
                    self.FONT, 0.60, _C.WHITE, 1, cv2.LINE_AA)
        y += 8
        cv2.line(panel, (8, y), (pw - 8, y), _C.GRAY, 1)
        y += 20

        # ── 2D 배열 텍스트 출력 ────────────────────────────────────────────
        cv2.putText(panel, "2D Array:", (10, y),
                    self.FONT, 0.50, _C.GRAY, 1, cv2.LINE_AA)
        y += 18

        for floor_idx, row in enumerate(status_array):
            floor_num = len(status_array) - floor_idx  # 2, 1
            prefix = f"  {floor_num}F ["
            suffix = "]"
            values = ", ".join(
                "True " if v is True else ("False" if v is False else "None ")
                for v in row
            )
            line = prefix + values + suffix
            c = _C.GRAY
            cv2.putText(panel, line, (10, y),
                        self.FONT, 0.46, c, 1, cv2.LINE_AA)
            y += 18

        y += 10
        cv2.line(panel, (8, y), (pw - 8, y), _C.GRAY, 1)
        y += 18

        # ── 세탁기 그리드 시각화 ──────────────────────────────────────────
        cv2.putText(panel, "Machine Grid:", (10, y),
                    self.FONT, 0.50, _C.GRAY, 1, cv2.LINE_AA)
        y += 20

        box_size = min(52, (pw - 30) // max(
            max((len(r) for r in status_array), default=1), 1
        ))
        gap = 8
        x_start = 14

        for floor_idx, row in enumerate(status_array):
            floor_num = len(status_array) - floor_idx
            # 층 레이블
            cv2.putText(panel, f"{floor_num}F", (x_start - 4, y + box_size // 2 + 4),
                        self.FONT, 0.42, _C.GRAY, 1, cv2.LINE_AA)
            bx = x_start + 24
            for col_idx, val in enumerate(row):
                # 해당 존 ID 찾기
                zone_id_match = None
                for zone in zones:
                    if zone.floor == floor_num and zone.position == col_idx:
                        zone_id_match = zone.zone_id
                        break

                state = states.get(zone_id_match, DoorState.UNKNOWN) \
                    if zone_id_match is not None else DoorState.UNKNOWN
                color = _state_color(state)

                # 박스 그리기
                bx1, by1 = bx, y
                bx2, by2 = bx + box_size, y + box_size
                cv2.rectangle(panel, (bx1, by1), (bx2, by2), color, -1)
                cv2.rectangle(panel, (bx1, by1), (bx2, by2), _C.D_GRAY, 1)

                # 상태 텍스트
                slbl = "OPEN" if val is True else ("CLOSE" if val is False else "UNKNOWN")
                (tw, _), _ = cv2.getTextSize(slbl, self.FONT, 0.35, 1)
                tx = bx1 + (box_size - tw) // 2
                ty = by1 + box_size // 2 + 5
                cv2.putText(panel, slbl, (tx, ty),
                            self.FONT, 0.35, _C.WHITE, 1, cv2.LINE_AA)

                # 머신 번호
                num = f"{floor_num}F-{col_idx + 1}"
                (nw, _), _ = cv2.getTextSize(num, self.FONT, 0.32, 1)
                nx = bx1 + (box_size - nw) // 2
                cv2.putText(panel, num, (nx, by1 + 12),
                            self.FONT, 0.32, _C.WHITE, 1, cv2.LINE_AA)

                bx += box_size + gap
                if bx + box_size > pw - 10:
                    break  # 패널 너비 초과 방지

            y += box_size + gap + 4

        # ── 요약 ─────────────────────────────────────────────────────────
        y += 6
        cv2.line(panel, (8, y), (pw - 8, y), _C.GRAY, 1)
        y += 18
        total = sum(len(r) for r in status_array)
        open_cnt = sum(1 for r in status_array for v in r if v is True)
        closed_cnt = sum(1 for r in status_array for v in r if v is False)
        cv2.putText(panel, f"Total: {total}  Open: {open_cnt}  Closed: {closed_cnt}",
                    (10, y), self.FONT, 0.46, _C.WHITE, 1, cv2.LINE_AA)

        # 패널을 확장 캔버스에 복사
        extended[:, w:] = panel
        return extended
