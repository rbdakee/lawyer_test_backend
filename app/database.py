import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from typing import Optional


# Lazy initialization для Firebase
_db = None


# Инициализация Firebase
def init_firebase():
    """Инициализирует Firebase Admin SDK"""
    if not firebase_admin._apps:
        # Получаем credentials из переменной окружения
        firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
        
        if firebase_credentials:
            # Если credentials в виде JSON строки
            try:
                cred_dict = json.loads(firebase_credentials)
                cred = credentials.Certificate(cred_dict)
            except json.JSONDecodeError:
                # Если это путь к файлу
                cred = credentials.Certificate(firebase_credentials)
        else:
            # Используем default credentials (для локальной разработки можно использовать файл)
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            else:
                # Для продакшена может использоваться default credentials
                cred = credentials.ApplicationDefault()
        
        firebase_admin.initialize_app(cred)
    
    return firestore.client()


def get_db():
    """Получить экземпляр Firestore (lazy initialization)"""
    global _db
    if _db is None:
        _db = init_firebase()
    return _db


# Для обратной совместимости - используем функцию вместо прямого доступа
def db():
    """Получить экземпляр Firestore (alias для get_db)"""
    return get_db()


# Коллекции
USERS_COLLECTION = "users"
QUESTIONS_COLLECTION = "questions"
EXAMS_COLLECTION = "exams"
REPORTS_COLLECTION = "reports"


def get_collection(collection_name: str):
    """Получить ссылку на коллекцию"""
    return get_db().collection(collection_name)

