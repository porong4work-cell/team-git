import uuid

from db import connect_db, now_text


def machine_type(machine_name):
    return "dryer" if "건조기" in machine_name else "washer"


def reservation_to_dict(row):
    return {
        "id": row["id"],
        "studentId": row["student_id"],
        "userName": row["user_name"],
        "machineName": row["machine_name"],
        "machineType": row["machine_type"],
        "createdAt": row["created_at"],
    }


def reservation_for_machine(db, machine_name):
    return db.execute(
        "SELECT * FROM reservations WHERE machine_name = ?",
        (machine_name,),
    ).fetchone()


def list_my_reservations(user_id):
    with connect_db() as db:
        rows = db.execute(
            """
            SELECT *
            FROM reservations
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [reservation_to_dict(row) for row in rows]


def create_reservation(user, payload):
    machine_name = str(payload.get("machineName", "")).strip()
    if not machine_name:
        return None, "예약할 기기를 선택하세요."

    with connect_db() as db:
        existing = db.execute(
            "SELECT id FROM reservations WHERE machine_name = ?",
            (machine_name,),
        ).fetchone()
        if existing:
            return None, "이미 예약된 기기입니다."

        reservation = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "student_id": user["student_id"],
            "user_name": user["name"],
            "machine_name": machine_name,
            "machine_type": machine_type(machine_name),
            "created_at": now_text(),
        }
        db.execute(
            """
            INSERT INTO reservations
                (id, user_id, student_id, user_name, machine_name, machine_type, created_at)
            VALUES
                (:id, :user_id, :student_id, :user_name, :machine_name, :machine_type, :created_at)
            """,
            reservation,
        )
    return reservation, ""


def delete_reservation(user_id, reservation_id):
    with connect_db() as db:
        cursor = db.execute(
            "DELETE FROM reservations WHERE id = ? AND user_id = ?",
            (reservation_id, user_id),
        )
    return cursor.rowcount > 0
