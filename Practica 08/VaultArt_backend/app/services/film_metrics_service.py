from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

class FilmMetricsService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
    async def create_film_metrics(self, film_id: str) -> None:
        await self.db.film_metrics.insert_one({
            "film_id": film_id,
            "views": 0,
            "likes": 0,
            "rating": 0,
            "total_ratings": 0
        })
    
    async def get_film_metrics(self, film_id: str) -> dict:
        return await self.db.film_metrics.find_one({"film_id": film_id}, {"_id": 0, "film_id": 0})
    
    async def increment_views(self, film_id: str, user_id: str) -> None:
        film = await self.db.film.find_one({"_id": ObjectId(film_id)})
        if not film:
            raise ValueError("La película no existe")
        user = await self.db.user.find_one({"_id": ObjectId(user_id), "viewed_films": film_id})
        if user:
            return
        await self.db.user.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"viewed_films": film_id}})
        await self.db.film_metrics.update_one({"film_id": film_id}, {"$inc": {"views": 1}})
    
    async def increment_likes(self, film_id: str, user_id: str) -> None:
        film = await self.db.film.find_one({"_id": ObjectId(film_id)})
        if not film:
            raise ValueError("La película no existe")
        user = await self.db.user.find_one({"_id": ObjectId(user_id), "liked_films": film_id})
        if user:
            return
        await self.db.user.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"liked_films": film_id}})
        await self.db.film_metrics.update_one({"film_id": film_id}, {"$inc": {"likes": 1}})
    
    async def increment_rating(self, film_id, rating: float, user_id: str) -> None:
        film = await self.db.film.find_one({"_id": ObjectId(film_id)})
        if not film:
            raise ValueError("La película no existe")
        user = await self.db.user.find_one({"_id": ObjectId(user_id), "rated_films": film_id})
        if user:
            return
        await self.db.user.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"rated_films": film_id}})
        metrics = await self.db.film_metrics.find_one({"film_id": film_id})
        old_rating = metrics.get("rating", 0.0) if metrics else 0
        old_total_ratings = metrics.get("total_ratings", 0) if metrics else 0
        
        new_total_ratings = old_total_ratings + 1
        new_rating = (old_rating*old_total_ratings + rating)/new_total_ratings
        
        await self.db.film_metrics.update_one({"film_id": film_id}, {"$inc": {"total_ratings": 1}, 
                                                                    "$set": {"rating": round(new_rating, 2)}}, upsert=True)
        
        
        