from functools import wraps
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request
import requests

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
            user = get_jwt_identity()
            if user["role"] != required_role:
                return jsonify({"error": f"Access restricted to {required_role} role"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ---------------- HEALTH ----------------

@app.route("/logic/health", methods=["GET"])
def health_check():
    return "Business Logic Service is running", 200

# ---------------- PUBLIC ----------------

@app.route("/services", methods=["GET"])
def get_services():
    response = requests.get(f"{DB_SERVICE_URL}/services")
    return jsonify(response.json()), response.status_code

# ---------------- CUSTOMER ----------------

@app.route("/appointments", methods=["POST"])
@requires_role("customer")
def create_appointment():
    user = get_jwt_identity()

    data = request.json
    appointment_data = {
        "user_id": user["id"],
        "service_id": data["service_id"],
        "date": data["date"],
        "time": data["time"]
    }

    response = requests.post(f"{DB_SERVICE_URL}/appointments", json=appointment_data)
    return jsonify(response.json()), response.status_code

@app.route("/appointments/me", methods=["GET"])
@requires_role("customer")
def get_my_appointments():
    user = get_jwt_identity()

    response = requests.get(f"{DB_SERVICE_URL}/appointments/user/{user['id']}")
    return jsonify(response.json()), response.status_code

@app.route("/appointments/me/<int:appointment_id>", methods=["DELETE"])
@requires_role("customer")
def delete_appointment(appointment_id):
    user = get_jwt_identity()

    # Fetch user's appointments from db-service
    response = requests.get(f"{DB_SERVICE_URL}/appointments/user/{user['id']}")
    if response.status_code != 200:
        return jsonify({"error": "Could not verify user ownership"}), 403

    appointments = response.json()
    if not any(a["id"] == appointment_id for a in appointments):
        return jsonify({"error": "You do not own this appointment"}), 403
    
    # Proceed with deletion
    response = requests.delete(f"{DB_SERVICE_URL}/appointments/{appointment_id}")
    return jsonify(response.json()), response.status_code

# ---------------- STAFF ----------------

@app.route("/appointments", methods=["GET"])
@requires_role("staff")
def get_all_appointments():
    response = requests.get(f"{DB_SERVICE_URL}/appointments")
    return jsonify(response.json()), response.status_code

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
