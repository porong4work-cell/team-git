"""
main.py
=======
세탁실 실시간 모니터링 메인 실행 파일
YOLO26n + OpenCV 기반 | Apple M5 Pro MPS 최적화

사용법:
  python main.py                            # 기본 카메라(0)
  python main.py --source 1                 # 카메라 1번
  python main.py --source rtsp://...        # RTSP 스트림
  python main.py --source video.mp4         # 파일
  python main.py --custom models/door.pt    # 커스텀 모델 사용
  python main.py --no-yolo                  # YOLO 비활성화 (CV만 사용)
  python main.py --debug                    # 디버그 오버레이 표시
  python main.py --recalibrate              # 보정값 재생성 강제

핫키 (실행 중):
  q / Esc : 종료
  d       : 디버그 오버레이 토글
  s       : 현재 상태 콘솔 출력
  c       : 재보정 시작
  r       : 추적기 상태 전체 리셋
  Space   : 일시정지

파이프라인:
  VideoCapture → YOLO26n 추론 → 존별 DoorDetector → StateTracker
  → 2D 상태 배열 생성 → Visualizer 렌더링 → imshow

2D 배열 구조:
  [
    [2층 왼쪽, 2층 중간, 2층 오른쪽, ...],   ← True=열림, False=닫힘
    [1층 왼쪽, 1층 중간, 1층 오른쪽, ...]
  ]
"""

from __future__ import annotations
import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.config import AppConfig
from src.zone_manager import ZoneManager, Zone_Statistic
from src.door_detector import DoorDetector_By_Custom_Model
from src.state_tracker import StateTracker #, DoorState
from src.yolo_handler import YOLOHandler
from src.visualizer import Visualizer

# ---------------------------------------------------------------------------
# 로깅 설정
# ---------------------------------------------------------------------------

def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")
    # Ultralytics 로그 억제
    logging.getLogger("ultralytics").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# CLI 인자 파싱
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="세탁실 세탁기 문 상태 실시간 모니터 (YOLO26n + OpenCV)")

    # AppConfig 단일 인스턴스화
    _default_config = AppConfig()

    p.add_argument("--source", default= _default_config.video.source,
                   help= f"카메라 인덱스, RTSP URL, 또는 파일 경로 (기본: {_default_config.video.source})") 
    p.add_argument("--floors", type=int, default=_default_config.layout.n_floors,
                   help=f"층 수 (기본: {_default_config.layout.n_floors})")
    p.add_argument("--machines", nargs="+", type=int, default=_default_config.layout.machines_per_floor,
                   help=f"층별 세탁기 수 (위층부터, 기본: {_default_config.layout.machines_per_floor})")
    p.add_argument("--zones", default="configs/zones.json",
                   help="존 설정 파일 경로 (기본: configs/zones.json)")
    p.add_argument("--custom", default=None,
                   help="커스텀 YOLO 모델 경로 (washer_open/closed 학습)")
    p.add_argument("--no-yolo", action="store_true",
                   help="YOLO26n 비활성화 (CV 방법만 사용)")
    p.add_argument("--debug", action="store_true",
                   help="디버그 오버레이 표시")
    p.add_argument("--recalibrate", action="store_true",
                   help="기존 보정값 무시하고 재보정")
    p.add_argument("--skip", type=int, default=1,
                   help="N 프레임마다 1회 처리 (기본: 1, 모든 프레임)")
    p.add_argument("--window", type=int, default=20,
                   help="상태 추적 윈도우 크기 (기본: 20)")
    return p.parse_args()


# ---------------------------------------------------------------------------
# 비디오 소스 열기
# ---------------------------------------------------------------------------

def open_source(source: str) -> cv2.VideoCapture:
    """VideoCapture 열기 + 최신 프레임 우선 버퍼 설정"""
    source = int(source) if source.isdigit() else source   
    # source는 카메라 종류: 1 = 맥북 캠, 0 = 웹캠
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[오류] 소스 열기 실패: {source}")
        sys.exit(1)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


# ---------------------------------------------------------------------------
# 상태 출력 유틸
# ---------------------------------------------------------------------------

