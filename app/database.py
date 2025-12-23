import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from typing import Optional


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


# Получаем экземпляр Firestore (инициализация при импорте модуля)
db = init_firebase()


# Коллекции
USERS_COLLECTION = "users"
QUESTIONS_COLLECTION = "questions"
EXAMS_COLLECTION = "exams"
REPORTS_COLLECTION = "reports"


def get_collection(collection_name: str):
    """Получить ссылку на коллекцию"""
    return db.collection(collection_name)

