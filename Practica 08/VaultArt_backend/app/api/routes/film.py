from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.api.dependencies.deps import get_current_user_from_cookie, require_active_subscription
from app.services.film_service import FilmService
from app.services.encryption_service import EncryptionService
from app.services.signature_service import SignatureService
from app.services.ecdh_service import ECDHservice
from app.api.routes.ecdh import ecdh_instance
from app.services.R2_service import R2Service
from app.services.film_metrics_service import FilmMetricsService
from app.schemas.film_schema import FilmCreate, FilmUpdate, FilmUploadResponse, FilmGetResponse, FilmByIdResponse, FilmUpdateResponse, FilmDeleteResponse, SecurePrivateKey
from moviepy import VideoFileClip
import tempfile
import os
import asyncio
import base64
import json

router = APIRouter(prefix="/film", tags=["Films"])

async def get_ecdh_service() -> ECDHservice:
    return ecdh_instance

async def get_encryption_service() -> EncryptionService:
    return EncryptionService()

async def get_drive_service() -> R2Service:
    return R2Service()

async def get_signature_service() -> SignatureService:
    return SignatureService()

async def get_metrics_service(db: AsyncIOMotorDatabase = Depends(get_database)):
    return FilmMetricsService(db)
    
async def get_film_service(db: AsyncIOMotorDatabase = Depends(get_database),
                           encryption_service: EncryptionService = Depends(get_encryption_service),
                           r2_service: R2Service = Depends(get_drive_service),
                           signature_service: SignatureService = Depends(get_signature_service)) -> FilmService:
    return FilmService(db, encryption_service, r2_service, signature_service)

@router.get("/", response_model=List[FilmGetResponse])
async def get_all_films(skip: int = 0, limit: int = 20, service: FilmService = Depends(get_film_service), 
                        current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        result = await service.get_films(skip, limit)
        for film in result:
            minutes = film["length"]//60
            secodns = film["length"]%60
            film["length"] = f"{minutes}:{secodns}"
        return [FilmGetResponse(**film) for film in result]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el contenido")
    
@router.get("/genre")
async def get_genres(service: FilmService = Depends(get_film_service), current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        return await service.get_genres()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se lograron obtener los géneros disponibles. {str(e)}")
    
@router.get("/type", response_model=Optional[List[FilmGetResponse]])
async def get_films_type(type_film: str, service: FilmService = Depends(get_film_service), current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        result = await service.get_film_type(type_film)
        for film in result:
            minutes = film["length"]//60
            secodns = film["length"]%60
            film["length"] = f"{minutes}:{secodns}"
        return [FilmGetResponse(**film) for film in result]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se lograron obtener las {type_film} disponibles. {str(e)}")
    
@router.get("/{film_id}", response_model=FilmByIdResponse)
async def get_film_details(film_id: str, service: FilmService = Depends(get_film_service), current_user: dict = Depends(get_current_user_from_cookie)):
    try:    
        film = await service.film_details(film_id)
        if not film:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Película no encontrada")
        minutes = film["length"]//60
        secodns = film["length"]%60
        film["length"] = f"{minutes}:{secodns}"
        return FilmByIdResponse(**film)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")

@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=FilmUploadResponse)
async def upload_film(data_client: str = Form(...),
                    title: str = Form(...),
                    director: str = Form(...),
                    artists: List[str] = Form(...),
                    synopsis: str = Form(...),
                    genre: str = Form(...),
                    type: str = Form(...),
                    release_year: Optional[int] = Form(None), 
                    video: UploadFile = File(...), 
                    poster: UploadFile = File(...),
                    current_user: dict = Depends(get_current_user_from_cookie), film_service: FilmService = Depends(get_film_service),
                    ecdh: ECDHservice = Depends(get_ecdh_service)):
    if current_user["rol"] not in ["admin", "artist"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No cuentas con los permisos suficientes")
    
    temp_path = None
    temp_poster = None
        
    try:
        data_dict = json.loads(data_client)
        data = SecurePrivateKey(**data_dict)
        salt = base64.b64decode(data.salt)
        secret = ecdh.derive_secret(data.public_key_client, salt)
        decrypt_data = ecdh.decrypt_data(data.data, secret)
        private_key_b64 = decrypt_data["private_key"]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            content = await video.read()
            temp_file.write(content)
            temp_path = temp_file.name
            
            with VideoFileClip(temp_path) as film:
                length = int(film.duration)
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as poster_file:
                poster_content = await poster.read()
                poster_file.write(poster_content)
                temp_poster = poster_file.name

            data_film = FilmCreate(title=title,director=director, artists=artists, length=length, synopsis=synopsis, 
                        genre=genre, type=type, release_year=release_year)
            
            result = await film_service.upload_file(film_data=data_film, artist_id=current_user["id_user"], file_path=temp_path, 
                                                    poster_path=temp_poster, private_key_b64=private_key_b64)
            return FilmUploadResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        if temp_poster and os.path.exists(temp_poster):
            os.unlink(temp_poster)
            
@router.get("/stream/{film_id}")
async def stream_film(film_id: str, start_chunk: int = 1, service: FilmService = Depends(get_film_service),
                    metrics: FilmMetricsService = Depends(get_metrics_service), current_user: dict = Depends(require_active_subscription)):
    asyncio.create_task(metrics.increment_views(film_id, current_user["id_user"]))
    return StreamingResponse(service.stream_file(film_id, start_chunk), media_type="video/mp4")

@router.post("/update/{film_id}", response_model=FilmUpdateResponse)
async def update_film(film_id: str, update: FilmUpdate, data: SecurePrivateKey, service: FilmService = Depends(get_film_service),
                    current_user: dict = Depends(get_current_user_from_cookie), ecdh: ECDHservice = Depends(get_ecdh_service)):
    try:
        salt = base64.b64decode(data.salt)
        secret = ecdh.derive_secret(data.public_key_client, salt)
        decrypt_data = ecdh.decrypt_data(data.data, secret)
        private_key_b64 = decrypt_data["private_key"]
        
        result = await service.update_file(film_id, update, private_key_b64)
        return FilmUpdateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)} No logro actualizar los datos correctamente.")
    
@router.delete("/delete/{film_id}", response_model=FilmDeleteResponse)
async def delete_film(film_id: str, service: FilmService = Depends(get_film_service), current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user["rol"] not in ["admin", "artist"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        result = await service.delete_file(film_id)
        return FilmDeleteResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)}. No se pudo eliminar la película.")
    
@router.get("/poster/{film_id}")
async def get_poster(film_id: str, service: FilmService = Depends(get_film_service), current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        result = await service.get_poster_file(film_id)
        return Response(content=result, media_type="image/jpg")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se logró obtener el poster de la película.")