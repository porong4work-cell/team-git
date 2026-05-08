import sqlite3
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends, Cookie, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth import (
    create_session,
    create_user,
    delete_session,
    find_user_by_session,
    find_user_by_student_id,
    public_user,
    validate_signup,
    verify_password,
)
from config import HOST, PORT, UI_DIR, USAGE_MINUTES
from db import ensure_db
from machines import list_machine_states, update_machine_signal
from model_signals import handle_model_door_result
from reservations import (
    create_reservation,
    delete_reservation,
    list_my_reservations,
    reservation_to_dict,
)

app = FastAPI(title="Dorm Reservation API")

# --- Pydantic Models ---

class SignupRequest(BaseModel):
    studentId: str
    name: str
    password: str

class LoginRequest(BaseModel):
    studentId: str
    password: str

class ReservationRequest(BaseModel):
    machineName: str

class MachineStatusRequest(BaseModel):
    machineName: str
    isInUse: bool

class ModelDoorStateRequest(BaseModel):
    machineName: str
    doorOpen: Optional[bool] = None
    isDoorOpen: Optional[bool] = None
    result: Optional[bool] = None

# --- Dependencies ---

def get_current_user(dorm_session: Optional[str] = Cookie(None)):
    if not dorm_session:
        return None
    return find_user_by_session(dorm_session)

def require_current_user(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")
    return user

# --- API Routes ---

@app.get("/api/me")
def api_me(user: dict = Depends(get_current_user)):
    return {"user": public_user(user) if user else None}

@app.get("/api/my-reservations")
def api_my_reservations(user: dict = Depends(require_current_user)):
    return {"reservations": list_my_reservations(user["id"])}

@app.get("/api/machines")
def api_machines():
    return {"machines": list_machine_states(), "usageMinutes": USAGE_MINUTES}

@app.post("/api/signup")
def api_signup(request: SignupRequest, response: Response):
    payload = request.model_dump()
    message = validate_signup(payload)
    if message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    try:
        user = create_user(payload)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 가입된 학번입니다.")
    
    token = create_session(user["id"])
    response.status_code = status.HTTP_201_CREATED
    response.set_cookie(key="dorm_session", value=token, path="/", httponly=True, samesite="lax")
    return {"user": public_user(user)}

@app.post("/api/login")
def api_login(request: LoginRequest, response: Response):
    user = find_user_by_student_id(request.studentId)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="학번 또는 비밀번호가 올바르지 않습니다.")
    
    token = create_session(user["id"])
    response.set_cookie(key="dorm_session", value=token, path="/", httponly=True, samesite="lax")
    return {"user": public_user(user)}

@app.post("/api/logout")
def api_logout(response: Response, dorm_session: Optional[str] = Cookie(None)):
    if dorm_session:
        delete_session(dorm_session)
    response.delete_cookie(key="dorm_session", path="/", httponly=True, samesite="lax")
    return {"ok": True}

@app.post("/api/reservations", status_code=status.HTTP_201_CREATED)
def api_create_reservation(request: ReservationRequest, user: dict = Depends(require_current_user)):
    payload = request.model_dump()
    reservation, message = create_reservation(user, payload)
    if message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {
        "reservation": reservation_to_dict(reservation),
        "reservations": list_my_reservations(user["id"]),
    }

@app.delete("/api/reservations/{reservation_id}")
def api_delete_reservation(reservation_id: str, user: dict = Depends(require_current_user)):
    if not delete_reservation(user["id"], reservation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예약을 찾지 못했습니다.")
    return {"reservations": list_my_reservations(user["id"])}

@app.post("/api/machines/status")
def api_machine_status(request: MachineStatusRequest):
    payload = request.model_dump()
    machine, message = update_machine_signal(payload)
    if message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {"machine": machine, "usageMinutes": USAGE_MINUTES}

@app.post("/api/model/door-state")
def api_model_door_state(request: ModelDoorStateRequest):
    payload = request.model_dump(exclude_none=True)
    machine, message = handle_model_door_result(payload)
    if message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {"machine": machine, "usageMinutes": USAGE_MINUTES}

# --- WebSockets ---
@app.websocket("/ws/model/door-state")
async def websocket_model_door_state(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # 비동기적으로 처리하거나 모델 결과 받기. 일단 동기 함수 호출
            machine, message = handle_model_door_result(data)
            if message:
                await websocket.send_json({"error": message})
            else:
                await websocket.send_json({"machine": machine, "usageMinutes": USAGE_MINUTES})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))

# --- Exception Handling for backwards UI compatibility ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

# --- Static Files (UI) ---
# Serve UI as the default fallback
app.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

def main():
    ensure_db()
    print("기숙사 예약 시스템 실행 중 (FastAPI)")
    print(f"이 컴퓨터에서 접속: http://localhost:{PORT}")
    print(f"같은 네트워크에서 접속할 때는 이 PC의 IP 주소와 포트 {PORT}를 사용하세요.")
    print(f"서버 바인딩: http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()
