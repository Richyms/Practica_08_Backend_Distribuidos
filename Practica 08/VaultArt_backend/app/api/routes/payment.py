from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.schemas.payment_schema import SubscriptionResponse, SecureSubscription, SubscriptionCreate, PaymentCreate
from app.services.payment_service import PaymentService
from app.services.ecdh_service import ECDHservice
from app.api.routes.ecdh import ecdh_instance
from app.api.dependencies.deps import get_current_user_from_cookie
from datetime import datetime
import base64

router = APIRouter(prefix="/payment", tags=["Payment"])

async def get_ecdh_service() -> ECDHservice:
    return ecdh_instance

def get_payment_service(db: AsyncIOMotorDatabase = Depends(get_database)):
    return PaymentService(db)

@router.post("/subscription", response_model=SubscriptionResponse)
async def user_subscribe(data: SecureSubscription, ecdh: ECDHservice = Depends(get_ecdh_service),
                        current_user: dict = Depends(get_current_user_from_cookie),
                        service: PaymentService = Depends(get_payment_service)):
    try:
        subscription = await service.get_status_subscription(current_user["id_user"])
        if subscription["is_active"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail=f"Ya cuentas con una suscripción activa hasta {subscription['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        salt = base64.b64decode(data.salt)
        secret = ecdh.derive_secret(data.public_key_client, salt)
        decrypt_data = ecdh.decrypt_data(data.data, secret)
        payment_method_object = PaymentCreate(**decrypt_data["payment_method"])
        payment_data = SubscriptionCreate(payment_method=payment_method_object, accept_terms=decrypt_data["accept_terms"])
        payment, expires_at = await service.process_subscription(current_user["id_user"], payment_data.payment_method.model_dump())
        if not payment:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No se pudo procesar el pago")
        
        return SubscriptionResponse(is_active=True, end_date=expires_at, 
                                    message=f"Suscripción activada correctamente. Válida hasta: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ha ocurrido un error al realizar la suscripción. {str(e)}")
    
@router.get("/status", response_model=SubscriptionResponse)
async def user_subscription_status(service: PaymentService = Depends(get_payment_service), current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        subscription = await service.get_status_subscription(current_user["id_user"])
        if not subscription["is_active"]:
            return SubscriptionResponse(is_active=False, message="No tienes una suscripción activa")
        return SubscriptionResponse(is_active=True, end_date=subscription["expires_at"], 
                                    message=f"Tu suscripción se encuentra activa hasta: {subscription["expires_at"].strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocurrio un error al verificar la subscripción. {str(e)}")
    
@router.get("/history")
async def user_history_subscription(limit: int = 10, service: PaymentService = Depends(get_payment_service), 
                                    current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        history = await service.payment_history(current_user["id_user"], limit)
        for payment in history:
            payment["created_at"] = payment["created_at"].strftime('%Y-%m-%d %H:%M:%S')
            payment["expires_at"] = payment["expires_at"].strftime('%Y-%m-%d %H:%M:%S')
        return history
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ha ocurrido un error al obtener el historial. {str(e)}")
    
@router.post("/cancel")
async def cancel_subscription(service: PaymentService = Depends(get_payment_service), current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        subscription = await service.get_status_subscription(current_user["id_user"])
        if not subscription["is_active"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No tienes una suscripción activa para cancelar")
        cancel = await service.cancel_subscription(current_user["id_user"])
        if not cancel:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se pudo cancelar la suscripción.")
        return {"message": "La suscripción se canceló exitosamente", "cancelled_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se pudo cancelar la suscripción.")