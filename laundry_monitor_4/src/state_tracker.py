"""
src/state_tracker.py
====================
시계열 상태 추적 모듈

프레임 단위 원시(raw) 감지 결과를 받아
시간적으로 안정된 확정 상태(stable state)를 출력.

핵심 메커니즘:
  1. 슬라이딩 윈도우 다수결 투표
     - 최근 N 프레임의 is_open 투표 비율이 threshold 초과 → 열림 확정
  2. 상태 기계 (State Machine) 디바운싱
     - CLOSED → OPENING → OPEN → CLOSING → CLOSED 전이
     - 새 상태를 최소 debounce_frames 연속 감지 후 전환
     - 순간적 노이즈로 인한 flicker 방지
  3. 신뢰도 가중 투표
     - confidence 낮은 프레임의 투표 가중치를 줄임
"""

from __future__ import annotations
import logging
import time
from collections import deque
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import AppConfig, TrackingConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 상태 열거형
# ---------------------------------------------------------------------------

class DoorState(Enum):
    UNKNOWN    = auto()   # 초기/판단 불가
    CLOSED     = auto()   # 문 닫힘
    OPENING    = auto()   # 열리는 중 (전환 상태)
    OPEN       = auto()   # 문 열림
    CLOSING    = auto()   # 닫히는 중 (전환 상태)

    def is_open(self) -> bool:
        return self in (DoorState.OPEN, DoorState.OPENING)

    def is_stable(self) -> bool:
        return self in (DoorState.OPEN, DoorState.CLOSED)

    def to_bool(self) -> Optional[bool]:
        """2D 배열 출력용: True=열림, False=닫힘, None=불확실"""
        if self == DoorState.OPEN:
            return True
        if self == DoorState.CLOSED:
            return False
        return None


# ---------------------------------------------------------------------------
# 단일 머신 상태 추적기
# ---------------------------------------------------------------------------

class MachineDoorTracker:
    """
    한 세탁기의 문 상태를 시계열로 추적.
    """

    def __init__(self, cfg: TrackingConfig, zone_id: int) -> None:
        self.cfg = cfg
        self.zone_id = zone_id

        # 슬라이딩 윈도우: (is_open, confidence) 튜플
        self._window: deque[Tuple[bool, float]] = deque(maxlen=cfg.state_window)

        # 상태 기계
        self._state = DoorState.UNKNOWN
        self._prev_stable = DoorState.UNKNOWN
        self._new_state_count = 0       # 현재 새 상태 연속 카운터
        self._transition_count = 0      # 전환 상태 유지 카운터

        # 통계
        self.state_change_times: List[float] = []  # 상태 변화 타임스탬프
        self.total_open_frames: int = 0
        self.total_frames: int = 0

    # ── 업데이트 ─────────────────────────────────────────────────────────────

    def update(
        self, raw_is_open: bool, confidence: float
    ) -> DoorState:
        """
        새 감지 결과로 상태 업데이트.
        반환: 현재 확정 상태
        """
        self.total_frames += 1
        if raw_is_open:
            self.total_open_frames += 1

        # 낮은 신뢰도: 투표 가중치 최소화 (이전 상태 방어)
        effective_conf = max(confidence, self.cfg.min_confidence)

        # 윈도우에 추가
        self._window.append((raw_is_open, effective_conf))

        # 윈도우가 충분히 채워지지 않으면 UNKNOWN 유지
        if len(self._window) < max(1, int(
            self.cfg.state_window * self.cfg.min_window_fill
        )):
            return self._state

        # ── 신뢰도 가중 투표 ─────────────────────────────────────────────
        open_weight = 0.0
        total_weight = 0.0
        for is_open, conf in self._window:
            total_weight += conf
            if is_open:
                open_weight += conf

        open_ratio = open_weight / max(total_weight, 1e-9)
        voted_open = open_ratio > self.cfg.open_vote_threshold

        # ── 상태 기계 전이 ───────────────────────────────────────────────
        self._state = self._transition(voted_open)
        return self._state

    def _transition(self, voted_open: bool) -> DoorState:
        """상태 기계 전이 로직"""
        cur = self._state

        # UNKNOWN → 첫 판단
        if cur == DoorState.UNKNOWN:
            self._state = DoorState.OPEN if voted_open else DoorState.CLOSED
            return self._state

        # 현재 안정 상태
        if cur == DoorState.CLOSED:
            if voted_open:
                self._new_state_count += 1
                if self._new_state_count >= self.cfg.debounce_frames:
                    self._enter_state(DoorState.OPENING)
            else:
                self._new_state_count = 0
            return self._state

        if cur == DoorState.OPEN:
            if not voted_open:
                self._new_state_count += 1
                if self._new_state_count >= self.cfg.debounce_frames:
                    self._enter_state(DoorState.CLOSING)
            else:
                self._new_state_count = 0
            return self._state

        # 전환 상태 (OPENING / CLOSING)
        self._transition_count += 1
        if self._transition_count >= self.cfg.transition_hold_frames:
            if cur == DoorState.OPENING:
                self._enter_state(DoorState.OPEN)
            else:  # CLOSING
                self._enter_state(DoorState.CLOSED)

        return self._state

    def _enter_state(self, new_state: DoorState) -> None:
        old = self._state
        self._state = new_state
        self._new_state_count = 0
        self._transition_count = 0
        if old != new_state:
            self.state_change_times.append(time.time())
            logger.debug(
                "Zone %d: %s → %s", self.zone_id, old.name, new_state.name
            )

    # ── 조회 ─────────────────────────────────────────────────────────────────

    @property
    def state(self) -> DoorState:
        return self._state

    def get_bool(self) -> Optional[bool]:
        """True=열림, False=닫힘, None=불확실"""
        return self._state.to_bool()

    def open_ratio(self) -> float:
        """최근 윈도우에서 열림 투표 비율"""
        if not self._window:
            return 0.0
        return sum(1 for v, _ in self._window if v) / len(self._window)

    def confidence(self) -> float:
        """현재 상태의 평균 신뢰도"""
        if not self._window:
            return 0.0
        return float(np.mean([c for _, c in self._window]))

    def recent_change(self, seconds: float = 60.0) -> bool:
        """최근 N초 안에 상태 변화 있었는지"""
        now = time.time()
        return any(now - t < seconds for t in self.state_change_times[-5:])

    # ── 히스토리 그래프 데이터 ───────────────────────────────────────────────

    def get_history(self) -> List[bool]:
        """윈도우 내 열림 여부 히스토리 리스트"""
        return [v for v, _ in self._window]


