"""认证与令牌生命周期测试：注册/登录/刷新轮换/复用检测/登出/权限。"""
from tests.conftest import register_and_login, register_user


def test_register_login_me(client):
    headers = register_and_login(client, "u1@example.com")
    resp = client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["user"]["email"] == "u1@example.com"
    assert resp.json()["code"] == "OK"
    assert resp.json()["request_id"]


def test_register_duplicate_email(client):
    client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "Passw0rd!123"})
    resp = client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "Passw0rd!123"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "EMAIL_TAKEN"


def test_login_wrong_password(client):
    register_user("u2@example.com")
    resp = client.post("/api/v1/auth/login", json={"email": "u2@example.com", "password": "wrong!"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "BAD_CREDENTIALS"


def test_unauthenticated_get_me(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"


def test_refresh_rotation_and_reuse_detection(client):
    register_user("u3@example.com")
    resp = client.post("/api/v1/auth/login", json={"email": "u3@example.com", "password": "Passw0rd!123"})
    tokens = resp.json()["data"]
    old_refresh = tokens["refresh_token"]

    # 正常轮换：旧 refresh 换新对
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200, resp.text
    new_tokens = resp.json()["data"]
    assert new_tokens["refresh_token"] != old_refresh

    # 复用已轮换的旧 refresh → 撤销整条会话链
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401
    assert resp.json()["code"] == "REFRESH_TOKEN_INVALID"

    # 新 refresh 也应被撤销（复用攻击防御）
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert resp.status_code == 401


def test_logout_revokes_session(client):
    headers = register_and_login(client, "u4@example.com")
    resp = client.post("/api/v1/auth/logout", headers=headers)
    assert resp.status_code == 200
    resp = client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 401


def test_validation_error_envelope(client):
    resp = client.post("/api/v1/auth/register", json={"email": "bad-email", "password": "123"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "errors" in (body["data"] or {})
    assert body["request_id"]
