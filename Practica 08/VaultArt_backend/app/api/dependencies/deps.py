from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.services.session_service import SessionService
from app.services.user_service import UserService
from typing import Optional

class SessionAuth:
    @classmethod
    async def from_header(
        cls, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
        db: AsyncIOMotorDatabase = Depends(get_database), request: Request = None
    ) -> dict:
        if not credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")
        if credentials.scheme != "Session":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esquema de autenticación inválido")
        return await cls.dvalidate_session(credentials.credentials, db, request)
    
    @classmethod
    async def from_cookie(cls, request: Request, 
                          session_id: Optional[str] = Cookie(None, alias="session_token"),
                          db: AsyncIOMotorDatabase = Depends(get_database)) -> dict:
        if not session_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")
        return await cls.dvalidate_session(session_id, db, request)
    
    @classmethod
    async def dvalidate_session(cls, session_id: str, db: AsyncIOMotorDatabase, request: Optional[Request] = None) -> dict:
        session_service = SessionService(db)
        
        if request:
            ip_address = request.client.host 
            user_agent = request.headers.get("user-agent", "")
        else:
            ip_address = "0.0.0.0"
            user_agent = ""
        
        session = await session_service.validate_session(session_id, ip_address, user_agent)
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o expirada", headers={"WWW-Authenticate": "Session"})
        
        user_service = UserService(db)
        user = await user_service.get_user_profile(session["user_id"])
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
        
        return user.model_dump()
    
async def get_current_user_from_header(user: dict = Depends(SessionAuth.from_header)) -> dict:
    return user

async def get_current_user_from_cookie(user: dict = Depends(SessionAuth.from_cookie)) -> dict:
    return user

async def require_active_subscription(current_user: dict = Depends(get_current_user_from_cookie)) -> dict:
    if not current_user.get("subscription_active", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Se requiere una suscripción activa para ver este contenido")
    return current_user