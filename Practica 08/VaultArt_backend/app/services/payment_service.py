from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from bson import ObjectId
import secrets

class PaymentService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
    async def process_subscription(self, user_id: str, payment_data: dict) -> Tuple[Optional[dict], Optional[datetime]]:
        payment_id = f"sim_{secrets.token_hex(8)}"
        last_four = payment_data["card_number"][-4:]
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30)
        payment_record = {
            "user_id": user_id,
            "amount": 99.00,
            "currency": "MXN",
            "last_four": last_four,
            "status": "completed",
            "payment_id": payment_id,
            "created_at": start_date,
            "expires_at": end_date
        }
        
        payment_result = await self.db.payment.insert_one(payment_record)
        payment_record["_id"] = str(payment_result.inserted_id)
        
        result = await self.db.user.update_one({"_id": ObjectId(user_id)}, {"$set": {"subscription_active": True,
                                                                            "subscription_start_date": start_date,
                                                                            "subscription_end_date": end_date}})
        if result.modified_count == 0:
            raise ValueError("Ocurrió un error al activar la suscripción")
        return payment_record, end_date
    
    async def get_status_subscription(self, user_id) -> dict:
        user = await self.db.user.find_one({"_id": ObjectId(user_id)}, {"subscription_active": 1, "subscription_end_date": 1})
        if not user:
            return {"is_active": False}
        is_active = user.get("subscription_active", False)
        expires_at = user.get("subscription_end_date")
        
        if is_active and expires_at < datetime.now():
            is_active = False
            await self.db.user.update_one({"_id": ObjectId(user_id)}, {"$set": {"subscription_active": False}, 
                                                                        "$unset": {"subscription_start_date": "", "subscription_end_date": ""}})
        return {"is_active": is_active, "expires_at": expires_at}
    
    async def payment_history(self, user_id: str, limit: int = 10) -> List[dict]:
        data = self.db.payment.find({"user_id": user_id}, {"_id": 1, "amount": 1, "currency": 1, "last_four": 1,
                                                                "created_at": 1, "expires_at": 1}).sort("created_at", -1).limit(limit)
        payments = await data.to_list(length=limit)
        for p in payments:
            p["_id"] = str(p["_id"])
        
        return payments
    
    async def cancel_subscription(self, user_id: str) -> bool:
        user = await self.db.user.find_one({"_id": ObjectId(user_id)}, {"password": 0})
        if not user or not user.get("subscription_active", False):
            return False
        await self.db.user.update_one({"_id": ObjectId(user_id)}, {"$set": {"subscription_active": False},
                                                                    "$unset": {"subscription_start_date": "", "subscription_end_date": ""}})
        return True