from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import database, get_database
from app.api.routes import film, film_metrics, admin, payment, user, session, ecdh
from app.services.session_service import SessionService
from app.middleware.session_middleware import SessionInfoMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    db = await get_database()
    session_service = SessionService(db)
    await session_service.create_index()
    
    yield
    
    await database.disconnect()
    
app = FastAPI(
    title="Vault Art API",
    description="Sistema de películas para artistas locales",
    version="1.0.0",
    lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins = settings.CORS_ORIGIN,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

app.add_middleware(SessionInfoMiddleware)

app.include_router(film.router, tags=["Film"])
app.include_router(film_metrics.router, tags=["Film metrics"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(payment.router, tags=["Payment"])
app.include_router(user.router, tags=["User"])
app.include_router(session.router, tags=["Sessions"])
app.include_router(ecdh.router, tags=["ECDH"])

@app.get("/")
async def root():
    return {
        "message": "Bienvenido a la API de VaultArt",
        "version": "1.0.0",
        "docs": "/docs"
    }
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)