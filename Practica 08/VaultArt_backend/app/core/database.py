from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        
    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_NAME]
            await self.client.admin.command('ping')
        except Exception as e:
            raise
    
    async def disconnect(self):
        if self.client:
            self.client.close()

database = Database()

async def get_database():
    return database.db