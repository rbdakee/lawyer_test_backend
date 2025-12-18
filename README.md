# Lawyer Test Backend

FastAPI backend для системы подготовки к экзаменам для юристов.

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
uvicorn app.main:app --reload
```

API будет доступно по адресу: http://localhost:8000

## Endpoints

- `GET /api/questions` - получить все вопросы
- `GET /api/questions/demo` - получить 15 случайных вопросов для демо
- `GET /api/questions/exam` - получить вопросы для экзамена

