from backend.app.api.routes import login_attempts
from backend.app.db.session import SessionLocal
from backend.app.models.entities import User
from backend.app.security.auth import hash_password


def login(client, username, password="initial-test-password"):  # noqa: F811
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def add_user(name, role="investigator"):
    with SessionLocal.begin() as db:
        user = User(username=name, role=role, password_hash=hash_password("initial-test-password"))
        db.add(user)
        db.flush()
        return user.id


def test_logout_revokes_only_current_session(client):  # noqa: F811
    login_attempts.clear()
    add_user("session-test")
    first, second = login(client, "session-test"), login(client, "session-test")
    assert client.post("/api/v1/auth/logout", headers=first).status_code == 200
    assert client.get("/api/v1/auth/me", headers=first).status_code == 401
    assert client.get("/api/v1/auth/me", headers=second).status_code == 200
    assert client.post("/api/v1/auth/logout-all", headers=second).status_code == 200
    assert client.get("/api/v1/auth/me", headers=second).status_code == 401


def test_password_change_checks_current_password_and_revokes_all(client):  # noqa: F811
    login_attempts.clear()
    add_user("password-test")
    first, second = login(client, "password-test"), login(client, "password-test")
    body = {"current_password": "incorrect", "new_password": "new-strong-test-password"}
    assert client.post("/api/v1/auth/password", headers=first, json=body).status_code == 403
    body["current_password"] = "initial-test-password"
    assert client.post("/api/v1/auth/password", headers=first, json=body).status_code == 200
    assert client.get("/api/v1/auth/me", headers=second).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "password-test", "password": "initial-test-password"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers=login(client, "password-test", "new-strong-test-password")).status_code == 200


def test_administrator_session_revocation_is_role_restricted(client):  # noqa: F811
    login_attempts.clear()
    target_id = add_user("revocation-target")
    target = login(client, "revocation-target")
    assert client.post(f"/api/v1/users/{target_id}/sessions/revoke", headers=target).status_code == 403
    admin = login(client, "admin", "test-password-123")
    assert client.post(f"/api/v1/users/{target_id}/sessions/revoke", headers=admin).status_code == 200
    assert client.get("/api/v1/auth/me", headers=target).status_code == 401
