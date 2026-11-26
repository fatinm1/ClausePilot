import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


@health_bp.route("/healthz", methods=["GET"])
def health_check():
    return jsonify(
        {
            "status": "ok",
            "version": "1.0.1-rule-preprocessing-active",  # DEPLOYED: Rule preprocessing is active!
            "timestamp": datetime.now().isoformat(),
            "features": ["rule_preprocessing", "firm_details_override"],
        }
    )


@health_bp.route("/test-firm-details", methods=["POST"])
def test_firm_details():
    """Test endpoint to see what firm details are received"""
    try:
        data = request.get_json() or {}
        firm_details = data.get("firm_details", {})

        return jsonify(
            {
                "status": "success",
                "received_data": data,
                "firm_details": firm_details,
                "firm_details_keys": list(firm_details.keys()) if firm_details else [],
                "firm_details_values": (
                    dict(firm_details.items()) if firm_details else {}
                ),
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
