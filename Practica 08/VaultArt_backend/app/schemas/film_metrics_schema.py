from pydantic import BaseModel, Field, field_validator

class FilmMetricsBase(BaseModel):
    id_film: str
    views: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    rating: float = Field(default=0, ge=0, le=5)
    total_ratings: int = Field(default=0, ge=0)
    
class FilmMetricsInDB(FilmMetricsBase):
    id_metrics: str = Field(alias="_id")
    
class FilmRate(BaseModel):
    rating: float = Field(default=0, ge=0, le=5)
    
class FilmMetricsResponse(FilmMetricsInDB):
    views: int
    likes: int
    rating: float
    total_ratings: int

    class Config:
        from_attributes = True