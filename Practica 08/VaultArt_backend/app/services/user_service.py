from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from bson import ObjectId
from datetime import datetime
from app.schemas.user_schema import UserCreate, UserLogin
from app.schemas.user_schema import UserRegisterResponse, UserLoginResponse, UserProfileResponse
from app.services.session_service import SessionService
import bcrypt

class UserService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.session_service = SessionService(db)
    
    async def email_exists(self, email: str) -> bool:
        result = await self.db.user.find_one({"email": email, }, {"_id": 1})
        return result is not None
    
    async def create_user(self, user_data: UserCreate) -> UserRegisterResponse:
        try:
            user_dict = user_data.model_dump()
            user_dict["password"] = (bcrypt.hashpw(user_dict["password"].encode('utf-8'), bcrypt.gensalt(rounds=12))).decode('utf-8')
            result = await self.db.user.insert_one(user_dict)
            created_user = await self.db.user.find_one({"_id": result.inserted_id}, {"name": 1, "email": 1})
            if not created_user:
                raise ValueError("Error al crear el usuario")
            created_user["message"] = f"Usuario {created_user['name']} con correo electrónico {created_user['email']} creado con éxito"
            return UserRegisterResponse(**created_user)
        except Exception as e:
            raise ValueError("No se pudo crear el usuario")
    
    async def login_user(self, user_data: UserLogin, ip_address: str, user_agent: str) -> Optional[UserLoginResponse]:
        try:
            user = await self.db.user.find_one({"email": user_data.email}, {"_id": 1, "password": 1})
            if not user:
                return None
            if not bcrypt.checkpw(user_data.password.encode('utf-8'), user["password"].encode('utf-8')):
                return None
            session_id, session = await self.session_service.create_session(
                user_id=str(user["_id"]),
                ip_address=ip_address,
                user_agent=user_agent,
                ttl=7
            )
            return UserLoginResponse(token = session_id)
        except Exception as e:
            raise ValueError("No se pudo iniciar sesión")
        
    async def get_user_profile(self, user_id: str) -> Optional[UserProfileResponse]:
        user = await self.db.user.find_one({"_id": ObjectId(user_id)}, {"_id": 1, "name": 1, "email": 1, "rol": 1, "subscription_start_date": 1, "subscription_active": 1,
                                                                            "subscription_end_date": 1})
        if not user:
            return None
        
        is_active = user.get("subscription_active", False)
        expires_at = user.get("subscription_end_date", None) 
        if is_active and expires_at and expires_at < datetime.now():
            is_active = False
            await self.db.user.update_one({"_id": ObjectId(user_id)}, {"$set": {"subscription_active": False}, 
                                                                        "$unset": {"subscription_start_date": "", "subscription_end_date": ""}})
        
        user["_id"] = str(user["_id"])
        user["subscription_active"] = is_active
        if is_active:
            start_date = user.get("subscription_start_date")
            end_date = user.get("subscription_end_date")
            user["subscription_start_date"] = start_date.strftime('%Y-%m-%d %H:%M:%S')
            user["subscription_end_date"] = end_date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            user["subscription_start_date"] = None
            user["subscription_end_date"] = None
        return UserProfileResponse(**user)