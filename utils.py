from functools import wraps
import os
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask import jsonify
from datetime import datetime, timedelta
import requests

# The base URL of the db-service - use environment variable with fallback
DB_SERVICE_URL = os.getenv('DB_SERVICE_URL', 'http://db-service:5003')

# Role decorator
def requires_role(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims["role"] != required_role:
                return jsonify({"error": f"Access restricted to {required_role} role"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

def calculate_available_slots(availabilities, appointments, service_duration):
    def time_str_to_dt(t): return datetime.strptime(t, "%H:%M")
    def dt_to_time_str(dt): return dt.strftime("%H:%M")

    booked_times = [
        (time_str_to_dt(a["time"]), time_str_to_dt(a["time"]) + timedelta(minutes=service_duration))
        for a in appointments
    ]

    free_slots = []

    for slot in availabilities:
        start = time_str_to_dt(slot["start_time"])
        end = time_str_to_dt(slot["end_time"])
        current = start

        while current + timedelta(minutes=service_duration) <= end:
            slot_end = current + timedelta(minutes=service_duration)

            # Check for conflicts
            overlap = any(
                (bt_start < slot_end and current < bt_end)
                for bt_start, bt_end in booked_times
            )

            if not overlap:
                free_slots.append(dt_to_time_str(current))

            current += timedelta(minutes=10)

    return free_slots

def is_time_slot_valid(date, time, service_id):
    # 1. Get service duration
    service_resp = requests.get(f"{DB_SERVICE_URL}/services/{service_id}")
    if service_resp.status_code != 200:
        return False, "Service not found"

    duration = int(service_resp.json()["duration"])

    # 2. Get availability for the day
    avail_resp = requests.get(f"{DB_SERVICE_URL}/availability/{date}")
    if avail_resp.status_code != 200:
        return False, "No availability for the selected date"
    availabilities = avail_resp.json()

    # 3. Get current appointments for that date
    appt_resp = requests.get(f"{DB_SERVICE_URL}/appointments/date/{date}")
    if appt_resp.status_code != 200:
        return False, "Could not retrieve appointments"
    appointments = appt_resp.json()

    # 4. Generate valid time slots
    slots = calculate_available_slots(availabilities, appointments, duration)

    # 5. Return True/False depending on whether the requested time is valid
    if time not in slots:
        return False, "Selected time slot is not available"

    return True, None
