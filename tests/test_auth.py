def test_signup_and_login(client):
    r = client.post("/auth/signup", json={
        "email": "a@example.com", "full_name": "A", "password": "password123",
    })
    assert r.status_code == 201

    r = client.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_signup_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "full_name": "A", "password": "password123"}
    r1 = client.post("/auth/signup", json=payload)
    r2 = client.post("/auth/signup", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 409


def test_login_wrong_password_rejected(client):
    client.post("/auth/signup", json={
        "email": "b@example.com", "full_name": "B", "password": "correctpass",
    })
    r = client.post("/auth/login", json={"email": "b@example.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_protected_route_requires_token(client):
    r = client.get("/bookings/")
    assert r.status_code == 401


def test_signup_short_password_rejected(client):
    r = client.post("/auth/signup", json={
        "email": "short@example.com", "full_name": "S", "password": "abc",
    })
    assert r.status_code == 422


def test_signup_invalid_email_rejected(client):
    r = client.post("/auth/signup", json={
        "email": "not-an-email", "full_name": "S", "password": "password123",
    })
    assert r.status_code == 422


def test_login_nonexistent_user_rejected(client):
    r = client.post("/auth/login", json={
        "email": "noone@example.com", "password": "password123",
    })
    assert r.status_code == 401


def test_expired_or_invalid_token_rejected(client):
    r = client.get("/bookings/", headers={"Authorization": "Bearer invalid.token.here"})
    assert r.status_code == 401
