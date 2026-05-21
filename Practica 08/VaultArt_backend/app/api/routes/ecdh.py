from fastapi import APIRouter, Depends
from app.services.ecdh_service import ECDHservice

router = APIRouter(prefix="/ecdh", tags=["ECDH"])
ecdh_instance = ECDHservice()

async def get_ecdh_service() -> ECDHservice:
    return ecdh_instance

@router.get("/public_key")
async def get_public_key(ecdh: ECDHservice = Depends(get_ecdh_service)):
    return {"public_key": ecdh.get_public_key()}