from flask import Blueprint, request, jsonify
import requests
from datetime import datetime, timedelta
from utils import requires_role, calculate_available_slots, DB_SERVICE_URL

availability_bp = Blueprint("availability", __name__)

@availability_bp.route("/availability/<date>", methods=["GET"])
@requires_role("staff")
def get_availability(date):
    response = requests.get(f"{DB_SERVICE_URL}/availability/{date}")
    return jsonify(response.json()), response.status_code

@availability_bp.route("/availability", methods=["POST"])
@requires_role("staff")
def define_availability():
    data = request.json
    date = data["date"]
    new_start = datetime.strptime(data["start_time"], "%H:%M")
    new_end = datetime.strptime(data["end_time"], "%H:%M")

    # Get all existing availability for this date
    response = requests.get(f"{DB_SERVICE_URL}/availability/{date}")
    existing = response.json()

    # Check for overlap
    for slot in existing:
        existing_start = datetime.strptime(slot["start_time"], "%H:%M")
        existing_end = datetime.strptime(slot["end_time"], "%H:%M")

        if new_start < existing_end and new_end > existing_start:
            return jsonify({"error": "Availability overlaps with an existing time slot"}), 400

    # Proceed to create availability
    create_resp = requests.post(f"{DB_SERVICE_URL}/availability", json=data)
    return jsonify(create_resp.json()), create_resp.status_code

@availability_bp.route("/availability/<int:availability_id>", methods=["DELETE"])
@requires_role("staff")
def delete_availability(availability_id):
    # Fetch availability by ID
    avail_resp = requests.get(f"{DB_SERVICE_URL}/availability/id/{availability_id}")
    if avail_resp.status_code != 200:
        return jsonify({"error": "Availability not found"}), 404
    availability = avail_resp.json()

    date = availability["date"]
    avail_start = datetime.strptime(availability["start_time"], "%H:%M")
    avail_end = datetime.strptime(availability["end_time"], "%H:%M")

    # Fetch all appointments for that date
    appt_resp = requests.get(f"{DB_SERVICE_URL}/appointments/date/{date}")
    if appt_resp.status_code != 200:
        return jsonify({"error": "Could not fetch appointments"}), 400

    appointments = appt_resp.json()

    # Check for overlap with appointments
    for appt in appointments:
        appt_time = datetime.strptime(appt["time"], "%H:%M")

        # Fetch service duration
        service_resp = requests.get(f"{DB_SERVICE_URL}/services/{appt['service_id']}")
        if service_resp.status_code != 200:
            continue

        duration = int(service_resp.json()["duration"])
        appt_end = appt_time + timedelta(minutes=duration)

        if appt_time < avail_end and avail_start < appt_end:
            return jsonify({"error": "Cannot delete availability with booked appointments"}), 400

    # Safe to delete
    delete_resp = requests.delete(f"{DB_SERVICE_URL}/availability/{availability_id}")
    return jsonify(delete_resp.json()), delete_resp.status_code

@availability_bp.route("/available-timeslots", methods=["GET"])
@requires_role("customer")
def get_available_timeslots():
    date = request.args.get("date")
    service_id = request.args.get("service_id")

    # Get service duration
    service_resp = requests.get(f"{DB_SERVICE_URL}/services/{service_id}")
    if service_resp.status_code != 200:
        return jsonify({"error": "Service not found"}), 404
    duration = int(service_resp.json()["duration"])

    # Get availability for date
    avail_resp = requests.get(f"{DB_SERVICE_URL}/availability/{date}")
    availabilities = avail_resp.json()

    # Get existing appointments
    appt_resp = requests.get(f"{DB_SERVICE_URL}/appointments/date/{date}")
    appointments = appt_resp.json()

    # Generate available time slots
    available_slots = calculate_available_slots(availabilities, appointments, duration)

    return jsonify({"available_slots": available_slots}), 200
