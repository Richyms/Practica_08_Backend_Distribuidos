from Crypto.Cipher import ChaCha20_Poly1305, AES
from Crypto.Random import get_random_bytes
from typing import Tuple
from app.core.config import settings
import base64

class EncryptionService:
    def __init__(self):
        self.kek = base64.b64decode(settings.KEY_ENCRYPTION_KEY)
        
    def encrypt_chunk(self, chunk_data: bytes, key: bytes) -> bytes:
        try:
            nonce = get_random_bytes(12)
            cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(chunk_data)
            return nonce + ciphertext + tag
        except Exception as e:
            raise ValueError(f"Error al guardar el contenido: {str(e)}")
    
    def decrypt_chunk(self, encrypted_data: bytes, key: bytes) -> bytes:
        try:
            tag = encrypted_data[-16:]
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:-16]
            cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag)
        except Exception as e:
            raise ValueError(f"Error al obtener el contenido: {str(e)}")
    
    def encrypt_key_content(self, content_key: bytes) -> Tuple[str, str, str]:
        try:
            cipher = AES.new(key=self.kek, mode=AES.MODE_KW)
            ciphertext = cipher.seal(content_key)
            return base64.b64encode(ciphertext).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Error: {str(e)}. Inténtalo de nuevo más tarde")
        
    def decrypt_key_content(self, encrypted_ck: str) -> bytes:
        try:
            cipher = AES.new(self.kek, AES.MODE_KW)
            ciphertext = base64.b64decode(encrypted_ck)
            return cipher.unseal(ciphertext)
        except Exception as e:
            raise ValueError(f"Error: {str(e)}. Inténtalo de nuevo más tarde")
            
    def generate_key_content(self) -> bytes:
        return get_random_bytes(32)