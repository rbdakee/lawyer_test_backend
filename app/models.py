from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class LegislationSection(str, Enum):
    """Разделы законодательства"""
    CIVIL_CODE = "civil_code"  # Гражданский кодекс
    CIVIL_PROCESS_CODE = "civil_process_code"  # Гражданский процессуальный кодекс
    CRIMINAL_CODE = "criminal_code"  # Уголовный кодекс
    CRIMINAL_PROCESS_CODE = "criminal_process_code"  # Уголовно процессуальный кодекс
    ADMINISTRATIVE_OFFENSES_CODE = "administrative_offenses_code"  # Кодекс об административных правонарушениях
    ANTI_CORRUPTION_LAW = "anti_corruption_law"  # Закон "О противодействии коррупции"
    ADMINISTRATIVE_PROCEDURE_CODE = "administrative_procedure_code"  # Административный процедурно-процессуальный кодекс
    ADVOCACY_LAW = "advocacy_law"  # Закон "Об адвокатской деятельности и юридической помощи"
    AML_LAW = "aml_law"  # Закон "О противодействии легализации (отмыванию) доходов..."


class TestMode(str, Enum):
    """Режимы тестирования"""
    EXAM = "exam"  # Экзамен
    DEMO = "demo"  # Демо
    TRAINER = "trainer"  # Тренажер


# Модели для авторизации
class UserRegister(BaseModel):
    phone: str
    password: str
    name: str


class UserLogin(BaseModel):
    phone: str
    password: str


class UserResponse(BaseModel):
    id: str
    phone: str
    name: str
    is_admin: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Модели для вопросов
class QuestionOption(BaseModel):
    kz: str
    ru: str


class QuestionText(BaseModel):
    kz: str
    ru: str


class QuestionCreate(BaseModel):
    question: QuestionText
    options: List[QuestionOption]
    correct: int  # 0-3
    explanation: QuestionText
    section: LegislationSection


class QuestionUpdate(BaseModel):
    question: Optional[QuestionText] = None
    options: Optional[List[QuestionOption]] = None
    correct: Optional[int] = None
    explanation: Optional[QuestionText] = None
    section: Optional[LegislationSection] = None


class QuestionResponse(BaseModel):
    id: str
    question: str  # Для конкретного языка
    options: List[str]  # Для конкретного языка
    correct: int
    explanation: str  # Для конкретного языка
    section: str
    section_name: Dict[str, str]  # Название раздела на kz и ru


# Модели для экзаменов
class ExamAnswer(BaseModel):
    question_id: str
    answer: int  # 0-3


class ExamSubmit(BaseModel):
    mode: TestMode
    answers: List[ExamAnswer]
    section: Optional[LegislationSection] = None  # Для тренажера
    time_spent: Optional[int] = None  # Время в секундах


class ExamResult(BaseModel):
    id: str
    user_id: str
    mode: TestMode
    total_questions: int
    correct_answers: int
    score: float  # Процент
    passed: bool
    section: Optional[str] = None
    section_results: Optional[Dict[str, Dict[str, int]]] = None  # {section: {"correct": X, "total": Y}}
    time_spent: Optional[int] = None
    created_at: datetime


class ExamHistoryResponse(BaseModel):
    exams: List[ExamResult]
    total_exams: int
    overall_statistics: Dict[str, Dict[str, int]]  # {section: {"correct": X, "total": Y}}


# Модели для Report
class ReportCreate(BaseModel):
    text: str


# Модели для фильтров
class QuestionFilter(BaseModel):
    section: Optional[LegislationSection] = None
    lang: str = "kz"
    limit: Optional[int] = None


# Модели для админки
class AdminQuestion(BaseModel):
    """Модель вопроса для админки (с kz/ru полями)"""
    id: str
    question: Dict[str, str]  # {"kz": "...", "ru": "..."}
    options: List[Dict[str, str]]  # [{"kz": "...", "ru": "..."}, ...]
    correct: int
    explanation: Dict[str, str]  # {"kz": "...", "ru": "..."}
    section: str
    section_name: Dict[str, str]  # {"kz": "...", "ru": "..."}


class PaginatedResponse(BaseModel):
    """Модель пагинированного ответа"""
    items: List[AdminQuestion]
    total: int
    page: int
    page_size: int
    total_pages: int


# Названия разделов
LEGISLATION_NAMES = {
    LegislationSection.CIVIL_CODE: {
        "kz": "Азаматтық кодекс",
        "ru": "Гражданский кодекс"
    },
    LegislationSection.CIVIL_PROCESS_CODE: {
        "kz": "Азаматтық процестік кодекс",
        "ru": "Гражданский процессуальный кодекс"
    },
    LegislationSection.CRIMINAL_CODE: {
        "kz": "Қылмыстық кодекс",
        "ru": "Уголовный кодекс"
    },
    LegislationSection.CRIMINAL_PROCESS_CODE: {
        "kz": "Қылмыстық процестік кодекс",
        "ru": "Уголовно процессуальный кодекс"
    },
    LegislationSection.ADMINISTRATIVE_OFFENSES_CODE: {
        "kz": "Әкімшілік құқықбұзушылықтар туралы кодекс",
        "ru": "Кодекс об административных правонарушениях"
    },
    LegislationSection.ANTI_CORRUPTION_LAW: {
        "kz": "Коррупцияға қарсы күрес туралы заң",
        "ru": "Закон \"О противодействии коррупции\""
    },
    LegislationSection.ADMINISTRATIVE_PROCEDURE_CODE: {
        "kz": "Әкімшілік процедуралық-процестік кодекс",
        "ru": "Административный процедурно-процессуальный кодекс"
    },
    LegislationSection.ADVOCACY_LAW: {
        "kz": "Адвокаттық қызмет және заңды көмек туралы заң",
        "ru": "Закон \"Об адвокатской деятельности и юридической помощи\""
    },
    LegislationSection.AML_LAW: {
        "kz": "Қылмыстық жолмен алынған кірістерді легализациялауға (ақтауға) қарсы күрес және терроризмді қаржыландыруға қарсы күрес туралы заң",
        "ru": "Закон \"О противодействии легализации (отмыванию) доходов, полученных преступным путем, и финансированию терроризма\""
    }
}

