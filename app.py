from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from prometheus_flask_exporter import PrometheusMetrics
from routes import register_blueprints
import os

app = Flask(__name__)

metrics = PrometheusMetrics(app)

# Secret key for JWT - use environment variable with fallback
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key')

jwt = JWTManager(app)

register_blueprints(app)

# Health check endpoint for Kubernetes
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Kubernetes liveness/readiness probes"""
    return jsonify({"status": "healthy", "service": "business-logic"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
