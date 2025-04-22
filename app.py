from functools import wraps
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request, get_jwt, jwt_required
import requests
import bcrypt
from datetime import datetime, timedelta
from utils import calculate_available_slots, is_time_slot_valid, DB_SERVICE_URL

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # same as in auth-service

jwt = JWTManager(app)

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

# ---------------- HEALTH ----------------

@app.route("/logic/health", methods=["GET"])
def health_check():
    return "Business Logic Service is running", 200

# ---------------- PROFILE ----------------

# This endpoint is for authenticated users
@app.route("/profile", methods=["GET"])
@jwt_required()
def get_my_profile():
    user_id = get_jwt_identity()
    response = requests.get(f"{DB_SERVICE_URL}/users/{user_id}")
    if response.status_code != 200:
        return jsonify({"error": "User not found"}), 404
    return jsonify(response.json()), 200

# This endpoint is for authenticated users
@app.route("/profile", methods=["PUT"])
@jwt_required()
def update_my_profile():
    user_id = get_jwt_identity()
    data = request.json

    allowed_fields = {"name", "email", "password"}
    payload = {}

    for field in allowed_fields:
        if field in data:
            if field == "password":
                hashed_pw = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                payload["password"] = hashed_pw
            else:
                payload[field] = data[field]

    if not payload:
        return jsonify({"error": "No valid fields to update"}), 400

    response = requests.put(f"{DB_SERVICE_URL}/users/{user_id}", json=payload)
    return jsonify(response.json()), response.status_code

# ---------------- SERVICES ----------------

# This endpoint is public
@app.route("/services", methods=["GET"])
def get_services():
    response = requests.get(f"{DB_SERVICE_URL}/services")
    return jsonify(response.json()), response.status_code

# This endpoint is for staff only
@app.route("/services", methods=["POST"])
@requires_role("staff")
def create_service():
    data = request.json
    response = requests.post(f"{DB_SERVICE_URL}/services", json=data)
    return jsonify(response.json()), response.status_code

# This endpoint is for staff only
@app.route("/services/<int:service_id>", methods=["PUT"])
@requires_role("staff")
def update_service(service_id):
    data = request.json
    response = requests.put(f"{DB_SERVICE_URL}/services/{service_id}", json=data)
    return jsonify(response.json()), response.status_code

# This endpoint is for staff only
@app.route("/services/<int:service_id>", methods=["DELETE"])
@requires_role("staff")
def delete_service(service_id):
    response = requests.delete(f"{DB_SERVICE_URL}/services/{service_id}")
    return jsonify(response.json()), response.status_code

# ---------------- APPOINTMENTS - CUSTOMER ----------------

# This endpoint is for customer only
@app.route("/appointments/me", methods=["GET"])
@requires_role("customer")
def get_my_appointments():
    user_id = get_jwt_identity()

    response = requests.get(f"{DB_SERVICE_URL}/appointments/user/{user_id}")
    return jsonify(response.json()), response.status_code

# This endpoint is for customer only
@app.route("/appointments", methods=["POST"])
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
@app.route("/appointments/me/<int:appointment_id>", methods=["PUT"])
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
    
    # Validate the new time slot
    is_valid, error_msg = is_time_slot_valid(data["date"], data["time"], data["service_id"])
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # Step 3: Forward update to db-service
    response = requests.put(f"{DB_SERVICE_URL}/appointments/{appointment_id}", json=update_data)
    return jsonify(response.json()), response.status_code

# This endpoint is for customer only
@app.route("/appointments/me/<int:appointment_id>", methods=["DELETE"])
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
@app.route("/appointments", methods=["GET"])
@requires_role("staff")
def get_all_appointments():
    response = requests.get(f"{DB_SERVICE_URL}/appointments")
    return jsonify(response.json()), response.status_code

@app.route("/appointments/date/<date>", methods=["GET"])
@requires_role("staff")
def get_appointments_by_date(date):
    response = requests.get(f"{DB_SERVICE_URL}/appointments/date/{date}")
    return jsonify(response.json()), response.status_code

@app.route("/appointments/<int:appointment_id>", methods=["PUT"])
@requires_role("staff")
def update_appointment_as_staff(appointment_id):
    data = request.json
    allowed_fields = {"date", "time"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "Only 'date' and 'time' can be updated"}), 400
    
    is_valid, error_msg = is_time_slot_valid(data["date"], data["time"], data["service_id"])
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    response = requests.put(f"{DB_SERVICE_URL}/appointments/{appointment_id}", json=update_data)
    return jsonify(response.json()), response.status_code

# This endpoint is for staff only
@app.route("/appointments/<int:service_id>", methods=["DELETE"])
@requires_role("staff")
def delete_appointment_as_staff(appointment_id):
    response = requests.delete(f"{DB_SERVICE_URL}/appointments/{appointment_id}")
    return jsonify(response.json()), response.status_code

# ---------------- AVAILABILITY ----------------

@app.route("/availability/<date>", methods=["GET"])
@requires_role("staff")
def get_availability(date):
    response = requests.get(f"{DB_SERVICE_URL}/availability/{date}")
    return jsonify(response.json()), response.status_code

@app.route("/availability", methods=["POST"])
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

@app.route("/availability/<int:availability_id>", methods=["DELETE"])
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

@app.route("/available-timeslots", methods=["GET"])
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

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
