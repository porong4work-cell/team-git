import time
import requests

try:
    res = requests.post("http://localhost:5000/api/machines/status", json={"machineName": "1번 세탁기", "isInUse": True})
    print("Set to True:", res.json())
    time.sleep(1)
    res = requests.post("http://localhost:5000/api/machines/status", json={"machineName": "1번 세탁기", "isInUse": False})
    print("Set to False:", res.json())
except Exception as e:
    print(e)
