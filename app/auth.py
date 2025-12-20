from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import hashlib
import bcrypt
from .database import db, USERS_COLLECTION
from .models import UserResponse

# Настройки JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 дней

# HTTP Bearer для токенов
security = HTTPBearer()


def _prepare_password_for_bcrypt(password: str) -> bytes:
    """Подготавливает пароль для bcrypt (bcrypt имеет ограничение 72 байта)"""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) <= 72:
        return password_bytes
    
    # Если пароль длиннее 72 байт, используем SHA256 для предварительного хеширования
    # Это стандартный подход для работы с bcrypt и длинными паролями
    hash_obj = hashlib.sha256(password_bytes)
    return hash_obj.digest()  # Возвращаем bytes, а не hexdigest


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль"""
    try:
        # hashed_password должен быть строкой в формате bcrypt
        prepared_password = _prepare_password_for_bcrypt(plain_password)
        # Декодируем хеш из строки в bytes
        hashed_bytes = hashed_password.encode('utf-8')
        # Проверяем пароль
        return bcrypt.checkpw(prepared_password, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Хеширует пароль"""
    prepared_password = _prepare_password_for_bcrypt(password)
    # Генерируем соль и хешируем пароль
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(prepared_password, salt)
    # Возвращаем как строку
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создает JWT токен"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Проверяет JWT токен"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """Получает текущего пользователя из токена"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Получаем пользователя из Firebase
    user_doc = db.collection(USERS_COLLECTION).document(user_id).get()
    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_data = user_doc.to_dict()
    return UserResponse(
        id=user_doc.id,
        phone=user_data.get("phone"),
        name=user_data.get("name"),
        is_admin=user_data.get("is_admin", False)
    )


async def get_current_admin_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """Проверяет, что пользователь является администратором"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user

