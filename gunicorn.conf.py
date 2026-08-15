import os


bind = os.environ.get("BIND", "0.0.0.0:8888")
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = 30
graceful_timeout = 30
keepalive = 5
preload_app = True

accesslog = "-"
errorlog = "-"
capture_output = True
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
access_log_format = (
    "client=%(h)s method=%(m)s path=%(U)s status=%(s)s "
    "bytes=%(B)s duration_ms=%(M)s user_agent=\"%(a)s\""
)
