from fastapi import APIRouter, Depends, HTTPException, status
from app.api.dependencies.deps import get_current_user_from_cookie
from app.services.session_service import SessionService
from app.core.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/session", tags=["Sessions"])

async def get_session_service(db: AsyncIOMotorDatabase = Depends(get_database)):
    return SessionService(db)

@router.get("/active")
async def get_active_sessions(current_user: dict = Depends(get_current_user_from_cookie), 
                                service: SessionService = Depends(get_session_service)):
    sessions = await service.get_active_sessions(current_user["id_user"])
    result = []
    for s in sessions:
        result.append({"ip_address": s.get("ip_address"),
                        "user_agent": s.get("user_agent"),
                        "created_at": s.get("created_at"),
                        "last_activity": s.get("last_activity"),
                        "is_active": s.get("is_active")})
    return {"active_sessions": result,
            "total": len(result),
            "max_allowed": 3}
    
@router.post("/logout_all/{user_id}")
async def invalidate_all_user_sessions(user_id: str, current_user: dict = Depends(get_current_user_from_cookie),
                                        service: SessionService = Depends(get_session_service)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No tienes los permisos suficientes")
    try:
        count = await service.invalidate_all_sessions(user_id)
        return {"message": f"Se cerraron {count} sesiones en todos los dispositivos"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se logró cerrar las sesiones del usuario. {str(e)}")