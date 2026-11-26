from functools import wraps

from flask import jsonify, request


def csrf_protect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:
                return jsonify({"error": "CSRF token required"}), 403
        return f(*args, **kwargs)

    return decorated_function
