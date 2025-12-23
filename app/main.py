from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import json
import random
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

from .database import db, USERS_COLLECTION, QUESTIONS_COLLECTION, EXAMS_COLLECTION, REPORTS_COLLECTION
from firebase_admin import firestore
from .models import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse, QuestionFilter,
    ExamSubmit, ExamResult, ExamHistoryResponse,
    ReportCreate,
    LegislationSection, TestMode, LEGISLATION_NAMES,
    AdminQuestion, PaginatedResponse,
    AdminQuestion, PaginatedResponse
)
from .auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_current_admin_user
)
from .middleware import TokenAuthMiddleware

load_dotenv()

app = FastAPI(title="Lawyer Test API")

# CORS middleware
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

origin_regex = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавляем защиту через SECRET_LOCAL_TOKEN
SECRET_LOCAL_TOKEN = os.getenv("SECRET_LOCAL_TOKEN")
if SECRET_LOCAL_TOKEN:
    app.add_middleware(TokenAuthMiddleware)

# Путь к файлу переводов
TRANSLATIONS_PATH = Path(__file__).parent / "translations.json"
TRANSLATIONS_COLLECTION = "translations"


_translations_cache = None

def load_translations() -> dict:
    """Загружает переводы из Firebase или из JSON файла (fallback)"""
    global _translations_cache
    
    # Используем кэш, если он уже загружен
    if _translations_cache is not None:
        return _translations_cache
    
    try:
        # Пытаемся загрузить из Firebase
        translations_ref = db.collection(TRANSLATIONS_COLLECTION)
        docs = translations_ref.get()
        
        if docs:
            translations = {}
            for doc in docs:
                lang = doc.id
                translations[lang] = doc.to_dict()
            
            if translations:
                print(f"✅ Переводы загружены из Firebase: {', '.join(translations.keys())}")
                _translations_cache = translations
                return translations
    except Exception as e:
        print(f"⚠️  Не удалось загрузить переводы из Firebase: {e}")
        print("   Используется fallback на JSON файл")
    
    # Fallback: загружаем из JSON файла
    if TRANSLATIONS_PATH.exists():
        with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
            translations = json.load(f)
        print(f"✅ Переводы загружены из JSON файла: {', '.join(translations.keys())}")
        _translations_cache = translations
        return translations
    else:
        raise FileNotFoundError(f"Файл переводов не найден: {TRANSLATIONS_PATH}")


# ==================== ПУБЛИЧНЫЕ ENDPOINTS ====================

