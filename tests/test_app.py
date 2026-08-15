import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
    })
    return app.test_client()


def create_task(client, title="Купить продукты"):
    return client.post("/api/tasks", json={"title": title})


def test_create_task(client):
    response = create_task(client)

    assert response.status_code == 201
    assert response.json["title"] == "Купить продукты"
    assert response.json["completed"] is False
    assert response.json["created_at"]


def test_get_tasks(client):
    create_task(client, "Первая")
    create_task(client, "Вторая")

    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert [task["title"] for task in response.json] == ["Вторая", "Первая"]


def test_update_task_title(client):
    task = create_task(client).json

    response = client.put(f"/api/tasks/{task['id']}", json={"title": "Купить молоко"})

    assert response.status_code == 200
    assert response.json["title"] == "Купить молоко"


def test_complete_and_reopen_task(client):
    task = create_task(client).json

    completed = client.put(f"/api/tasks/{task['id']}", json={"completed": True})
    reopened = client.put(f"/api/tasks/{task['id']}", json={"completed": False})

    assert completed.status_code == 200
    assert completed.json["completed"] is True
    assert reopened.status_code == 200
    assert reopened.json["completed"] is False


def test_delete_task(client):
    task = create_task(client).json

    response = client.delete(f"/api/tasks/{task['id']}")

    assert response.status_code == 204
    assert client.get("/api/tasks").json == []


@pytest.mark.parametrize("payload", [{}, {"title": ""}, {"title": "   "}, {"title": None}])
def test_reject_empty_task(client, payload):
    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 400
    assert response.json == {"error": "Title is required"}


def test_missing_task_returns_404(client):
    assert client.put("/api/tasks/999", json={"completed": True}).status_code == 404
    assert client.delete("/api/tasks/999").status_code == 404
