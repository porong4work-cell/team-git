from machines import update_machine_signal


def normalize_model_payload(payload):
    machine_name = str(payload.get("machineName", "")).strip()
    door_open = payload.get("doorOpen")
    if door_open is None:
        door_open = payload.get("isDoorOpen")
    if door_open is None:
        door_open = payload.get("result")

    if not machine_name:
        return None, "기기 이름이 필요합니다."
    if not isinstance(door_open, bool):
        return None, "문 열림 결과는 true 또는 false여야 합니다."

    return {"machineName": machine_name, "isInUse": door_open}, ""


def handle_model_door_result(payload):
    normalized, message = normalize_model_payload(payload)
    if message:
        return None, message
    return update_machine_signal(normalized)
