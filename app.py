from functools import wraps
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request, get_jwt, jwt_required
import requests
import bcrypt

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # same as in auth-service

jwt = JWTManager(app)

# Base URL for DB service
DB_SERVICE_URL = "http://db-service:5003"

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

@app.route("/appointments/<int:appointment_id>", methods=["PUT"])
@requires_role("staff")
def update_appointment_as_staff(appointment_id):
    data = request.json
    allowed_fields = {"date", "time"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "Only 'date' and 'time' can be updated"}), 400

    response = requests.put(f"{DB_SERVICE_URL}/appointments/{appointment_id}", json=update_data)
    return jsonify(response.json()), response.status_code

# This endpoint is for staff only
@app.route("/appointments/<int:service_id>", methods=["DELETE"])
@requires_role("staff")
def delete_appointment_as_staff(appointment_id):
    response = requests.delete(f"{DB_SERVICE_URL}/appointments/{appointment_id}")
    return jsonify(response.json()), response.status_code

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
