"""
setup_zones.py
==============
세탁기 존(Zone) 설정 도구 (최초 1회 실행)

사용법:
  python setup_zones.py                      # 기본 카메라(0) 사용
  python setup_zones.py --source 1           # 카메라 1번 사용
  python setup_zones.py --source rtsp://...  # RTSP 스트림
  python setup_zones.py --source video.mp4   # 파일
  python setup_zones.py --auto               # Hough Circle 자동 감지 시도

조작:
  - 마우스 왼쪽 드래그: 세탁기 ROI 지정
  - 우클릭: 직전 존 취소
  - Enter / q: 완료 + 저장
  - r: 처음부터 다시
  - a: 자동 감지 시도
  - Esc: 취소

실행 순서: 2층 세탁기 왼→오, 이어서 1층 세탁기 왼→오
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.config import AppConfig
from src.zone_manager import ZoneManager


def parse_args():
    p = argparse.ArgumentParser(description="세탁실 존 설정 도구")

    # AppConfig 단일 인스턴스화
    _default_config = AppConfig()
    p.add_argument("--source", default= _default_config.video.source,
                   help= f"카메라 인덱스, RTSP URL, 또는 파일 경로 (기본: {_default_config.video.source})") 
    p.add_argument("--floors", type=int, default=_default_config.layout.n_floors,
                   help=f"층 수 (기본: {_default_config.layout.n_floors})")
    p.add_argument("--machines", nargs="+", type=int, default=_default_config.layout.machines_per_floor,
                   help=f"층별 세탁기 수 (위층부터, 기본: {_default_config.layout.machines_per_floor})")
    
    p.add_argument("--auto", action="store_true",
                   help="Hough Circle 자동 감지 시도")
    p.add_argument("--out", default="configs/zones.json",
                   help="저장 경로 (기본: configs/zones.json)")
    return p.parse_args()


def grab_frame(source: str) -> np.ndarray:
    """소스에서 안정화된 프레임 한 장 가져오기"""
    src = int(source) if source.isdigit() else source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"[오류] 소스 열기 실패: {source}")
        sys.exit(1)

    # 카메라 안정화를 위해 초반 프레임 건너뜀
    for _ in range(10):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("[오류] 프레임 읽기 실패")
        sys.exit(1)
    return frame


def main():
    args = parse_args()

    # 설정 구성
    config = AppConfig()
    config.zones_file = args.out
    config.layout.n_floors = args.floors
    config.layout.machines_per_floor = args.machines

    total = sum(args.machines)
    print(f"\n{'='*60}")
    print(f" 세탁실 존 설정 도구")
    print(f"{'='*60}")
    print(f" 소스      : {args.source}")
    print(f" 층 수     : {args.floors}")
    print(f" 세탁기 수 : {args.machines} (총 {total}대)")
    print(f" 저장 경로 : {args.out}")
    print(f"{'='*60}\n")

    # 프레임 가져오기
    print("[1/3] 카메라에서 기준 프레임 캡처 중...")
    frame = grab_frame(args.source)
    h, w = frame.shape[:2]
    print(f"      프레임 크기: {w}x{h}")

    zone_mgr = ZoneManager(config)

    # 인터랙티브 수동 설정
    print("[2/3] 인터랙티브 존 설정 시작...")
    print(f"""
  조작법:
    - 마우스 왼쪽 드래그 : 세탁기 ROI 지정
    - 우클릭             : 직전 존 취소
    - Enter / q          : 설정 완료 + 저장
    - r                  : 처음부터 다시
    - a                  : 자동 감지 재시도

  지정 순서: 2층 왼쪽 → 오른쪽, 이어서 1층 왼쪽 → 오른쪽
""")

    ok = zone_mgr.interactive_setup(frame)
    if not ok:
        print("[경고] 존 설정이 완전하지 않아 저장하지 않습니다.")
        sys.exit(1)

    print(f"\n[3/3] 존 설정 완료 ({len(zone_mgr.zones)}개)")
    for z in zone_mgr.zones:
        print(f"  Zone {z.zone_id:02d} ({z.label}): ({z.x1},{z.y1})-({z.x2},{z.y2})\t크기={z.width}x{z.height}")

    print(f"\n[완료] 존 설정 저장: {args.out}")
    print("  이제 main.py를 실행하세요.\n")

if __name__ == "__main__":
    main()