@app.get("/")
def read_root():
    return {"message": "Lawyer Test API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint для keep-alive и мониторинга"""
    try:
        # Проверяем подключение к Firebase
        # Простая проверка доступности
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "firebase": "connected"
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@app.get("/api/translations/{lang}")
def get_translations(lang: str):
    """Получить переводы для указанного языка (kz или ru)"""
    translations = load_translations()
    if lang not in translations:
        lang = "kz"
    return {"lang": lang, "translations": translations[lang]}


@app.get("/api/translations")
def get_all_translations():
    """Получить все доступные переводы"""
    translations = load_translations()
    return translations


@app.get("/api/legislation-sections")
def get_legislation_sections(lang: str = "kz"):
    """Получить список всех разделов законодательства"""
    sections = []
    for section in LegislationSection:
        sections.append({
            "id": section.value,
            "name": LEGISLATION_NAMES[section][lang]
        })
    return {"sections": sections}


# ==================== АВТОРИЗАЦИЯ ====================

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь с таким телефоном
    users_ref = db.collection(USERS_COLLECTION)
    query = users_ref.where("phone", "==", user_data.phone).limit(1).get()
    
    if query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким телефоном уже существует"
        )
    
    # Создаем нового пользователя
    user_dict = {
        "phone": user_data.phone,
        "password_hash": get_password_hash(user_data.password),
        "name": user_data.name,
        "is_admin": False,
        "created_at": datetime.utcnow()
    }
    
    doc_ref = db.collection(USERS_COLLECTION).add(user_dict)
    user_id = doc_ref[1].id
    
    # Создаем токен
    access_token = create_access_token(data={"sub": user_id})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user_id,
            phone=user_data.phone,
            name=user_data.name,
            is_admin=False
        )
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Вход пользователя"""
    # Ищем пользователя по телефону
    users_ref = db.collection(USERS_COLLECTION)
    query = users_ref.where("phone", "==", user_data.phone).limit(1).get()
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный телефон или пароль"
        )
    
    user_doc = query[0]
    user_data_dict = user_doc.to_dict()
    
    # Проверяем пароль
    if not verify_password(user_data.password, user_data_dict.get("password_hash")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный телефон или пароль"
        )
    
    # Создаем токен
    access_token = create_access_token(data={"sub": user_doc.id})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user_doc.id,
            phone=user_data_dict.get("phone"),
            name=user_data_dict.get("name"),
            is_admin=user_data_dict.get("is_admin", False)
        )
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user


# ==================== ВОПРОСЫ ====================

def format_question_for_language(question_doc, lang: str) -> QuestionResponse:
    """Форматирует вопрос из Firebase для указанного языка"""
    question_data = question_doc.to_dict()
    section = LegislationSection(question_data.get("section"))
    
    return QuestionResponse(
        id=question_doc.id,
        question=question_data["question"][lang],
        options=[opt[lang] for opt in question_data["options"]],
        correct=question_data["correct"],
        explanation=question_data["explanation"][lang],
        section=section.value,
        section_name=LEGISLATION_NAMES[section]
    )


@app.get("/api/questions", response_model=List[QuestionResponse])
async def get_questions(
    section: Optional[LegislationSection] = None,
    lang: str = "kz",
    limit: Optional[int] = None
):
    """Получить вопросы (с фильтрацией по разделу)"""
    questions_ref = db.collection(QUESTIONS_COLLECTION)
    
    if section:
        query = questions_ref.where("section", "==", section.value)
    else:
        query = questions_ref
    
    questions = query.get()
    
    formatted_questions = [format_question_for_language(q, lang) for q in questions]
    
    if limit:
        formatted_questions = formatted_questions[:limit]
    
    return formatted_questions


@app.get("/api/questions/demo", response_model=List[QuestionResponse])
async def get_demo_questions(lang: str = "kz"):
    """Получить 20 случайных вопросов для демо режима"""
    questions_ref = db.collection(QUESTIONS_COLLECTION)
    all_questions = questions_ref.get()
    
    if len(all_questions) == 0:
        return []
    
    # Выбираем случайные 20 вопросов
    selected_questions = random.sample(all_questions, min(20, len(all_questions)))
    
    formatted_questions = [format_question_for_language(q, lang) for q in selected_questions]
    return formatted_questions


@app.get("/api/questions/exam", response_model=List[QuestionResponse])
async def get_exam_questions(lang: str = "kz"):
    """Получить 100 случайных вопросов для экзамена"""
    questions_ref = db.collection(QUESTIONS_COLLECTION)
    all_questions = questions_ref.get()
    
    if len(all_questions) == 0:
        return []
    
    # Выбираем случайные 100 вопросов
    selected_questions = random.sample(all_questions, min(100, len(all_questions)))
    
    formatted_questions = [format_question_for_language(q, lang) for q in selected_questions]
    return formatted_questions


@app.get("/api/questions/trainer", response_model=List[QuestionResponse])
async def get_trainer_questions(
    section: LegislationSection,
    lang: str = "kz"
):
    """Получить вопросы для тренажера по конкретному разделу"""
    questions_ref = db.collection(QUESTIONS_COLLECTION)
    query = questions_ref.where("section", "==", section.value)
    questions = query.get()
    
    formatted_questions = [format_question_for_language(q, lang) for q in questions]
    return formatted_questions


@app.get("/api/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: str, lang: str = "kz"):
    """Получить вопрос по ID"""
    question_doc = db.collection(QUESTIONS_COLLECTION).document(question_id).get()
    
    if not question_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос не найден"
        )
    
    return format_question_for_language(question_doc, lang)


# ==================== ЭКЗАМЕНЫ ====================

@app.post("/api/exams/submit", response_model=ExamResult)
async def submit_exam(
    exam_data: ExamSubmit,
    current_user: UserResponse = Depends(get_current_user)
):
    """Отправить результаты экзамена"""
    try:
        # Получаем вопросы для проверки ответов
        questions_ref = db.collection(QUESTIONS_COLLECTION)
        question_ids = [ans.question_id for ans in exam_data.answers]
        
        # Получаем все вопросы
        questions_dict = {}
        for qid in question_ids:
            q_doc = questions_ref.document(qid).get()
            if q_doc.exists:
                questions_dict[qid] = q_doc.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении вопросов: {str(e)}"
        )
    
    # Подсчитываем результаты
    # Используем количество вопросов из экзамена, а не только отвеченных
    total_questions = len(exam_data.answers)
    correct_answers = 0
    section_results = {}  # {section: {"correct": X, "total": Y}}
    
    for answer in exam_data.answers:
        if answer.question_id in questions_dict:
            question = questions_dict[answer.question_id]
            section = question.get("section")
            
            # Подсчитываем по разделам (все вопросы)
            if section:
                if section not in section_results:
                    section_results[section] = {"correct": 0, "total": 0}
                section_results[section]["total"] += 1
            
            # Проверяем ответ только если он валидный (>= 0)
            if answer.answer >= 0:
                if question["correct"] == answer.answer:
                    correct_answers += 1
                    # Учитываем правильный ответ в разделе
                    if section:
                        section_results[section]["correct"] += 1
    
    score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # Определяем, прошел ли экзамен (проходной балл 70)
    passed = score >= 70
    
    # Сохраняем результат
    exam_dict = {
        "user_id": current_user.id,
        "mode": exam_data.mode.value,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "score": score,
        "passed": passed,
        "section": exam_data.section.value if exam_data.section else None,
        "section_results": section_results,
        "time_spent": exam_data.time_spent,
        "answers": [{"question_id": ans.question_id, "answer": ans.answer} for ans in exam_data.answers],  # Сохраняем ответы пользователя
        "created_at": datetime.utcnow()
    }
    
    try:
        doc_ref = db.collection(EXAMS_COLLECTION).add(exam_dict)
        exam_id = doc_ref[1].id
        
        return ExamResult(
            id=exam_id,
            user_id=current_user.id,
            mode=exam_data.mode,
            total_questions=total_questions,
            correct_answers=correct_answers,
            score=score,
            passed=passed,
            section=exam_data.section.value if exam_data.section else None,
            section_results=section_results,
            time_spent=exam_data.time_spent,
            created_at=exam_dict["created_at"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при сохранении результата экзамена: {str(e)}"
        )


@app.get("/api/exams/history", response_model=ExamHistoryResponse)
async def get_exam_history(
    current_user: UserResponse = Depends(get_current_user)
):
    """Получить историю экзаменов пользователя"""
    exams_ref = db.collection(EXAMS_COLLECTION)
    # Используем только where, без order_by, чтобы избежать требования индекса
    # Сортировку делаем в Python
    query = exams_ref.where("user_id", "==", current_user.id)
    exams = query.get()
    
    exam_results = []
    overall_statistics = {}  # {section: {"correct": X, "total": Y}}
    
    for exam_doc in exams:
        exam_data = exam_doc.to_dict()
        
        # Обновляем общую статистику
        section_results = exam_data.get("section_results", {})
        for section, stats in section_results.items():
            if section not in overall_statistics:
                overall_statistics[section] = {"correct": 0, "total": 0}
            overall_statistics[section]["correct"] += stats["correct"]
            overall_statistics[section]["total"] += stats["total"]
        
        exam_results.append(ExamResult(
            id=exam_doc.id,
            user_id=exam_data["user_id"],
            mode=TestMode(exam_data["mode"]),
            total_questions=exam_data["total_questions"],
            correct_answers=exam_data["correct_answers"],
            score=exam_data["score"],
            passed=exam_data["passed"],
            section=exam_data.get("section"),
            section_results=exam_data.get("section_results"),
            time_spent=exam_data.get("time_spent"),
            created_at=exam_data["created_at"]
        ))
    
    # Сортируем результаты по дате создания (от новых к старым)
    exam_results.sort(key=lambda x: x.created_at, reverse=True)
    
    return ExamHistoryResponse(
        exams=exam_results,
        total_exams=len(exam_results),
        overall_statistics=overall_statistics
    )


@app.get("/api/exams/{exam_id}")
async def get_exam_details(
    exam_id: str,
    lang: str = "kz",
    current_user: UserResponse = Depends(get_current_user)
):
    """Получить детали экзамена с вопросами и ответами"""
    try:
        exam_doc = db.collection(EXAMS_COLLECTION).document(exam_id).get()
        
        if not exam_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Экзамен не найден"
            )
        
        exam_data = exam_doc.to_dict()
        
        # Проверяем, что экзамен принадлежит текущему пользователю
        if exam_data["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этому экзамену"
            )
        
        # Получаем вопросы и ответы
        questions_ref = db.collection(QUESTIONS_COLLECTION)
        answers = exam_data.get("answers", [])
        
        questions_with_answers = []
        for answer_data in answers:
            question_id = answer_data["question_id"]
            user_answer = answer_data["answer"]
            
            question_doc = questions_ref.document(question_id).get()
            if question_doc.exists:
                question_dict = question_doc.to_dict()
                formatted_question = format_question_for_language(question_doc, lang)
                
                questions_with_answers.append({
                    **formatted_question.dict(),
                    "user_answer": user_answer,
                    "is_correct": user_answer >= 0 and question_dict.get("correct") == user_answer,
                })
        
        return {
            "exam": {
                "id": exam_id,
                "mode": exam_data["mode"],
                "score": exam_data["score"],
                "correct_answers": exam_data["correct_answers"],
                "total_questions": exam_data["total_questions"],
                "passed": exam_data["passed"],
                "time_spent": exam_data.get("time_spent"),
                "created_at": exam_data["created_at"],
            },
            "questions": questions_with_answers
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка при получении деталей экзамена: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении деталей экзамена: {str(e)}"
        )


# ==================== REPORT ====================

@app.post("/api/reports")
async def create_report(
    report_data: ReportCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Создать отчет (пока не обрабатывается)"""
    report_dict = {
        "user_id": current_user.id,
        "text": report_data.text,
        "created_at": datetime.utcnow(),
        "processed": False
    }
    
    doc_ref = db.collection(REPORTS_COLLECTION).add(report_dict)
    
    return {"id": doc_ref[1].id, "message": "Отчет создан"}


