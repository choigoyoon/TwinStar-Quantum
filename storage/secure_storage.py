"""
API 키 암호화 저장 시스템
"""

import os
import sys
import json
import base64
import hashlib
from typing import Dict, Optional

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# ========== EXE 호환 경로 처리 ==========
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

try:
    from paths import Paths
    Paths.ensure_dirs()
    ENCRYPTED_KEYS_FILE = Paths.encrypted_keys()
    PLAIN_KEYS_FILE = os.path.join(Paths.CREDENTIALS, 'exchange_keys.json')
except ImportError:
    BASE_DIR = get_base_path()
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    CREDENTIALS_DIR = os.path.join(BASE_DIR, 'credentials')
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    ENCRYPTED_KEYS_FILE = os.path.join(DATA_DIR, 'encrypted_keys.dat')
    PLAIN_KEYS_FILE = os.path.join(CREDENTIALS_DIR, 'exchange_keys.json')


def _get_machine_key() -> bytes:
    """
    하드웨어 기반 암호화 키 생성
    MAC 주소 + 시스템 정보로 고유 키 생성
    """
    import platform
    import uuid
    
    # MAC 주소
    mac = hex(uuid.getnode())
    
    # 시스템 정보
    system_info = f"{platform.node()}-{platform.processor()}"
    
    # 조합
    combined = f"{mac}-{system_info}".encode('utf-8')
    
    # SHA256 해시 후 32바이트 키 생성
    key_hash = hashlib.sha256(combined).digest()
    
    # Fernet용 키 (base64 url-safe)
    return base64.urlsafe_b64encode(key_hash)


def _simple_encrypt(data: str, key: bytes) -> str:
    """간단한 XOR 암호화 (cryptography 없을 때)"""
    key_bytes = hashlib.sha256(key).digest()
    data_bytes = data.encode('utf-8')
    
    encrypted = bytearray()
    for i, byte in enumerate(data_bytes):
        encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
    
    return base64.b64encode(bytes(encrypted)).decode('utf-8')


def _simple_decrypt(encrypted: str, key: bytes) -> str:
    """간단한 XOR 복호화"""
    key_bytes = hashlib.sha256(key).digest()
    data_bytes = base64.b64decode(encrypted)
    
    decrypted = bytearray()
    for i, byte in enumerate(data_bytes):
        decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
    
    return bytes(decrypted).decode('utf-8')


class SecureKeyStorage:
    """API 키 암호화 저장소"""
    
    def __init__(self):
        self.machine_key = _get_machine_key()
        self.fernet = None
        
        if HAS_CRYPTO:
            self.fernet = Fernet(self.machine_key)
    
    def encrypt(self, data: str) -> str:
        """데이터 암호화"""
        if self.fernet:
            return self.fernet.encrypt(data.encode()).decode()
        else:
            return _simple_encrypt(data, self.machine_key)
    
    def decrypt(self, encrypted: str) -> str:
        """데이터 복호화"""
        if self.fernet:
            return self.fernet.decrypt(encrypted.encode()).decode()
        else:
            return _simple_decrypt(encrypted, self.machine_key)
    
    def save_api_keys(self, keys: Dict[str, Dict]) -> bool:
        """
        API 키 저장
        
        keys = {
            'bybit': {'api_key': 'xxx', 'api_secret': 'yyy'},
            'binance': {'api_key': 'xxx', 'api_secret': 'yyy'},
        }
        """
        try:
            # JSON으로 직렬화
            json_data = json.dumps(keys, ensure_ascii=False)
            
            # 암호화
            encrypted = self.encrypt(json_data)
            
            # 저장 경로 폴더 생성
            os.makedirs(os.path.dirname(ENCRYPTED_KEYS_FILE), exist_ok=True)
            with open(ENCRYPTED_KEYS_FILE, 'w', encoding='utf-8') as f:
                f.write(encrypted)
            
            # 기존 평문 파일 삭제 (보안)
            if os.path.exists(PLAIN_KEYS_FILE):
                os.remove(PLAIN_KEYS_FILE)
            
            return True
            
        except Exception as e:
            print(f"API 키 저장 오류: {e}")
            return False
    
    def load_api_keys(self) -> Dict[str, Dict]:
        """API 키 로드"""
        try:
            # 암호화 파일 우선
            if os.path.exists(ENCRYPTED_KEYS_FILE):
                with open(ENCRYPTED_KEYS_FILE, 'r', encoding='utf-8') as f:
                    encrypted = f.read()
                
                decrypted = self.decrypt(encrypted)
                return json.loads(decrypted)
            
            # 평문 파일 (레거시 호환)
            if os.path.exists(PLAIN_KEYS_FILE):
                with open(PLAIN_KEYS_FILE, 'r', encoding='utf-8') as f:
                    keys = json.load(f)
                
                # 암호화 파일로 마이그레이션
                self.save_api_keys(keys)
                return keys
            
            return {}
            
        except Exception as e:
            print(f"API 키 로드 오류: {e}")
            return {}
    
    def get_exchange_keys(self, exchange: str) -> Optional[Dict]:
        """특정 거래소 키 가져오기"""
        keys = self.load_api_keys()
        return keys.get(exchange.lower())
    
    def set_exchange_keys(self, exchange: str, api_key: str, api_secret: str, 
                          passphrase: str = None):
        """특정 거래소 키 저장"""
        keys = self.load_api_keys()
        
        key_data = {
            'api_key': api_key,
            'api_secret': api_secret
        }
        if passphrase:
            key_data['passphrase'] = passphrase
        
        keys[exchange.lower()] = key_data
        self.save_api_keys(keys)
    
    def delete_exchange_keys(self, exchange: str):
        """특정 거래소 키 삭제"""
        keys = self.load_api_keys()
        if exchange.lower() in keys:
            del keys[exchange.lower()]
            self.save_api_keys(keys)
    
    def list_exchanges(self) -> list:
        """저장된 거래소 목록"""
        keys = self.load_api_keys()
        return list(keys.keys())
    
    def has_keys(self, exchange: str) -> bool:
        """거래소 키 존재 여부"""
        keys = self.load_api_keys()
        return exchange.lower() in keys


# 싱글톤
_storage = None

def get_secure_storage() -> SecureKeyStorage:
    global _storage
    if _storage is None:
        _storage = SecureKeyStorage()
    return _storage


# 테스트
if __name__ == "__main__":
    print("=== API 키 암호화 테스트 ===\\n")
    
    print(f"Base path: {get_base_path()}")
    print(f"Encrypted file: {ENCRYPTED_KEYS_FILE}")
    print(f"Frozen: {getattr(sys, 'frozen', False)}")
    
    storage = get_secure_storage()
    
    print(f"\\nCrypto library: {'Fernet' if HAS_CRYPTO else 'Simple XOR'}")
    
    # 테스트 키 저장
    test_keys = {
        'bybit': {
            'api_key': 'test_api_key_12345',
            'api_secret': 'test_secret_67890'
        }
    }
    
    storage.save_api_keys(test_keys)
    print("Keys saved (encrypted)")
    
    # 로드
    loaded = storage.load_api_keys()
    print(f"Keys loaded: {loaded}")
    
    # 검증
    if loaded == test_keys:
        print("\\n[OK] Encryption/Decryption works!")
    else:
        print("\\n[ERROR] Mismatch!")
