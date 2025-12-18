from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import random
import os
from pathlib import Path
from typing import List

app = FastAPI(title="Lawyer Test API")

# CORS middleware для работы с фронтендом
# В продакшене используем переменную окружения FRONTEND_URL, для локальной разработки - localhost
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Для продакшена лучше разрешить все Vercel домены через regex или просто использовать allow_origin_regex
# Но для простоты используем список разрешенных origins
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Добавляем фронтенд URL если он указан
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

# Используем regex для поддержки всех Vercel доменов
origin_regex = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Путь к файлу базы знаний
KNOWLEDGE_BASE_PATH = Path(__file__).parent / "knowledge_base.json"
TRANSLATIONS_PATH = Path(__file__).parent / "translations.json"


def load_knowledge_base() -> dict:
    """Загружает базу знаний из JSON файла"""
    with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_translations() -> dict:
    """Загружает переводы из JSON файла"""
    with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/")
def read_root():
    return {"message": "Lawyer Test API is running"}


def format_question_for_language(question: dict, lang: str) -> dict:
    """Форматирует вопрос для указанного языка"""
    if lang not in ["kz", "ru"]:
        lang = "kz"  # По умолчанию казахский
    
    formatted = {
        "id": question["id"],
        "question": question["question"][lang],
        "options": [option[lang] for option in question["options"]],
        "correct": question["correct"],
        "explanation": question["explanation"][lang]
    }
    return formatted


@app.get("/api/questions")
def get_all_questions(lang: str = "kz"):
    """Получить все вопросы из базы знаний для указанного языка"""
    knowledge_base = load_knowledge_base()
    all_questions = knowledge_base["questions"]
    formatted_questions = [format_question_for_language(q, lang) for q in all_questions]
    return {"questions": formatted_questions}


@app.get("/api/questions/demo")
def get_demo_questions(lang: str = "kz"):
    """Получить 15 случайных вопросов для демо режима"""
    knowledge_base = load_knowledge_base()
    all_questions = knowledge_base["questions"]
    
    # Выбираем случайные 15 вопросов
    selected_questions = random.sample(all_questions, min(15, len(all_questions)))
    
    # Форматируем для указанного языка
    formatted_questions = [format_question_for_language(q, lang) for q in selected_questions]
    
    return {"questions": formatted_questions}


@app.get("/api/questions/exam")
def get_exam_questions(lang: str = "kz"):
    """Получить вопросы для экзамена (можно настроить количество)"""
    knowledge_base = load_knowledge_base()
    all_questions = knowledge_base["questions"]
    
    # Для экзамена тоже можно использовать случайный выбор
    # Или все вопросы - зависит от требований
    selected_questions = random.sample(all_questions, min(20, len(all_questions)))
    
    # Форматируем для указанного языка
    formatted_questions = [format_question_for_language(q, lang) for q in selected_questions]
    
    return {"questions": formatted_questions}


@app.get("/api/translations/{lang}")
def get_translations(lang: str):
    """Получить переводы для указанного языка (kz или ru)"""
    translations = load_translations()
    if lang not in translations:
        lang = "kz"  # По умолчанию казахский
    return {"lang": lang, "translations": translations[lang]}


@app.get("/api/translations")
def get_all_translations():
    """Получить все доступные переводы"""
    translations = load_translations()
    return translations

