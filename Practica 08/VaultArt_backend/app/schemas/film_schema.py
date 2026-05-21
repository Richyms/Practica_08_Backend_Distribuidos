from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class FilmBase(BaseModel):
    title: str
    director: str
    artists: List[str]
    length: int
    synopsis: str
    genre: str
    type: str = Field(..., pattern="^(Película|Serie)$")
    release_year: int
    
class FilmCreate(FilmBase):
    pass

class SecurePrivateKey(BaseModel):
    public_key_client: str
    data: dict
    salt: str

class FilmInDB(FilmBase):
    id_film: str = Field(alias="_id")
    artist_id: str
    content_key: str
    chunks: int
    chunk_size: int = 2*1024*1024
    created_at: datetime
    poster: str
    is_active: bool = True

class FilmUpdate(BaseModel):
    title: Optional[str] = None
    director: Optional[str] = None
    artists: Optional[List[str]] = None
    synopsis: Optional[str] = None
    genre: Optional[str] = None
    type: Optional[str] = None
    release_year: Optional[int] = None
    
class FilmUploadResponse(BaseModel):
    title: str
    director: str
    message: str
    
class FilmGetResponse(BaseModel):
    id_film: str = Field(alias="_id")
    title: str
    director: str
    release_year: int
    length: str
    genre: str
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
    
class FilmUpdateResponse(BaseModel):
    title: str
    director: str
    message: str
    
class FilmDeleteResponse(BaseModel):
    title: str
    director: str
    message: str

    class Config:
        from_attributes = True
        populate_by_name = True