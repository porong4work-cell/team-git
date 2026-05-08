# 세탁실 모니터 실행 방법

현재 설정 기준 실행 문서입니다.

## 실행 위치

```bash
cd /home/masterj/codex/share/dorm-reservation-share/laundry_monitor_2_copy
```

## 처음 한 번만 설치

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

이미 설치했다면 다음부터는 활성화만 하면 됩니다.

```bash
source venv/bin/activate
```

## 현재 테스트 영상 실행

현재 `configs/zones.json`에는 세탁기 영역이 1개만 설정되어 있습니다.
그래서 지금은 아래 명령이 맞습니다.

```bash
python main.py --source test_video1_mp4.mp4 --floors 1 --machines 1
```

가상환경 활성화가 헷갈리면 아래처럼 직접 실행해도 됩니다.

```bash
venv/bin/python main.py --source test_video1_mp4.mp4 --floors 1 --machines 1
```

## 카메라로 실행

카메라 0번:

```bash
python main.py --source 0 --floors 1 --machines 1
```

카메라 1번:

```bash
python main.py --source 1 --floors 1 --machines 1
```

## 세탁기 영역 다시 설정

현재처럼 1개만 볼 때:

```bash
python setup_zones.py --source 0 --floors 1 --machines 1
```

2층 3대, 1층 3대를 전부 볼 때:

```bash
python setup_zones.py --source 0 --floors 2 --machines 3 3
```

그 경우 실행도 아래처럼 맞춰야 합니다.

```bash
python main.py --source 0 --floors 2 --machines 3 3
```

## 실행 중 키

```text
q 또는 Esc : 종료
d         : 디버그 표시 켜기/끄기
s         : 현재 상태 콘솔 출력
c         : 재보정
r         : 추적 상태 리셋
Space     : 일시정지
```

## cv2 오류

아래 오류가 뜨면 OpenCV가 현재 Python 환경에 설치되지 않은 것입니다.

```text
ModuleNotFoundError: No module named 'cv2'
```

해결:

```bash
cd /home/masterj/codex/share/dorm-reservation-share/laundry_monitor_2_copy
source venv/bin/activate
pip install -r requirements.txt
python -c "import cv2; print(cv2.__version__)"
```

`source venv/bin/activate`가 헷갈리면 항상 아래처럼 `venv/bin/python`으로 실행하세요.

```bash
venv/bin/python main.py --source test_video1_mp4.mp4 --floors 1 --machines 1
```

## project/START.md는 무엇인가

`/home/masterj/codex/share/project/START.md`는 세탁실 모니터 실행법이 아닙니다.
새 프로젝트를 처음 만들 때 목표, 범위, 검증 방법을 정리하도록 만든 AI 작업용 템플릿 문서입니다.
일반 실행에는 필요 없습니다.
