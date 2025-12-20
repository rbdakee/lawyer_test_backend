from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import os


SECRET_LOCAL_TOKEN = os.getenv("SECRET_LOCAL_TOKEN")


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки SECRET_LOCAL_TOKEN"""
    
    async def dispatch(self, request: Request, call_next):
        # Пропускаем OPTIONS запросы (preflight для CORS)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Пропускаем публичные endpoints
        public_paths = ["/", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Публичные API endpoints (не требуют токена)
        public_api_paths = [
            "/api/translations",
            "/api/questions",
            "/api/legislation-sections",
            "/api/auth/register",
            "/api/auth/login",
        ]
        
        # Проверяем, начинается ли путь с публичного пути
        for public_path in public_api_paths:
            if request.url.path.startswith(public_path):
                return await call_next(request)
        
        # Если есть Authorization заголовок (JWT токен), пропускаем проверку X-API-Token
        # JWT токены обрабатываются через get_current_user dependency
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return await call_next(request)
        
        # Проверяем токен в заголовке X-API-Token (для прямых API запросов)
        token = request.headers.get("X-API-Token")
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен API не предоставлен"
            )
        
        if token != SECRET_LOCAL_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен API"
            )
        
        return await call_next(request)

