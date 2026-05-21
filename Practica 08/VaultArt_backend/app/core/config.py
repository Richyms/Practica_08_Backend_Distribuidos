from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    MONGODB_URI: str
    MONGODB_NAME: str
    SESSION_SECRET: str
    MAX_SESSIONS_PER_USER: int
    KEY_ENCRYPTION_KEY: str
    R2_BUCKET: str
    R2_ACCESS_KEY: str
    R2_SECRET_KEY: str
    R2_ENDPOINT: str
    ENVIROMENT: str
    
    @property
    def MONGODB_URL(self) -> str:
        return self.MONGODB_URI
    
    @property
    def CORS_ORIGIN(self) -> List[str]:
        if self.ENVIROMENT == "production":
            return [""]
        else:
            return ["http://localhost:3000", "http://127.0.0.1", "http://localhost:5173"]
        
    class Config:
        env_file = ".env"
        case_sensitive = False
        
settings = Settings()