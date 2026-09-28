from datetime import datetime, timedelta, timezone
from unittest.mock import patch


def _future_iso():
    """Return an ISO-8601 timestamp 7 days from now (always in the future)."""
    return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


def _create_centre_with_test(client):
    r = client.post("/centres/", json={"name": "City Diagnostics", "location": "Delhi"})
    centre = r.json()
    r = client.post(f"/centres/{centre['id']}/tests", json={"name": "CBC", "price": 500})
    test = r.json()
    return centre, test


# ---- Booking CRUD ----

def test_create_booking(client, auth_headers):
    _, test = _create_centre_with_test(client)
    r = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "PENDING"
    assert body["amount"] == 500


def test_booking_requires_valid_test_id(client, auth_headers):
    r = client.post(
        "/bookings/",
        json={"test_id": "does-not-exist", "appointment_time": _future_iso()},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_booking_past_appointment_rejected(client, auth_headers):
    _, test = _create_centre_with_test(client)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    r = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": past},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_list_my_bookings_with_pagination(client, auth_headers):
    _, test = _create_centre_with_test(client)
    for _ in range(3):
        client.post(
            "/bookings/",
            json={"test_id": test["id"], "appointment_time": _future_iso()},
            headers=auth_headers,
        )
    r = client.get("/bookings/?limit=2", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["has_next"] is True


def test_pagination_metadata_on_empty(client, auth_headers):
    r = client.get("/bookings/", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["has_next"] is False


def test_cannot_view_other_users_booking(client, auth_headers):
    _, test = _create_centre_with_test(client)
    r = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    )
    booking_id = r.json()["id"]

    # second user
    client.post("/auth/signup", json={
        "email": "other@example.com", "full_name": "Other", "password": "password123",
    })
    login = client.post("/auth/login", json={
        "email": "other@example.com", "password": "password123",
    })
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = client.get(f"/bookings/{booking_id}", headers=other_headers)
    assert r.status_code == 403


# ---- Cancel ----

def test_cancel_pending_booking(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()
    r = client.post(f"/bookings/{booking['id']}/cancel", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED"


def test_cancel_confirmed_booking_rejected(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()
    client.post("/payments/webhook/", json={
        "event_id": "evt-conf-1",
        "booking_id": booking["id"],
        "status": "SUCCESS",
    })
    r = client.post(f"/bookings/{booking['id']}/cancel", headers=auth_headers)
    assert r.status_code == 409


def test_cancel_nonexistent_booking_404(client, auth_headers):
    r = client.post("/bookings/does-not-exist/cancel", headers=auth_headers)
    assert r.status_code == 404


# ---- Webhook ----

def test_webhook_confirms_booking(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()

    r = client.post("/payments/webhook/", json={
        "event_id": "evt-123",
        "booking_id": booking["id"],
        "status": "SUCCESS",
        "provider_reference": "ref-123",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "processed"

    updated = client.get(f"/bookings/{booking['id']}", headers=auth_headers).json()
    assert updated["status"] == "CONFIRMED"


def test_webhook_failed_payment_marks_booking_failed(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()

    r = client.post("/payments/webhook/", json={
        "event_id": "evt-fail-1",
        "booking_id": booking["id"],
        "status": "FAILED",
    })
    assert r.status_code == 200
    updated = client.get(f"/bookings/{booking['id']}", headers=auth_headers).json()
    assert updated["status"] == "FAILED"


def test_webhook_is_idempotent_on_duplicate_event_id(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()

    event = {
        "event_id": "evt-dup-1",
        "booking_id": booking["id"],
        "status": "SUCCESS",
        "provider_reference": "ref-dup-1",
    }

    r1 = client.post("/payments/webhook/", json=event)
    r2 = client.post("/payments/webhook/", json=event)
    r3 = client.post("/payments/webhook/", json=event)

    assert r1.json()["status"] == "processed"
    assert r2.json()["status"] == "already_processed"
    assert r3.json()["status"] == "already_processed"

    # Booking stays CONFIRMED — no corruption from duplicates.
    updated = client.get(f"/bookings/{booking['id']}", headers=auth_headers).json()
    assert updated["status"] == "CONFIRMED"


def test_webhook_unknown_booking_returns_404(client):
    r = client.post("/payments/webhook/", json={
        "event_id": "evt-999",
        "booking_id": "nonexistent",
        "status": "SUCCESS",
    })
    assert r.status_code == 404


# ---- Simulated payment ----

def test_simulated_payment_success(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()

    with patch("app.routers.payments.random.random", return_value=0.1):
        r = client.post(
            "/payments/",
            json={"booking_id": booking["id"]},
            headers=auth_headers,
        )
    assert r.status_code == 201
    assert r.json()["status"] == "SUCCESS"


def test_simulated_payment_failure(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()

    with patch("app.routers.payments.random.random", return_value=0.99):
        r = client.post(
            "/payments/",
            json={"booking_id": booking["id"]},
            headers=auth_headers,
        )
    assert r.status_code == 201
    assert r.json()["status"] == "FAILED"


def test_double_payment_rejected(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()

    # Confirm via webhook first
    client.post("/payments/webhook/", json={
        "event_id": "evt-pay-1",
        "booking_id": booking["id"],
        "status": "SUCCESS",
    })

    # Attempt to pay again — rejected because status is CONFIRMED
    r = client.post(
        "/payments/",
        json={"booking_id": booking["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 409


def test_payment_for_nonexistent_booking(client, auth_headers):
    r = client.post(
        "/payments/",
        json={"booking_id": "does-not-exist"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_payment_for_other_users_booking(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()

    # Create second user
    client.post("/auth/signup", json={
        "email": "other@example.com", "full_name": "Other", "password": "password123",
    })
    login = client.post("/auth/login", json={
        "email": "other@example.com", "password": "password123",
    })
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = client.post(
        "/payments/",
        json={"booking_id": booking["id"]},
        headers=other_headers,
    )
    assert r.status_code == 403


def test_get_payment(client, auth_headers):
    _, test = _create_centre_with_test(client)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": _future_iso()},
        headers=auth_headers,
    ).json()

    with patch("app.routers.payments.random.random", return_value=0.1):
        payment = client.post(
            "/payments/",
            json={"booking_id": booking["id"]},
            headers=auth_headers,
        ).json()

    r = client.get(f"/payments/{payment['id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == payment["id"]


def test_get_payment_not_found(client, auth_headers):
    r = client.get("/payments/does-not-exist", headers=auth_headers)
    assert r.status_code == 404