# ==================== АДМИНКА ====================

@app.get("/api/admin/questions", response_model=PaginatedResponse)
async def get_admin_questions(
    page: int = 1,
    page_size: int = 10,
    current_user: UserResponse = Depends(get_current_admin_user)
):
    """Получить вопросы для админки в исходном формате (с kz/ru полями) с пагинацией"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 10
    
    questions_ref = db.collection(QUESTIONS_COLLECTION)
    all_questions = questions_ref.get()
    
    # Получаем общее количество вопросов
    total = len(all_questions)
    
    # Вычисляем индексы для среза
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    # Форматируем только нужные вопросы
    questions = []
    for q_doc in all_questions[start_index:end_index]:
        q_data = q_doc.to_dict()
        section_value = q_data.get("section", "")
        section_name = {"kz": "", "ru": ""}
        try:
            if section_value:
                section = LegislationSection(section_value)
                section_name = LEGISLATION_NAMES.get(section, {"kz": "", "ru": ""})
        except (ValueError, KeyError):
            pass
        
        questions.append(AdminQuestion(
            id=q_doc.id,
            question=q_data.get("question", {}),
            options=q_data.get("options", []),
            correct=q_data.get("correct", 0),
            explanation=q_data.get("explanation", {}),
            section=section_value,
            section_name=section_name
        ))
    
    # Вычисляем общее количество страниц
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return PaginatedResponse(
        items=questions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@app.post("/api/admin/questions", response_model=QuestionResponse)
async def create_question(
    question_data: QuestionCreate,
    lang: str = "kz",
    current_user: UserResponse = Depends(get_current_admin_user)
):
    """Создать новый вопрос (только для админов)"""
    question_dict = {
        "question": question_data.question.dict(),
        "options": [opt.dict() for opt in question_data.options],
        "correct": question_data.correct,
        "explanation": question_data.explanation.dict(),
        "section": question_data.section.value,
        "created_at": datetime.utcnow()
    }
    
    doc_ref = db.collection(QUESTIONS_COLLECTION).add(question_dict)
    question_id = doc_ref[1].id
    
    # Получаем созданный вопрос для возврата
    question_doc = db.collection(QUESTIONS_COLLECTION).document(question_id).get()
    return format_question_for_language(question_doc, lang)


@app.put("/api/admin/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str,
    question_data: QuestionUpdate,
    lang: str = "kz",
    current_user: UserResponse = Depends(get_current_admin_user)
):
    """Обновить вопрос (только для админов)"""
    question_ref = db.collection(QUESTIONS_COLLECTION).document(question_id)
    question_doc = question_ref.get()
    
    if not question_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос не найден"
        )
    
    # Обновляем только переданные поля
    update_dict = {}
    if question_data.question:
        update_dict["question"] = question_data.question.dict()
    if question_data.options:
        update_dict["options"] = [opt.dict() for opt in question_data.options]
    if question_data.correct is not None:
        update_dict["correct"] = question_data.correct
    if question_data.explanation:
        update_dict["explanation"] = question_data.explanation.dict()
    if question_data.section:
        update_dict["section"] = question_data.section.value
    
    update_dict["updated_at"] = datetime.utcnow()
    
    question_ref.update(update_dict)
    
    # Получаем обновленный вопрос
    updated_doc = question_ref.get()
    return format_question_for_language(updated_doc, lang)


@app.delete("/api/admin/questions/{question_id}")
async def delete_question(
    question_id: str,
    current_user: UserResponse = Depends(get_current_admin_user)
):
    """Удалить вопрос (только для админов)"""
    question_ref = db.collection(QUESTIONS_COLLECTION).document(question_id)
    question_doc = question_ref.get()
    
    if not question_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос не найден"
        )
    
    question_ref.delete()
    return {"message": "Вопрос удален"}