def _print_status(
    status_array: List[List[Optional[bool]]],
    frame_idx: int,
    verbose: bool = False,
) -> None:
    """콘솔에 2D 배열 시각적 출력"""
    ts = time.strftime("%H:%M:%S")
    print(f"\n[{ts}] Frame #{frame_idx} | 세탁기 상태:")

    # 2D 배열 Python 표현
    rows = []
    for fi, row in enumerate(status_array):
        floor_num = len(status_array) - fi
        row_str = "[" + ", ".join(
            " True" if v is True else ("False" if v is False else " None")
            for v in row
        ) + "]"
        rows.append(f"  {floor_num}층: {row_str}")
    print("\n".join(rows))
    print()

    if verbose:
        open_cnt = sum(1 for r in status_array for v in r if v is True)
        total = sum(len(r) for r in status_array)
        print(f"  요약: 총 {total}대 중 {open_cnt}대 열림, {total - open_cnt}대 닫힘\n")

# ---------------------------------------------------------------------------
# 메인 루프
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    # ── 설정 구성 ─────────────────────────────────────────────────────────
    config = AppConfig()
    config.video.source = args.source
    config.video.frame_skip = args.skip
    config.zones_file = args.zones
    config.layout.n_floors = args.floors
    config.layout.machines_per_floor = args.machines
    config.tracking.state_window = args.window
    config.display.show_debug_info = args.debug

    device = config.get_device()
    logger.info("장치: %s", device)
    logger.info("소스: %s", args.source)
    logger.info("세탁기 레이아웃: %s층 × %s", args.floors, args.machines)

    # ── 모듈 초기화 ──────────────────────────────────────────────────────
    zone_mgr   = ZoneManager(config)
    zone_stat  = Zone_Statistic()
    # --custom 옵션으로 custom_v1.pt 경로를 DoorDetector에 직접 전달
    detector   = DoorDetector_By_Custom_Model(config)
    tracker    = StateTracker(config)
    visualizer = Visualizer(config)

    # YOLO26n 핸들러
    yolo_handler = YOLOHandler(config) if not args.no_yolo else None

    # ── 존 로드 ──────────────────────────────────────────────────────────
    print()
    if zone_mgr.load():
        zones = zone_mgr.get_zones()
    else:
        print("\n[경고] 존 설정 파일이 없습니다.")
        print(f"\tsetup_zone 실행\n")
        
        # 카메라를 오픈
        cap_tmp = open_source(args.source)
        for _ in range(7):      # 카메라 워밍업을 위해 7번 반복
            cap_tmp.read()
        
        # ___.read() -> (ret, frame) 튜플 반환       
        # ret: retrieval로 성공/실패에 대한 bool 값 | frame: 캡쳐된 이미지 데이터 
        ret, setup_frame = cap_tmp.read()      

        # 카메라(웹캠)나 동영상 파일에 대한 하드웨어 권한을 해제하고 os에 돌려주는 기능
        cap_tmp.release()   

        try:
            ok = zone_mgr.interactive_setup(setup_frame)
            if ok:
                print("\n파일 로드 중...")
                zones = zone_mgr.get_zones()
                for z in zones:
                    print(f"\tZone {z.zone_id:02d} ({z.label}): ({z.x1},{z.y1})-({z.x2},{z.y2})\t크기={z.width}x{z.height}")
                print()
        except Exception as e:
            print(f"Error: {e}\n")
            print(f"[설정 실패] 다음 명령어로 setup_zones.py를 실행해주세요.")
            print(f"\tpython setup_zones.py --source {args.source}")
            sys.exit(1)
        

    # ── YOLO26n 로드 ─────────────────────────────────────────────────────
    if yolo_handler is not None:
        print()
        yolo_handler.load()
        # 커스텀 모델은 DoorDetector에 직접 연결됨 (yolo_handler 경유 불필요)

    # ── 비디오 소스 열기 ─────────────────────────────────────────────────
    cap = open_source(args.source)
    print()
    logger.info("VideoCapture 열림")

    # ── 보정 ─────────────────────────────────────────────────────────────
    # YOLO 기반 DoorDetector 에서 needs_calibration=True → 보정 진행 (기본: False)
    if getattr(detector, "needs_calibration", True):
        print(1)
        cal_loaded = False
        if not args.recalibrate:
            cal_loaded = zone_stat.load_statistics()
        if not cal_loaded:
            detector.run_calibration(cap, zone_mgr, zone_stat, config)
        else:
            logger.info("기존 보정 데이터 로드 완료")
    else:
        logger.info("보정 단계 스킵 (YOLO 모델 — 보정 불필요)")
        print()

    # ── 메인 처리 루프 ───────────────────────────────────────────────────
    win_name = config.display.window_name
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

    frame_idx = 0
    paused = False
    status_array = None

    
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                logger.warning("프레임 읽기 실패 - 재연결 시도...")
                cap.release()
                time.sleep(config.video.reconnect_delay)
                cap = open_source(args.source)
                continue

            frame_idx += 1

            # 프레임 건너뜀 (성능 조정)
            if frame_idx % config.video.frame_skip != 0:
                cv2.imshow(win_name, frame)
                key = cv2.waitKey(1) & 0xFF
                ESC = 27
                if key in (ord('q'), ESC):
                    break
                continue

            # ── YOLO26n 추론 (사람 탐지 보조) ──────────────────────────
            yolo_result = None
            if yolo_handler is not None and yolo_handler.is_loaded():
                yolo_result = yolo_handler.infer(frame)

            # ── 존별 문 상태 감지 (custom_v1.pt 직접 판단) ──────────────
            raw_results = detector.detect_all(frame, zones, zone_stat)

            if frame_idx == 1:
                print("\n[실행 중] 핫키: q=종료 | d=디버그 | s=상태출력 | c=재보정 | r=리셋 | Space=일시정지\n")

            # ── 시계열 상태 추적 ─────────────────────────────────────────
            stable_states = tracker.update(raw_results)

            # ── 2D 배열 생성 ─────────────────────────────────────────────
            bool_map = tracker.get_bool_map()
            status_array = zone_mgr.get_status_array(bool_map)

            # ── 주기적 콘솔 출력 ─────────────────────────────────────────
            if frame_idx % config.log_status_interval == 0:
                _print_status(status_array, frame_idx)

            # ── 디버그 정보 수집 ─────────────────────────────────────────
            debug_map = {zid: dbg for zid, (_, _, dbg) in raw_results.items()}

            # ── 시각화 ───────────────────────────────────────────────────
            trackers_map = {zid: tracker.get_tracker(zid) for zid in
                            [z.zone_id for z in zones]}
            display_frame = visualizer.render(
                frame=frame,
                zones=zones,
                states=stable_states,
                trackers=trackers_map,
                yolo_result=yolo_result,
                debug_map=debug_map,
                status_array=status_array,
            )

            cv2.imshow(win_name, display_frame)

        # ── 키 입력 처리 ─────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        ESC = 27

        if key in (ord('q'), ESC):   # q / Esc: 종료
            break

        elif key == ord('d'):        # d: 디버그 토글
            config.display.show_debug_info = not config.display.show_debug_info
            print(f"\t디버그 오버레이: {'ON' if config.display.show_debug_info else 'OFF'}")

        elif key == ord('s'):        # s: 상태 즉시 출력
            if 'status_array' in dir():
                _print_status(status_array, frame_idx, verbose=True)

        elif key == ord('c'):        # c: 재보정
            print("\n[재보정] 시작... (모든 문을 닫아주세요)")
            config.calibration.n_frames = 30
            detector.run_calibration(cap, zone_mgr, zone_stat, config)
            tracker.reset()
            print("")

        elif key == ord('r'):        # r: 추적기 리셋
            tracker.reset()
            print("\t추적기 상태 리셋 완료")

        elif key == ord(' '):        # Space: 일시정지
            paused = not paused 
            print(f"\t{'일시정지' if paused else '재개'}")

    # ── 정리 ─────────────────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
    print("\n[종료] 모니터링 종료\n")


# ---------------------------------------------------------------------------
# 엔트리포인트
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()



