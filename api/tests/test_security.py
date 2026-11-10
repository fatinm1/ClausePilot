import datetime
import jwt
import pytest
from app import create_app, db
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-with-more-than-thirty-two-characters"

@pytest.fixture(scope="module")
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        for email, role in [("admin@example.test", "ADMIN"), ("user@example.test", "USER")]:
            u = app.User(email=email, role=role, is_active=True)
            u.set_password("test-password")
            db.session.add(u)
        db.session.commit()
    return app

def token(uid, kind="access", expired=False):
    return jwt.encode({"user_id": uid, "type": kind,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=-1 if expired else 60)},
        TestConfig.JWT_SECRET_KEY, algorithm="HS256")

def test_identity_header_is_not_authentication(app):
    client = app.test_client()
    assert client.get("/v1/admin/users", headers={"X-User-ID": "1"}).status_code == 401
    assert client.post("/v1/documents/upload").status_code == 401

def test_verified_role_and_token_type(app):
    c = app.test_client()
    assert c.get("/v1/admin/users", headers={"Authorization": "Bearer " + token(1)}).status_code == 200
    assert c.get("/v1/admin/users", headers={"Authorization": "Bearer " + token(2)}).status_code == 403
    for t in [token(1, "refresh"), token(1, expired=True), "forged"]:
        assert c.get("/v1/admin/users", headers={"Authorization": "Bearer " + t}).status_code == 401

def test_document_ownership(app):
    with app.app_context():
        d = app.Document(user_id=1, filename="sample.docx", original_filename="sample.docx", file_path="unused", file_size=1)
        db.session.add(d); db.session.commit(); document_id = d.id
    c = app.test_client()
    assert c.post(f"/v1/documents/{document_id}/process", json={}, headers={"Authorization": "Bearer " + token(2)}).status_code == 403

def test_health_is_public_and_minimal(app):
    assert app.test_client().get("/healthz").get_json() == {"status": "ok"}

def test_admin_bootstrap_is_not_public(app):
    assert app.test_client().post("/v1/admin/create-admin", json={}).status_code == 401
