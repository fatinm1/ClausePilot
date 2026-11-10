"""Public liveness checks must never expose secrets or call paid providers."""
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)

@health_bp.route("/healthz", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})
