def test_create_centre(client):
    r = client.post("/centres/", json={"name": "City Diagnostics", "location": "Delhi"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "City Diagnostics"
    assert data["location"] == "Delhi"
    assert "id" in data


def test_list_centres_with_pagination(client):
    client.post("/centres/", json={"name": "A", "location": "Delhi"})
    client.post("/centres/", json={"name": "B", "location": "Mumbai"})
    r = client.get("/centres/")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["has_next"] is False


def test_pagination_limits_results(client):
    for i in range(5):
        client.post("/centres/", json={"name": f"Centre {i}", "location": "Delhi"})
    r = client.get("/centres/?limit=2")
    body = r.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["has_next"] is True


def test_filter_centres_by_location(client):
    client.post("/centres/", json={"name": "A", "location": "Delhi"})
    client.post("/centres/", json={"name": "B", "location": "Mumbai"})
    r = client.get("/centres/?location=delhi")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["location"] == "Delhi"


def test_get_centre(client):
    r = client.post("/centres/", json={"name": "Test", "location": "Delhi"})
    cid = r.json()["id"]
    r = client.get(f"/centres/{cid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Test"


def test_get_nonexistent_centre_returns_404(client):
    r = client.get("/centres/nonexistent-uuid")
    assert r.status_code == 404


def test_add_test_to_centre(client):
    r = client.post("/centres/", json={"name": "Lab", "location": "Delhi"})
    cid = r.json()["id"]
    r = client.post(f"/centres/{cid}/tests", json={"name": "CBC", "price": 500})
    assert r.status_code == 201
    assert r.json()["name"] == "CBC"
    assert r.json()["price"] == 500


def test_add_test_to_nonexistent_centre_returns_404(client):
    r = client.post("/centres/nonexistent-uuid/tests", json={"name": "CBC", "price": 500})
    assert r.status_code == 404


def test_test_price_must_be_positive(client):
    r = client.post("/centres/", json={"name": "Lab", "location": "Delhi"})
    cid = r.json()["id"]
    r = client.post(f"/centres/{cid}/tests", json={"name": "CBC", "price": -100})
    assert r.status_code == 422


def test_list_tests_for_centre(client):
    r = client.post("/centres/", json={"name": "Lab", "location": "Delhi"})
    cid = r.json()["id"]
    client.post(f"/centres/{cid}/tests", json={"name": "CBC", "price": 500})
    client.post(f"/centres/{cid}/tests", json={"name": "LFT", "price": 800})
    r = client.get(f"/centres/{cid}/tests")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_centre_includes_tests_in_response(client):
    r = client.post("/centres/", json={"name": "Lab", "location": "Delhi"})
    cid = r.json()["id"]
    client.post(f"/centres/{cid}/tests", json={"name": "CBC", "price": 500})
    r = client.get(f"/centres/{cid}")
    assert r.status_code == 200
    data = r.json()
    assert len(data["tests"]) == 1
    assert data["tests"][0]["name"] == "CBC"
