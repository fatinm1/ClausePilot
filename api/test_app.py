from flask import Flask, jsonify
from flask_cors import CORS


def create_test_app():
    app = Flask(__name__)

    # CORS setup
    CORS(app, origins=["http://localhost:3000"], supports_credentials=True)

    @app.route("/healthz", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"})

    @app.route("/v1/auth/login", methods=["POST"])
    def test_login():
        return jsonify({"message": "Test login endpoint working"})

    @app.route("/v1/auth/register", methods=["POST"])
    def test_register():
        return jsonify({"message": "Test register endpoint working"})

    return app


if __name__ == "__main__":
    app = create_test_app()
    print("🚀 Starting test Flask app on http://localhost:5001")
    print("📡 Health check: http://localhost:5001/healthz")
    print("🔐 Test auth: http://localhost:5001/v1/auth/login")
    app.run(host="0.0.0.0", port=5001, debug=True)
