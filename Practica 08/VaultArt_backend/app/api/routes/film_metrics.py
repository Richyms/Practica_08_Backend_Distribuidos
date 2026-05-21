from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.schemas.film_metrics_schema import FilmMetricsResponse, FilmRate
from app.services.film_metrics_service import FilmMetricsService
from app.api.dependencies.deps import get_current_user_from_cookie

router = APIRouter(prefix="/film_metrics", tags=["Film metrics"])

def get_film_metric_service(db: AsyncIOMotorDatabase = Depends(get_database)):
    return FilmMetricsService(db)

@router.get("/", response_model=FilmMetricsResponse)
async def get_film_metrics(film_id: str, service: FilmMetricsService = Depends(get_film_metric_service), 
                            current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        result = await service.get_film_metrics(film_id)
        return FilmMetricsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se pudieron obtener las métricas correspondientes. {str(e)}")
    
@router.post("/view/{film_id}")
async def view_film(film_id: str, service: FilmMetricsService = Depends(get_film_metric_service),
                    current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        await service.increment_views(film_id, current_user["id_user"])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se pudo realizar la acción correspondiente. {str(e)}")
    
@router.post("/like/{film_id}")
async def like_film(film_id: str, service: FilmMetricsService = Depends(get_film_metric_service),
                    current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        await service.increment_likes(film_id, current_user["id_user"])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se pudo realizar la acción correspondiente. {str(e)}")
    
@router.post("/rating/{film_id}")
async def rating_film(film_id: str, rate: FilmRate, service: FilmMetricsService = Depends(get_film_metric_service),
                    current_user: dict = Depends(get_current_user_from_cookie)):
    try:
        await service.increment_rating(film_id, rate.rating, current_user["id_user"])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se ha podido realizar la acción correspondiente. {str(e)}")