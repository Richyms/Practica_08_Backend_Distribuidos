from app.services.encryption_service import EncryptionService
from app.services.signature_service import SignatureService
from app.services.film_metrics_service import FilmMetricsService
from app.services.R2_service import R2Service
from app.schemas.film_schema import FilmCreate, FilmUpdate
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
import math
import os
import asyncio

class FilmService:
    def __init__(self, db: AsyncIOMotorDatabase, encryption_service: EncryptionService, r2_service: R2Service, signature_service: SignatureService):
        self.db = db
        self.encryption = encryption_service
        self.r2 = r2_service
        self.signature = signature_service
        self.metrics = FilmMetricsService(db)
        self.chunks_size = 2*1024*1024
     
    def read_file_in_chunks(self, file_path: str, chunk_size: int):
         with open(file_path, "rb") as file:
             while True:
                 chunk = file.read(chunk_size)
                 if not chunk:
                     break
                 yield chunk

    async def encrypt_async(self, data: bytes, key: bytes):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.encryption.encrypt_chunk, data, key)
    
    async def decrypt_async(self, data: bytes, key: bytes):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.encryption.decrypt_chunk, data, key)
        
    async def upload_file(self, film_data: FilmCreate, artist_id: str, file_path: str, poster_path: str, private_key_b64: str) -> Optional[dict]:
        key = self.encryption.generate_key_content()
        encrypted_key = self.encryption.encrypt_key_content(key)
        
        file_size = os.path.getsize(file_path)
        total_chunks = math.ceil(file_size/self.chunks_size)
        film_dict = film_data.model_dump()
        
        poster_key = f"films/posters/{film_data.title.replace(" ", "")}_{int(datetime.now(timezone.utc).timestamp())}.jpg"
        await self.r2.upload_chunk(open(poster_path, "rb").read(), poster_key)
        
        signature_metadata = self.signature.signature_data(film_dict, private_key_b64)
        result = await self.db.film.insert_one({
            **film_dict,
            "artist_id": artist_id,
            "content_key": encrypted_key,
            "total_chunks": total_chunks,
            "chunk_size": self.chunks_size,
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
            "poster": poster_key,
            "signature": signature_metadata
        })
        film_id = str(result.inserted_id)
        await self.metrics.create_film_metrics(film_id)
        
        semaphore = asyncio.Semaphore(5)
        async def process(index, data):
            async with semaphore:
                encrypted = await self.encrypt_async(data, key)
                object_key = f"films/{film_id}/chunk_{index+1:04d}.enc"
                await self.r2.upload_chunk(encrypted, object_key)
                return {
                    "film_id": film_id,
                    "chunk_index": index+1,
                    "chunk_size": len(data),
                    "object_key": object_key,
                    "created_at": datetime.now(timezone.utc)
                }
        tasks = []
        chunk_metadata = []
        for i, chunk in enumerate(self.read_file_in_chunks(file_path, self.chunks_size)):
            tasks.append(process(index=i, data=chunk))
            if len(tasks) >= 20:
                batch_results = await asyncio.gather(*tasks)
                chunk_metadata.extend(batch_results)
                tasks = []
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            chunk_metadata.extend(batch_results)
            
        await self.db.film_chunk.insert_many(chunk_metadata)                    
        return {"title": film_data.title, "director": film_data.director, "message": "La película ha sido procesada y almacenada correctamente."}
    
    async def stream_file(self, film_id: str, start_chunk: int = 1):
        film = await self.db.film.find_one({"_id": ObjectId(film_id), "is_active": True})
        if not film:
            raise ValueError("Película no encontrada")
        
        try:
            key = self.encryption.decrypt_key_content(film["content_key"])
            cursor = self.db.film_chunk.find({"film_id": film_id, "chunk_index": {"$gte": start_chunk}}).sort("chunk_index", 1)
            async for chunk in cursor:
                encrypted = await self.r2.download_chunk(chunk["object_key"])
                decrypted = await self.decrypt_async(encrypted, key)
                yield decrypted
        except Exception as e:
            raise ValueError(f"Error: {str(e)}")
            
    async def get_films(self, skip, limit) -> List[dict]:
        result = self.db.film.find({"is_active": True}, {"_id": 1, "title": 1, "director": 1, "release_year": 1,
                                                            "length": 1, "genre": 1}).sort("release_year", -1).skip(skip).limit(limit)
        films = await result.to_list(length=limit)
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
    
    async def get_poster_file(self, film_id: str):
        try:
            film = await self.db.film.find_one({"_id": ObjectId(film_id)}, {"poster": 1})
            if not film:
                raise ValueError("No se pudo encontrar la película.")
            return await self.r2.download_chunk(film["poster"])
        except Exception as e:
            raise ValueError("No se pudo obtener el poster correctamente.")
    
    async def update_file(self, film_id: str, data_update: FilmUpdate, private_key_b64: str) -> Optional[dict]:        
        film = await self.db.film.find_one({"_id": ObjectId(film_id), "is_active": True}, {"title": 1, "director": 1})
        update_dict = data_update.model_dump(exclude_unset=True)
        if not update_dict or not film:
            return
        await self.db.film.update_one({"_id": ObjectId(film_id), "is_active": True}, {"$set": update_dict})
        
        update_film = await self.db.film.find_one({"_id": ObjectId(film_id), "is_active": True}, {"_id": 1,
            "artist_id": 1, "title": 1, "director": 1, "artists": 1, "release_year": 1, "length": 1, "genre": 1,
            "synopsis": 1, "type": 1, "signature": 1})
        metadata = {
                "title": update_film["title"], "director": update_film["director"], "artists": update_film["artists"], "release_year": update_film["release_year"],
                "length": update_film["length"], "genre": update_film["genre"], "synopsis": update_film["synopsis"], "type": update_film["type"]
            }
        new_signature = self.signature.signature_data(metadata, private_key_b64)
        await self.db.film.update_one({"_id": ObjectId(film_id)}, {"$set": {"signature": new_signature}})
        
        return {"title": update_film["title"], "director": update_film["director"], "message": "Los datos se han actualizado correctamente."}
    
    async def delete_file(self, film_id: str) -> Optional[dict]:
        film = await self.db.film.find_one({"_id": ObjectId(film_id), "is_active": True} ,{"title": 1, "director": 1, "poster": 1})
        if not film:
            raise ValueError("Película no encontrada")
        
        chunks = await self.db.film_chunk.find({"film_id": film_id}).to_list(length=1000)
        delete_chunks = 0
        for chunk in chunks:
            try:
                await self.r2.delete_chunk(chunk["object_key"])
                delete_chunks += 1
            except Exception as e:
                raise ValueError("Ocurrió un error al eliminar le película.")
            
        try:
            await self.r2.delete_chunk(film["poster"])
        except Exception as e:
            raise ValueError("Ocurrió un error al eliminar el poster")
        
        await self.db.film_chunk.delete_many({"film_id": film_id})
        await self.db.film_metrics.delete_many({"film_id": film_id})
        await self.db.user.update_many({}, {"$pull": {"viewed_films": film_id, "liked_films": film_id, "rated_films": film_id}})
        await self.db.film.delete_one({"_id": ObjectId(film_id)})
        
        return {"title": film["title"], "director": film["director"], "message": "La película se ha eliminado correctamente."}
    
    async def get_genres(self) -> List[str]:
        result = await self.db.film.distinct("genre", {"is_active": True})
        return sorted(result)
    
    async def get_film_type(self, type_film: str) -> Optional[List[dict]]:
        result = self.db.film.find({"type": type_film, "is_active": True}, {"_id": 1, "title": 1, "director": 1, "release_year": 1,
                                                            "length": 1, "genre": 1})
        result_list = await result.to_list()
        for film in result_list:
            film["_id"] = str(film["_id"])
            metrics = await self.metrics.get_film_metrics(film["_id"])
            film.update(metrics)
        return result_list