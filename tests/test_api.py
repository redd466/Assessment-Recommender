from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_is_helpful():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["endpoints"]["chat"] == "/chat"


def test_chat_schema():
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Hiring a Java developer"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"reply", "recommendations", "end_of_conversation"}
    assert isinstance(body["recommendations"], list)
