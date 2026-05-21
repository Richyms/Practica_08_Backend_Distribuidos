from pydantic import BaseModel, Field
from typing import Optional, List

class KeyRequest(BaseModel):
    public_key_client: str

class GetUsersResponse(BaseModel):
    user_id: str = Field(alias="_id")
    name: str
    email: str
    rol: str

class ChangeRolResponse(BaseModel):
    user_id: str
    name: str
    rol: str
    message: str
    
class DeleteUserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    message: str
    
class UserDetailsResponse(BaseModel):
    user_id: str = Field(alias="_id")
    name: str
    email: str
    rol: str
    public_key: Optional[str] = None
    
class FilmGetResponse(BaseModel):
    id_film: str = Field(alias="_id")
    title: str
    director: str
    release_year: int
    length: str
    genre: str
    is_active: bool
    views: int
    likes: int
    rating: float
    total_ratings: int
    
class FilmByIdResponse(BaseModel):
    id_film: str = Field(alias="_id")
    title: str
    director: str
    artists: List[str]
    release_year: int
    length: str
    genre: str
    synopsis: str
    type: str
    verify: bool
    views: int
    likes: int
    rating: float
    total_ratings: int
    
    class Config:
        from_attributes = True
        populate_by_name = True