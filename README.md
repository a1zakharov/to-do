# My To-Do

Простой веб-список задач на Flask и SQLite. Задачи можно создавать,
редактировать, отмечать выполненными, возвращать в активные, фильтровать и
удалять. Данные сохраняются в локальном файле `todo.db`.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Откройте <http://127.0.0.1:5000>.

База данных и таблица создаются автоматически при первом запуске.

## Запуск в Docker

Соберите образ:

```bash
docker build -t todo-app .
```

Запустите контейнер с постоянным хранилищем для SQLite:

```bash
docker run -d \
  --name todo-app \
  --restart unless-stopped \
  -p 8888:8888 \
  -v todo-data:/data \
  todo-app
```

Приложение будет доступно по адресу <http://127.0.0.1:8888>. Для доступа с
другого устройства используйте IP-адрес сервера, например
`http://192.168.1.50:8888`.

Остановить и удалить контейнер можно командами:

```bash
docker stop todo-app
docker rm todo-app
```

Именованный volume `todo-data` при этом не удаляется, поэтому задачи сохранятся.

## Тесты

```bash
pytest
```
