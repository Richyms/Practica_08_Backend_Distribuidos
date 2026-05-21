from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from typing import List
from hashlib import sha3_256
import uuid
import hmac

class UserSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_hash: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    previous_ips: List[str] = []
    
    @classmethod
    def hash_session_id(cls, session_id: str) -> str:
        key = settings.SESSION_SECRET
        return hmac.new(key.encode(), session_id.encode(), sha3_256).hexdigest()
    
    @classmethod
    def create(cls, user_id: str, ip_address: str, user_agent: str, ttl: int = 7):
        session_id = str(uuid.uuid4())
        session_hash = cls.hash_session_id(session_id)
        
        return cls(
            session_id = session_id,
            session_hash = session_hash,
            user_id = user_id,
            ip_address = ip_address,
            user_agent = user_agent,
            expires_at = datetime.now(timezone.utc) + timedelta(days=ttl)
        )
    
    class Config:
        from_attributes = True