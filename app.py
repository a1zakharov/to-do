from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from time import perf_counter

from flask import Flask, g, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("DATABASE", str(BASE_DIR / "todo.db"))
    )
    app.logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"], timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA busy_timeout = 10000")
        return g.db

    def task_to_dict(task):
        return {
            "id": task["id"],
            "title": task["title"],
            "completed": bool(task["completed"]),
            "created_at": task["created_at"],
        }

    def find_task(task_id):
        return get_db().execute(
            "SELECT id, title, completed, created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        get_db().execute("PRAGMA journal_mode = WAL")
        get_db().execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        get_db().commit()

    @app.before_request
    def start_request_timer():
        g.request_started_at = perf_counter()

    @app.after_request
    def log_failed_or_slow_request(response):
        duration_ms = (perf_counter() - g.request_started_at) * 1000
        if response.status_code >= 400:
            app.logger.warning(
                "request_failed method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )
        elif duration_ms >= 500:
            app.logger.warning(
                "request_slow method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )
        return response

    @app.errorhandler(sqlite3.Error)
    def handle_database_error(error):
        app.logger.exception("database_error", exc_info=error)
        return jsonify(error="Database error"), 500

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return jsonify(status="ok")

    @app.get("/api/tasks")
    def get_tasks():
        tasks = get_db().execute(
            "SELECT id, title, completed, created_at FROM tasks ORDER BY id DESC"
        ).fetchall()
        return jsonify([task_to_dict(task) for task in tasks])

    @app.post("/api/tasks")
    def create_task():
        data = request.get_json(silent=True) or {}
        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            return jsonify(error="Title is required"), 400

        title = title.strip()
        created_at = datetime.now(timezone.utc).isoformat()
        cursor = get_db().execute(
            "INSERT INTO tasks (title, created_at) VALUES (?, ?)",
            (title, created_at),
        )
        get_db().commit()
        task = find_task(cursor.lastrowid)
        app.logger.info("task_created task_id=%s", task["id"])
        return jsonify(task_to_dict(task)), 201

    @app.put("/api/tasks/<int:task_id>")
    def update_task(task_id):
        task = find_task(task_id)
        if task is None:
            return jsonify(error="Task not found"), 404

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="JSON body is required"), 400

        title = task["title"]
        completed = bool(task["completed"])
        changed = False

        if "title" in data:
            if not isinstance(data["title"], str) or not data["title"].strip():
                return jsonify(error="Title is required"), 400
            title = data["title"].strip()
            changed = True

        if "completed" in data:
            if not isinstance(data["completed"], bool):
                return jsonify(error="Completed must be a boolean"), 400
            completed = data["completed"]
            changed = True

        if not changed:
            return jsonify(error="No supported fields provided"), 400

        get_db().execute(
            "UPDATE tasks SET title = ?, completed = ? WHERE id = ?",
            (title, int(completed), task_id),
        )
        get_db().commit()
        app.logger.info(
            "task_updated task_id=%s fields=%s",
            task_id,
            ",".join(key for key in ("title", "completed") if key in data),
        )
        return jsonify(task_to_dict(find_task(task_id)))

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id):
        if find_task(task_id) is None:
            return jsonify(error="Task not found"), 404

        get_db().execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        get_db().commit()
        app.logger.info("task_deleted task_id=%s", task_id)
        return "", 204

    with app.app_context():
        init_db()

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
