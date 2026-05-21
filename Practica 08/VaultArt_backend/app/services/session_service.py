from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from typing import Optional, Tuple
from app.schemas.session_schema import UserSession
from app.core.config import settings
from hashlib import sha3_256
import hmac

class SessionService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.session_secret = settings.SESSION_SECRET
        self.max_sessions_per_user = settings.MAX_SESSIONS_PER_USER
    
    async def create_index(self):
        await self.db.sessions.create_index("session_hash", unique=True)
        await self.db.sessions.create_index("user_id")
        await self.db.sessions.create_index([("user_id", 1), ("is_active", 1)])
        await self.db.sessions.create_index("expires_at", expireAfterSeconds=0)
        await self.db.sessions.create_index("last_activity")
        
    def shash_session_id(self, session_id: str) -> str:
        return hmac.new(self.session_secret.encode(), session_id.encode(), sha3_256).hexdigest()
    
    async def create_session(self, user_id: str, ip_address: str, user_agent: str, ttl: int = 7) -> Tuple[str, UserSession]:
        await self.session_limit(user_id)
        
        session = UserSession.create(user_id=user_id, ip_address=ip_address, user_agent=user_agent, ttl=ttl)
        session_dict = session.model_dump()
        session_dict["_id"] = session_dict.pop("session_id")
        await self.db.sessions.insert_one(session_dict)
        
        return session.session_id, session
    
    async def validate_session(self, session_id: str, ip_address: str, user_agent: str) -> Optional[dict]:
        session_hash = self.shash_session_id(session_id)
        session = await self.db.sessions.find_one({"session_hash": session_hash, "is_active": True, "expires_at": {"$gt": datetime.now(timezone.utc)}})
        if not session:
            return None
        
        if session["ip_address"] != ip_address:
            await self.db.sessions.update_one({"_id": session["_id"]}, {"$addToSet": {"previous_ips": ip_address}})
            
        if session["user_agent"] != user_agent:
            await self.db.sessions.update_one({"_id": session["_id"]}, {"$set": {"user_agent_changed": True}})
            
        await self.db.sessions.update_one({"_id": session["_id"]}, {"$set": {"last_activity": datetime.now(timezone.utc)}})
        
        return session
    
    async def invalidate_session(self, session_id: str) -> bool:
        session_hash = self.shash_session_id(session_id)
        result = await self.db.sessions.update_one({"session_hash": session_hash}, {"$set": {"is_active": False}})
        return result.modified_count>0
    
    async def invalidate_all_sessions(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        close_sessions = {"user_id": user_id, "is_active": True}
        if except_session_id:
            except_hash = self.shash_session_id(except_session_id)
            close_sessions["session_hash"] = {"$ne": except_hash}
        result = await self.db.sessions.update_many(close_sessions, {"$set": {"is_active": False}})
        return result.modified_count
    
    async def invalidate_session_by_id(self, session_uuid: str) -> bool:
        result = await self.db.sessions.update_one({"_id": session_uuid, "is_active": True}, {"$set": {"is_active": False}})
        return result.modified_count>0
    
    async def get_active_sessions(self, user_id: str) -> list:
        result = self.db.sessions.find({"user_id": user_id, "is_active": True, "expires_at": {"$gt": datetime.now(timezone.utc)}}).sort("last_activity", -1)
        return await result.to_list(length=100)
    
    async def session_limit(self, user_id: str) -> None:
        active_sessions = await self.get_active_sessions(user_id)
        if len(active_sessions) >= self.max_sessions_per_user:
            oldest_session = active_sessions[-1]
            return await self.invalidate_session_by_id(oldest_session["_id"])