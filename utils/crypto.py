"""
TwinStar Quantum - Security Utility
API 키 및 민감 정보 암호화 저장 관리
"""
import os
import logging
from cryptography.fernet import Fernet
from pathlib import Path

logger = logging.getLogger(__name__)

# 마스터 키 저장 경로 (user 폴더 내, .gitignore에 포함됨)
try:
    from paths import Paths
    KEY_FILE = Path(Paths.USER_DIR) / "secret.key"
except:
    KEY_FILE = Path("user") / "secret.key"

class CryptoManager:
    """
    Fernet 대칭 암호화를 이용한 보안 관리자
    """
    
    _instance = None
    _key = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CryptoManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._key is None:
            self._key = self._load_or_generate_key()
            self.fernet = Fernet(self._key)

    def _load_or_generate_key(self) -> bytes:
        """키 파일을 로드하거나 없으면 생성"""
        if not KEY_FILE.parent.exists():
            KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            
        if not KEY_FILE.exists():
            logger.info("[SECURITY] Generating new master key...")
            key = Fernet.generate_key()
            with open(KEY_FILE, "wb") as f:
                f.write(key)
            # 파일 권한 제한 (Windows는 생략되거나 다르게 처리됨)
            return key
        
        with open(KEY_FILE, "rb") as f:
            return f.read()

    def encrypt(self, plain_text: str) -> str:
        """문자열 암호화"""
        if not plain_text: return ""
        return self.fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        """문자열 복호화"""
        if not encrypted_text: return ""
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception as e:
            logger.error(f"[SECURITY] Decryption failed: {e}")
            return ""

# 편의 함수
def encrypt_key(api_key: str) -> str:
    return CryptoManager().encrypt(api_key)

def decrypt_key(encrypted: str) -> str:
    return CryptoManager().decrypt(encrypted)

if __name__ == "__main__":
    # 테스트
    test_key = "my_secret_api_key_12345"
    enc = encrypt_key(test_key)
    dec = decrypt_key(enc)
    
    logger.info(f"Original: {test_key}")
    logger.info(f"Encrypted: {enc}")
    logger.info(f"Decrypted: {dec}")
    assert test_key == dec, "Encryption/Decryption mismatch!"
    logger.info("✅ Crypto test passed")