# ---------------------------------------------------------------------------
# 전체 세탁기 상태 관리자
# ---------------------------------------------------------------------------

class StateTracker:
    """
    모든 세탁기 존의 상태를 통합 관리.
    """

    def __init__(self, config: AppConfig) -> None:
        self.cfg = config.tracking
        self.trackers: Dict[int, MachineDoorTracker] = {}

    def _get_tracker(self, zone_id: int) -> MachineDoorTracker:
        if zone_id not in self.trackers:
            self.trackers[zone_id] = MachineDoorTracker(self.cfg, zone_id)
        return self.trackers[zone_id]

    def update(
        self,
        raw_results: Dict[int, Tuple[bool, float, dict]],
    ) -> Dict[int, DoorState]:
        """
        Parameters
        ----------
        raw_results : {zone_id: (is_open, confidence, debug)}

        Returns
        -------
        stable_states : {zone_id: DoorState}
        """
        stable: Dict[int, DoorState] = {}
        for zone_id, (is_open, conf, _debug) in raw_results.items():
            tracker = self._get_tracker(zone_id)
            state = tracker.update(is_open, conf)
            stable[zone_id] = state
        return stable

    def get_bool_map(self) -> Dict[int, Optional[bool]]:
        """모든 존의 {zone_id: bool} 반환"""
        return {zid: t.get_bool() for zid, t in self.trackers.items()}

    def get_state_map(self) -> Dict[int, DoorState]:
        """모든 존의 {zone_id: DoorState} 반환"""
        return {zid: t.state for zid, t in self.trackers.items()}

    def get_tracker(self, zone_id: int) -> MachineDoorTracker:
        return self._get_tracker(zone_id)

    def reset(self, zone_id: Optional[int] = None) -> None:
        """특정 존 또는 전체 리셋"""
        if zone_id is not None:
            if zone_id in self.trackers:
                del self.trackers[zone_id]
        else:
            self.trackers.clear()
