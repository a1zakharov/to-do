from concurrent.futures import ThreadPoolExecutor
import logging
import sqlite3

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
    })


@pytest.fixture()
def client(app):
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


def test_index_and_health(client):
    page = client.get("/")
    health = client.get("/health")

    assert page.status_code == 200
    assert b"My To-Do" in page.data
    assert health.status_code == 200
    assert health.json == {"status": "ok"}


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


@pytest.mark.parametrize(
    "payload",
    [
        {"completed": "yes"},
        {"completed": 1},
        {"title": "   "},
        {"unknown": True},
    ],
)
def test_reject_invalid_updates(client, payload):
    task = create_task(client).json

    response = client.put(f"/api/tasks/{task['id']}", json=payload)

    assert response.status_code == 400
    assert "error" in response.json


def test_database_persists_after_app_recreation(app):
    first_client = app.test_client()
    create_task(first_client, "Сохранить меня")

    restarted_app = create_app({
        "TESTING": True,
        "DATABASE": app.config["DATABASE"],
    })
    tasks = restarted_app.test_client().get("/api/tasks").json

    assert [task["title"] for task in tasks] == ["Сохранить меня"]


def test_concurrent_task_creation(app):
    def submit_task(number):
        with app.test_client() as thread_client:
            return create_task(thread_client, f"Задача {number}").status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(submit_task, range(20)))

    assert statuses == [201] * 20
    assert len(app.test_client().get("/api/tasks").json) == 20


def test_sqlite_uses_wal_mode(app):
    with sqlite3.connect(app.config["DATABASE"]) as database:
        journal_mode = database.execute("PRAGMA journal_mode").fetchone()[0]

    assert journal_mode == "wal"


def test_database_errors_are_logged_as_json(app, caplog):
    with sqlite3.connect(app.config["DATABASE"]) as database:
        database.execute("DROP TABLE tasks")

    with caplog.at_level(logging.ERROR, logger=app.logger.name):
        response = app.test_client().get("/api/tasks")

    assert response.status_code == 500
    assert response.json == {"error": "Database error"}
    assert "database_error" in caplog.text


def test_failed_requests_are_logged(app, caplog):
    with caplog.at_level(logging.WARNING, logger=app.logger.name):
        response = app.test_client().post("/api/tasks", json={"title": ""})

    assert response.status_code == 400
    assert "request_failed method=POST path=/api/tasks status=400" in caplog.text
