from ecdsa.keys import SigningKey, VerifyingKey
from ecdsa.curves import NIST384p
from ecdsa.util import sigencode_der, sigdecode_der
from hashlib import sha3_256
from typing import Tuple
import base64
import json

class SignatureService:
    def __init__(self):
        self.curve = NIST384p
        self.hash_function = sha3_256
        
    def key_generation(self) -> Tuple[str, str]:
        private_key = SigningKey.generate(curve=self.curve, hashfunc=self.hash_function)
        public_key = private_key.verifying_key
        private_key_b64 = base64.b64encode(private_key.to_pem()).decode()
        public_key_b64 = base64.b64encode(public_key.to_pem()).decode()
        
        return public_key_b64, private_key_b64
    
    def signature_data(self, metadata: dict, private_key_b64: str) -> str:
        metadata_str = json.dumps(metadata, sort_keys=True)
        metadata_bytes = metadata_str.encode("utf-8")
        private_key_bits = base64.b64decode(private_key_b64)
        private_key = SigningKey.from_pem(private_key_bits, hashfunc=self.hash_function)
        try:
            signature = private_key.sign(metadata_bytes, sigencode=sigencode_der)
            signature_b64 = base64.b64encode(signature).decode()
            return signature_b64
        except Exception as e:
            raise ValueError(f"Ocurrio un error al firmar. {str(e)}")
            
    def signature_verification(self, signature: str, metadata: dict, public_key_b64: str) -> bool:
        metadata_str = json.dumps(metadata, sort_keys=True)
        metadata_bytes = metadata_str.encode("utf-8")
        public_key_bits = base64.b64decode(public_key_b64)
        public_key = VerifyingKey.from_pem(public_key_bits, hashfunc=self.hash_function)
        signature_decode = base64.b64decode(signature)
        try:
            public_key.verify(signature_decode, metadata_bytes, hashfunc=self.hash_function, sigdecode=sigdecode_der)
            return True
        except Exception as e:
            return False