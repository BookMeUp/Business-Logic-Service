from flask import Blueprint, request, jsonify
import requests
from app import DB_SERVICE_URL
from utils import requires_role

services_bp = Blueprint("services", __name__)

# This endpoint is public
@services_bp.route("/services", methods=["GET"])
def get_services():
    response = requests.get(f"{DB_SERVICE_URL}/services")
    return jsonify(response.json()), response.status_code

# This endpoint is for staff only
@services_bp.route("/services", methods=["POST"])
@requires_role("staff")
def create_service():
    data = request.json
    response = requests.post(f"{DB_SERVICE_URL}/services", json=data)
    return jsonify(response.json()), response.status_code

# This endpoint is for staff only
@services_bp.route("/services/<int:service_id>", methods=["PUT"])
@requires_role("staff")
def update_service(service_id):
    data = request.json
    response = requests.put(f"{DB_SERVICE_URL}/services/{service_id}", json=data)
    return jsonify(response.json()), response.status_code

# This endpoint is for staff only
@services_bp.route("/services/<int:service_id>", methods=["DELETE"])
@requires_role("staff")
def delete_service(service_id):
    response = requests.delete(f"{DB_SERVICE_URL}/services/{service_id}")
    return jsonify(response.json()), response.status_code
