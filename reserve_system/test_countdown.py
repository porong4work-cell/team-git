import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from db import connect_db
from model_signals import handle_model_door_result
from machines import find_machine_state
import json

def test_logic():
    machine = "1번 세탁기"
    
    # Check if reservation exists
    with connect_db() as db:
        res = db.execute("SELECT * FROM reservations WHERE machine_name=?", (machine,)).fetchone()
        if not res:
            print(f"[{machine}] 예약 정보가 DB에 없습니다. 테스트를 위해 예약을 먼저 해주세요.")
        else:
            print(f"[{machine}] 예약 확인됨: {dict(res)}")

    print("\n[1] 문 열림 (True) 전송...")
    res1, err1 = handle_model_door_result({"machineName": machine, "doorOpen": True})
    print("결과:", json.dumps(res1, indent=2, ensure_ascii=False) if res1 else err1)

    print("\n[2] 문 닫힘 (False) 전송...")
    res2, err2 = handle_model_door_result({"machineName": machine, "doorOpen": False})
    print("결과:", json.dumps(res2, indent=2, ensure_ascii=False) if res2 else err2)

    print("\n[3] 닫힌 상태 유지 (False) 전송...")
    res3, err3 = handle_model_door_result({"machineName": machine, "doorOpen": False})
    print("결과:", json.dumps(res3, indent=2, ensure_ascii=False) if res3 else err3)

if __name__ == "__main__":
    test_logic()