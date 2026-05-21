from botocore.config import Config
from app.core.config import settings
import asyncio
import boto3
import time

class R2Service:
    def __init__(self):
        self.bucket = settings.R2_BUCKET
        self.client = boto3.client("s3", endpoint_url=settings.R2_ENDPOINT, aws_access_key_id=settings.R2_ACCESS_KEY, 
                                    aws_secret_access_key=settings.R2_SECRET_KEY, config=Config(
                                        signature_version="s3v4", max_pool_connections=50, retries={"max_attempts": 3, "mode": "standard"},
                                        connect_timeout=10, read_timeout=30, tcp_keepalive=True
                                    ), region_name="auto")
        
    async def upload_chunk(self, data: bytes, key: str) -> str:
        loop = asyncio.get_event_loop()
        def upload():
            for attemp in range(3):
                try:
                    self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
                    return
                except Exception as e:
                    if attemp == 2:
                        raise e
                    time.sleep(2**attemp)
        await loop.run_in_executor(None, upload)
        return key    

    async def download_chunk(self, key: str):
        loop = asyncio.get_event_loop()
        def download():
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        return await loop.run_in_executor(None, download)
    
    async def delete_chunk(self, key: str):
        loop= asyncio.get_event_loop()
        def delete():
            self.client.delete_object(Bucket=self.bucket, Key=key)
        await loop.run_in_executor(None, delete)