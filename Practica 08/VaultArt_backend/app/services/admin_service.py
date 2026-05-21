from app.services.film_metrics_service import FilmMetricsService
from app.services.encryption_service import EncryptionService
from app.services.signature_service import SignatureService
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId

class AdminService:
    def __init__(self, db: AsyncIOMotorDatabase, encryption_service: EncryptionService, signature_service: SignatureService):
        self.db = db
        self.encryption = encryption_service
        self.signature = signature_service
        self.metrics = FilmMetricsService(db)
        
    async def get_users(self) -> List[dict]:
        result = await self.db.user.find({}, {"_id": 1, "name": 1, "email": 1, "rol": 1}).to_list()
        for user in result:
            user["_id"] = str(user["_id"])
        return result
    
    async def get_artists(self) -> List[dict]:
        result = await self.db.user.find({"rol": "artist"}, {"_id": 1, "name": 1, "email": 1, "rol": 1}).to_list()
        for artist in result:
            artist["_id"] = str(artist["_id"])
        return result
    
    async def get_user_details(self, user_id: str) -> Optional[dict]:
        user = await self.db.user.find_one({"_id": ObjectId(user_id)}, {"_id": 1, "name": 1, "email": 1, "rol": 1, "public_key": 1})
        if not user:
            raise ValueError("El usuario no existe")
        user["_id"] = str(user["_id"])
        return user
    
    async def change_rol(self, user_id: str, new_rol: str) -> dict:
        user = await self.db.user.find_one({"_id": ObjectId(user_id)}, {"_id": 1, "name": 1, "rol": 1})
        if not user:
            raise ValueError("El usuario no existe")
        await self.db.user.update_one({"_id": ObjectId(user_id)}, {"$set": {"rol": new_rol}})
        return {"user_id": user_id, "name": user["name"], "rol": new_rol, "message": "Se ha asignado un nuevo rol correctamente."}
    
    async def delete_user(self, user_id: str) -> dict:
        user = await self.db.user.find_one({"_id": ObjectId(user_id)}, {"_id": 1, "name": 1, "email": 1})
        if not user:
            raise ValueError("El usuario no existe")
        await self.db.sessions.delete_many({"user_id": user_id})
        await self.db.user.delete_one({"_id": ObjectId(user_id)})
        return {"user_id": user_id, "name": user["name"], "email": user["email"], "message": "El usuario se ha eliminado correctamente."}
    
    async def get_films(self) -> List[dict]:
        result = self.db.film.find({}, {"_id": 1, "title": 1, "director": 1, "release_year": 1,
                                                            "length": 1, "genre": 1, "is_active": 1}).sort("release_year", -1)
        films = await result.to_list()
        for film in films:
            film["_id"] = str(film["_id"])
            metrics = await self.metrics.get_film_metrics(film["_id"])
            film.update(metrics)
        return films
    
    async def film_details(self, film_id) -> Optional[dict]:
        result = await self.db.film.find_one({"_id": ObjectId(film_id), "is_active": True}, {"_id": 1,
            "artist_id": 1, "title": 1, "director": 1, "artists": 1, "release_year": 1, "length": 1, "genre": 1,
            "synopsis": 1, "type": 1, "signature": 1})
        if not result:
            return None
        result["_id"] = str(result["_id"])
        
        response_data = {
                "_id": result["_id"], "title": result["title"], "director": result["director"], "artists": result["artists"], "release_year": result["release_year"],
                "length": result["length"], "genre": result["genre"], "synopsis": result["synopsis"], "type": result["type"]
            }
        
        artist = await self.db.user.find_one({"_id": ObjectId(result["artist_id"])}, {"public_key": 1})
        if artist and artist.get("public_key") and result.get("signature"):
            metadata = {
                "title": result["title"], "director": result["director"], "artists": result["artists"], "release_year": result["release_year"],
                "length": result["length"], "genre": result["genre"], "synopsis": result["synopsis"], "type": result["type"]
            }
            verify = self.signature.signature_verification(result["signature"], metadata, artist["public_key"])
            response_data["verify"] = verify
        else:
            response_data["verify"] = False
        
        metrics = await self.metrics.get_film_metrics(result["_id"])
        response_data.update(metrics)
        return response_data      
    
    async def toggle_film(self, film_id: str):
        film = await self.db.film.find_one({"_id": ObjectId(film_id)})
        if not film:
            raise ValueError("La película no existe")
        if film["is_active"] == True:
            await self.db.film.update_one({"_id": ObjectId(film_id)}, {"$set": {"is_active": False}})
            return {"message": "La película se ha desactivado correctamente"}
        else:
            await self.db.film.update_one({"_id": ObjectId(film_id)}, {"$set": {"is_active": True}})
            return {"message": "La película se ha activado correctamente"}
    
    async def user_key_generation(self, user_id: str) -> str:
        public_b64, private_b64 = self.signature.key_generation()
        await self.db.user.update_one({"_id": ObjectId(user_id)}, {"$set": {"public_key": public_b64}})
        return private_b64