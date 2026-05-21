from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr
    rol: str = Field(default="user", pattern="^(admin|user|artist)$")
    
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
class SecureUserRegister(BaseModel):
    public_key_client: str
    data: dict
    salt: str
    
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)
    rol: Optional[str] = Field(default=None, pattern="^(admin|user|artist)$")
    user_public_key: Optional[str] = None
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    
class UserInDB(UserBase):
    id_user: str = Field(alias="_id")
    user_public_key: Optional[str] = None
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    password: str
    viewed_films: List[str] = []
    liked_films: List[str] = []
    rated_films: List[str] = []
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
class SecureUserLogin(BaseModel):
    public_key_client: str
    data: dict
    salt: str
    
class UserUpdateSubscription(BaseModel):
    subscription_start_date: datetime
    subscription_end_date: datetime
    
class UserRegisterResponse(BaseModel):
    name: str
    email: EmailStr
    message: str    
    
class UserLoginResponse(BaseModel):
    token: str
    token_type: str = "session"
    
class UserProfileResponse(BaseModel):
    id_user : str = Field(alias="_id")
    name: str
    email: EmailStr
    rol: str
    subscription_active: bool
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True