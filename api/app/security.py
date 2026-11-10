"""Verified identity shared by every protected API blueprint."""
from functools import wraps
from flask import current_app, jsonify, request
import jwt


def authenticated_user():
    """Resolve an active account from a signed access token, never a user-ID header."""
    header = request.headers.get("Authorization", "")
    token = header[7:] if header.startswith("Bearer ") else request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"],
                             algorithms=["HS256"], options={"require": ["exp", "user_id", "type"]})
        if payload["type"] != "access":
            return None
        user = current_app.extensions["sqlalchemy"].session.get(current_app.User, payload["user_id"])
        return user if user and user.is_active else None
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None


def require_auth(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        user = authenticated_user()
        if user is None:
            return jsonify({"error": "Authentication required"}), 401
        # Browser cookie writes must originate from the configured application.
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not request.headers.get("Authorization"):
            origin = request.headers.get("Origin")
            if origin and origin.rstrip("/") not in [o.rstrip("/") for o in current_app.config["CORS_ORIGINS"]]:
                return jsonify({"error": "Origin not allowed"}), 403
        return function(user, *args, **kwargs)
    return wrapped


def require_admin(function):
    @wraps(function)
    @require_auth
    def wrapped(user, *args, **kwargs):
        if not user.is_admin():
            return jsonify({"error": "Admin access required"}), 403
        return function(user, *args, **kwargs)
    return wrapped
