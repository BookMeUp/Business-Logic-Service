from flask import Flask
from flask_jwt_extended import JWTManager
from prometheus_flask_exporter import PrometheusMetrics
from routes import register_blueprints

app = Flask(__name__)

metrics = PrometheusMetrics(app)

app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # same as in auth-service

jwt = JWTManager(app)

register_blueprints(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
