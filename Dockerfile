FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE=/data/todo.db

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app app.py ./
COPY --chown=app:app templates ./templates
COPY --chown=app:app static ./static

RUN mkdir -p /data && chown app:app /data

USER app

VOLUME ["/data"]
EXPOSE 8888

CMD ["gunicorn", "--bind", "0.0.0.0:8888", "--workers", "2", "--access-logfile", "-", "app:app"]
