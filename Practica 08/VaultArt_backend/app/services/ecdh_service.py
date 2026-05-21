from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from typing import Dict
import base64
import secrets
import json

class ECDHservice():
    def __init__(self):
        self.curve = ec.SECP384R1()
        self.server_key_generation()
        
    def server_key_generation(self):
        self.private_key = ec.generate_private_key(self.curve, default_backend())
        self.public_key = self.private_key.public_key()
        
    def get_public_key(self) -> str:
        return self.public_key.public_bytes(encoding=serialization.Encoding.PEM, 
                                            format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        
    def derive_secret(self, client_public_key: str, salt: bytes) -> bytes:
        try:
            client_public = serialization.load_pem_public_key(client_public_key.encode(), backend=default_backend())
        except Exception:
            raise ValueError("Ocurrio un error con la llave")
        if not isinstance(client_public, ec.EllipticCurvePublicKey):
            raise ValueError(f"La clave pública es incorrecta")
        if client_public.curve.name != self.curve.name:
            raise ValueError(f"La clave no pertence a la curva esperada")
        
        try:
            secret = self.private_key.exchange(ec.ECDH(), client_public)
            hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b"vaultart_ecdh", backend=default_backend())
            return hkdf.derive(secret)
        except Exception:
            raise ValueError(f"Ocurrio un error al realizar ECDH")
        
    def decrypt_data(self, data_encrypt: Dict[str, str], secret: bytes) -> dict:
        raw = base64.b64decode(data_encrypt["ciphertext"])
        nonce = base64.b64decode(data_encrypt["nonce"])
        ciphertext = raw[:-16]
        tag = raw[-16:]
        cipher = Cipher(algorithms.AES(secret), modes.GCM(nonce, tag), backend=default_backend())
        decrypt = cipher.decryptor()
        decrypt.authenticate_additional_data(b"vaultart_ecdh")
        plaintext = decrypt.update(ciphertext) + decrypt.finalize()
        return json.loads(plaintext.decode("utf-8"))
    
    def encrypt_data(self, data: Dict[str, str], secret: bytes) -> dict:
        nonce = secrets.token_bytes(12)
        plaintext = json.dumps(data, sort_keys=True).encode("utf-8")
        cipher = Cipher(algorithms.AES(secret), modes.GCM(nonce), backend=default_backend())
        encrypt = cipher.encryptor()
        encrypt.authenticate_additional_data(b"vaultart_ecdh")
        ciphertext = encrypt.update(plaintext) + encrypt.finalize()
        return {"ciphertext": base64.b64encode(ciphertext + encrypt.tag).decode(),
                "nonce": base64.b64encode(nonce).decode()}