from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_info():
    response = client.get("/api")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["endpoints"]["chat"] == "/chat"
    assert body["endpoints"]["app"] == "/"


def test_root_serves_frontend():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "SHL Assessment Recommender" in response.text
    assert "welcome-card" in response.text
    assert 'href="/styles.css"' in response.text


def test_frontend_assets():
    response = client.get("/styles.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")

    response = client.get("/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "")


def test_legacy_app_redirects_home():
    response = client.get("/app/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/"


def test_chat_schema():
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Hiring a Java developer"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"reply", "recommendations", "end_of_conversation"}
    assert isinstance(body["recommendations"], list)
