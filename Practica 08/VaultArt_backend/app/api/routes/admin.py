from fastapi import APIRouter, HTTPException, Depends, status
from app.services.admin_service import AdminService
from app.services.encryption_service import EncryptionService
from app.services.signature_service import SignatureService
from app.services.ecdh_service import ECDHservice
from app.api.routes.ecdh import ecdh_instance
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.admin_schema import GetUsersResponse, ChangeRolResponse, DeleteUserResponse, UserDetailsResponse, FilmGetResponse, FilmByIdResponse, KeyRequest
from typing import List
from app.core.database import get_database
from app.api.dependencies.deps import get_current_user_from_cookie
import secrets
import base64

router = APIRouter(prefix="/admin", tags=["Admin"])

async def get_ecdh_service() -> ECDHservice:
    return ecdh_instance

async def get_encryption_service() -> EncryptionService:
    return EncryptionService()

async def get_signature_service() -> SignatureService:
    return SignatureService()

async def get_admin_service(db: AsyncIOMotorDatabase = Depends(get_database),
                            encryption_service: EncryptionService = Depends(get_encryption_service),
                            signature_service: SignatureService = Depends(get_signature_service)):
    return AdminService(db, encryption_service, signature_service)

@router.get("/users", response_model=List[GetUsersResponse])
async def get_users(service: AdminService = Depends(get_admin_service), current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        result = await service.get_users()
        return [GetUsersResponse(**user) for user in result]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: Ocurrió un error al realizar la acción. {str(e)}")
    
@router.get("/artists", response_model=List[GetUsersResponse])
async def get_artists(service: AdminService = Depends(get_admin_service), current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        result = await service.get_artists()
        return [GetUsersResponse(**artist) for artist in result]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: Ocurrió un error al realizar la acción. {str(e)}")
    
@router.get("/user/{user_id}", response_model=UserDetailsResponse)
async def get_user_details(user_id: str, service: AdminService = Depends(get_admin_service),
                        current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        user = await service.get_user_details(user_id)
        return UserDetailsResponse(**user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocurrio un error al obtener los detalles del usuario. {str(e)}")

@router.post("/rol/{user_id}", response_model=ChangeRolResponse)
async def change_rol(user_id: str, new_rol: str, current_user: dict = Depends(get_current_user_from_cookie),
                        service: AdminService = Depends(get_admin_service)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        result = await service.change_rol(user_id, new_rol)
        return ChangeRolResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: Ocurrió un error al realizar la acción. {str(e)}")
    
@router.post("/delete/{user_id}", response_model=DeleteUserResponse)
async def delete_user(user_id: str, service: AdminService = Depends(get_admin_service),
                        current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        result = await service.delete_user(user_id)
        return DeleteUserResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: Ocurrió un error al realizar la acción. {str(e)}")
    
@router.get("/films", response_model=List[FilmGetResponse])    
async def get_all_films(service: AdminService = Depends(get_admin_service), 
                    current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        films = await service.get_films()
        for film in films:
            minutes = film["length"]//60
            secodns = film["length"]%60
            film["length"] = f"{minutes}:{secodns}"
        return [FilmGetResponse(**film) for film in films]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocurrio un error al obtener las películas. {str(e)}")
    
@router.get("/film/{film_id}", response_model=FilmByIdResponse)
async def get_film(film_id: str, service: AdminService = Depends(get_admin_service), current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        film = await service.film_details(film_id)
        if not film:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"La película no existe")
        minutes = film["length"]//60
        secodns = film["length"]%60
        film["length"] = f"{minutes}:{secodns}"
        return FilmByIdResponse(**film)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocurrió un error al realizar la acción. {str(e)}")
    
@router.post("/film/toggle/{film_id}")
async def toggle_film(film_id: str, service: AdminService = Depends(get_admin_service),
                    current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        return await service.toggle_film(film_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocurrio un error al realizar la acción. {str(e)}")    
    
@router.post("/key_generation/{user_id}")
async def key_generation(user_id: str, request: KeyRequest, service: AdminService = Depends(get_admin_service),
                        current_user: dict = Depends(get_current_user_from_cookie), ecdh: ECDHservice = Depends(get_ecdh_service)):
    if current_user["rol"] not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No cuentas con los permisos suficientes")
    try:
        salt = secrets.token_bytes(16)
        secret = ecdh.derive_secret(request.public_key_client, salt)   
        private_key_b64 = await service.user_key_generation(user_id)
        encrypt_response = ecdh.encrypt_data({"private_key": private_key_b64}, secret)
        return {"public_key_server": ecdh.get_public_key(), "salt": base64.b64encode(salt).decode(), "data": encrypt_response}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: Ocurrió un error al generar las llaves. {str(e)}")