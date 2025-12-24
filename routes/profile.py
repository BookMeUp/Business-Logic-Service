from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import bcrypt
import requests
from app import DB_SERVICE_URL

profile_bp = Blueprint("profile", __name__)

# This endpoint is for authenticated users
@profile_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_my_profile():
    user_id = get_jwt_identity()
    response = requests.get(f"{DB_SERVICE_URL}/users/{user_id}")
    if response.status_code != 200:
        return jsonify({"error": "User not found"}), 404
    return jsonify(response.json()), 200

# This endpoint is for authenticated users
@profile_bp.route("/profile", methods=["PUT"])
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
