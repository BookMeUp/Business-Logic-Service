from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
import requests
from utils import requires_role, is_time_slot_valid, DB_SERVICE_URL

appointments_bp = Blueprint("appointments", __name__)

# ---------------- APPOINTMENTS - CUSTOMER ----------------

# This endpoint is for customer only
@appointments_bp.route("/appointments/me", methods=["GET"])
@requires_role("customer")
def get_my_appointments():
    user_id = get_jwt_identity()

    response = requests.get(f"{DB_SERVICE_URL}/appointments/user/{user_id}")
    return jsonify(response.json()), response.status_code

# This endpoint is for customer only
@appointments_bp.route("/appointments", methods=["POST"])
@requires_role("customer")
def create_appointment():
    user_id = get_jwt_identity()

    data = request.json

    is_valid, error_msg = is_time_slot_valid(data["date"], data["time"], data["service_id"])
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    appointment_data = {
        "user_id": user_id,
        "service_id": data["service_id"],
        "date": data["date"],
        "time": data["time"]
    }

    response = requests.post(f"{DB_SERVICE_URL}/appointments", json=appointment_data)
    return jsonify(response.json()), response.status_code

# This endpoint is for customer only
@appointments_bp.route("/appointments/me/<int:appointment_id>", methods=["PUT"])
@requires_role("customer")
def update_appointment_as_customer(appointment_id):
    user_id = get_jwt_identity()

    # Step 1: Verify the appointment belongs to the user
    response = requests.get(f"{DB_SERVICE_URL}/appointments/user/{user_id}")
    if response.status_code != 200:
        return jsonify({"error": "Could not verify user ownership"}), 403

    appointments = response.json()
    if not any(a["id"] == appointment_id for a in appointments):
        return jsonify({"error": "You do not own this appointment"}), 403

    # Step 2: Allow updates to date and/or time only
    data = request.json
    allowed_fields = {"date", "time"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "Only 'date' and 'time' can be updated"}), 400
    
    # Fetch the existing appointment
    appt_resp = requests.get(f"{DB_SERVICE_URL}/appointments/{appointment_id}")
    if appt_resp.status_code != 200:
        return jsonify({"error": "Appointment not found"}), 404

    existing_appt = appt_resp.json()
    service_id = existing_appt["service_id"]
    
    # Validate the new time slot
    is_valid, error_msg = is_time_slot_valid(data["date"], data["time"], service_id)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # Step 3: Forward update to db-service
    response = requests.put(f"{DB_SERVICE_URL}/appointments/{appointment_id}", json=update_data)
    return jsonify(response.json()), response.status_code

# This endpoint is for customer only
@appointments_bp.route("/appointments/me/<int:appointment_id>", methods=["DELETE"])
@requires_role("customer")
def delete_appointment_as_customer(appointment_id):
    user_id = get_jwt_identity()

    # Fetch user's appointments from db-service
    response = requests.get(f"{DB_SERVICE_URL}/appointments/user/{user_id}")
    if response.status_code != 200:
        return jsonify({"error": "Could not verify user ownership"}), 403

    appointments = response.json()
    if not any(a["id"] == appointment_id for a in appointments):
        return jsonify({"error": "You do not own this appointment"}), 403
    
    # Proceed with deletion
    response = requests.delete(f"{DB_SERVICE_URL}/appointments/{appointment_id}")
    return jsonify(response.json()), response.status_code

# ---------------- APPOINTMENTS - STAFF ----------------

# This endpoint is for staff only
@appointments_bp.route("/appointments", methods=["GET"])
@requires_role("staff")
def get_all_appointments():
    response = requests.get(f"{DB_SERVICE_URL}/appointments")
    return jsonify(response.json()), response.status_code

@appointments_bp.route("/appointments/date/<date>", methods=["GET"])
@requires_role("staff")
def get_appointments_by_date(date):
    response = requests.get(f"{DB_SERVICE_URL}/appointments/date/{date}")
    return jsonify(response.json()), response.status_code

@appointments_bp.route("/appointments/<int:appointment_id>", methods=["PUT"])
@requires_role("staff")
def update_appointment_as_staff(appointment_id):
    data = request.json
    allowed_fields = {"date", "time"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "Only 'date' and 'time' can be updated"}), 400

    # Fetch the existing appointment
    appt_resp = requests.get(f"{DB_SERVICE_URL}/appointments/{appointment_id}")
    if appt_resp.status_code != 200:
        return jsonify({"error": "Appointment not found"}), 404

    existing_appt = appt_resp.json()
    service_id = existing_appt["service_id"]

    # Now validate with the correct service_id
    is_valid, error_msg = is_time_slot_valid(data["date"], data["time"], service_id)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # Proceed with updating
    response = requests.put(f"{DB_SERVICE_URL}/appointments/{appointment_id}", json=update_data)
    return jsonify(response.json()), response.status_code

# This endpoint is for staff only
@appointments_bp.route("/appointments/<int:appointment_id>", methods=["DELETE"])
@requires_role("staff")
def delete_appointment_as_staff(appointment_id):
    response = requests.delete(f"{DB_SERVICE_URL}/appointments/{appointment_id}")
    return jsonify(response.json()), response.status_code
