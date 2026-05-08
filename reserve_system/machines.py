from datetime import UTC, datetime, timedelta

from config import USAGE_MINUTES
from db import connect_db, now_text, parse_time
from reservations import reservation_for_machine, reservation_to_dict


def machine_state_to_dict(row, reservation=None):
    ends_at = parse_time(row["ends_at"])
    remaining_seconds = 0
    if ends_at:
        remaining_seconds = max(0, int((ends_at - datetime.now(UTC)).total_seconds()))
    in_use = bool(row["in_use"]) and remaining_seconds > 0
    return {
        "machineName": row["machine_name"],
        "signalValue": bool(row["signal_value"]),
        "inUse": in_use,
        "startedAt": row["started_at"],
        "endsAt": row["ends_at"],
        "remainingSeconds": remaining_seconds if in_use else 0,
        "reserved": reservation is not None,
        "reservation": reservation_to_dict(reservation) if reservation else None,
    }


def empty_machine_state(machine_name, reservation=None):
    return {
        "machineName": machine_name,
        "signalValue": False,
        "inUse": False,
        "startedAt": None,
        "endsAt": None,
        "remainingSeconds": 0,
        "reserved": reservation is not None,
        "reservation": reservation_to_dict(reservation) if reservation else None,
    }


def find_machine_state(machine_name):
    with connect_db() as db:
        row = db.execute(
            "SELECT * FROM machine_states WHERE machine_name = ?",
            (machine_name,),
        ).fetchone()
        reservation = reservation_for_machine(db, machine_name)
    return machine_state_to_dict(row, reservation) if row else empty_machine_state(machine_name, reservation)


def list_machine_states():
    with connect_db() as db:
        rows = db.execute("SELECT * FROM machine_states ORDER BY machine_name").fetchall()
        states = []
        for row in rows:
            states.append(machine_state_to_dict(row, reservation_for_machine(db, row["machine_name"])))
        return states


def update_machine_signal(payload):
    machine_name = str(payload.get("machineName", "")).strip()
    signal_value = payload.get("isInUse")
    if not machine_name:
        return None, "기기 이름이 필요합니다."
    if not isinstance(signal_value, bool):
        return None, "isInUse는 true 또는 false여야 합니다."

    with connect_db() as db:
        previous = db.execute(
            "SELECT * FROM machine_states WHERE machine_name = ?",
            (machine_name,),
        ).fetchone()
        reservation = reservation_for_machine(db, machine_name)
        previous_signal = bool(previous["signal_value"]) if previous else False
        started_at = previous["started_at"] if previous else None
        ends_at = previous["ends_at"] if previous else None
        in_use = bool(previous["in_use"]) if previous else False

        if previous_signal and not signal_value and reservation:
            start = datetime.now(UTC)
            started_at = start.isoformat(timespec="milliseconds").replace("+00:00", "Z")
            ends_at = (start + timedelta(minutes=USAGE_MINUTES)).isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z")
            in_use = True
        elif signal_value:
            started_at = None
            ends_at = None
            in_use = False
        elif not reservation:
            started_at = None
            ends_at = None
            in_use = False

        db.execute(
            """
            INSERT INTO machine_states
                (machine_name, signal_value, in_use, started_at, ends_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(machine_name) DO UPDATE SET
                signal_value = excluded.signal_value,
                in_use = excluded.in_use,
                started_at = excluded.started_at,
                ends_at = excluded.ends_at,
                updated_at = excluded.updated_at
            """,
            (
                machine_name,
                1 if signal_value else 0,
                1 if in_use else 0,
                started_at,
                ends_at,
                now_text(),
            ),
        )

    return find_machine_state(machine_name), ""
