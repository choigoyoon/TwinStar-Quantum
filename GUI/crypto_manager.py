# crypto_manager.py - API 키 암호화 관리자
"""
머신 고유 ID 기반 AES-256-GCM 암호화
- 다른 PC에서 파일 복사해도 복호화 불가
- config/api_keys.dat에 암호화 저장
"""

import os
import json
import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict

# Logging
import logging
logger = logging.getLogger(__name__)

# cryptography 타입 초기화
AESGCM: Any = None
hashes: Any = None
PBKDF2HMAC: Any = None

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.info("[Warning] cryptography 라이브러리 없음. pip install cryptography")

# 파일 경로
import sys

# [FIX] EXE 환경(PyInstaller) 경로 호환성
if getattr(sys, 'frozen', False):
    # EXE 실행 시: 실행 파일이 있는 폴더 기준
    ROOT_DIR = Path(sys.executable).parent
else:
    # Python 실행 시: 현재 파일의 상위상위 폴더 (GUI/../)
    ROOT_DIR = Path(__file__).parent.parent

CONFIG_DIR = ROOT_DIR / 'config'
API_KEYS_FILE = CONFIG_DIR / 'api_keys.dat'
LEGACY_CONFIG_FILE = CONFIG_DIR / 'exchange_config.json'

# 암호화 상수
SALT = b'staru_quantum_v2_salt_2024'
NONCE_SIZE = 12


def get_machine_id() -> str:
    """
    머신 고유 ID 생성 (MAC + UUID)
    다른 PC에서는 다른 ID가 생성됨
    """
    try:
        # MAC 주소
        mac = hex(uuid.getnode())[2:]
        
        # 추가 엔트로피: 사용자 이름 + 홈 디렉토리
        user = os.getenv('USERNAME', os.getenv('USER', 'default'))
        home = str(Path.home())
        
        # 조합하여 해시
        combined = f"{mac}:{user}:{home}"
        return hashlib.sha256(combined.encode()).hexdigest()
    except Exception as e:
        logger.info(f"[Warning] Machine ID 생성 실패: {e}")
        # 폴백: MAC만 사용
        return hashlib.sha256(hex(uuid.getnode()).encode()).hexdigest()


def _derive_key(machine_id: str) -> bytes:
    """머신 ID에서 AES 키 유도 (32바이트)"""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography 라이브러리가 필요합니다")
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
    )
    return kdf.derive(machine_id.encode())


def _encrypt(data: bytes, key: bytes) -> bytes:
    """AES-256-GCM 암호화"""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography 라이브러리가 필요합니다")
    
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def _decrypt(encrypted: bytes, key: bytes) -> bytes:
    """AES-256-GCM 복호화"""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography 라이브러리가 필요합니다")
    
    nonce = encrypted[:NONCE_SIZE]
    ciphertext = encrypted[NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def save_api_keys(config: Dict) -> bool:
    """
    API 키 암호화 저장
    
    Args:
        config: {'bybit': {'api_key': '...', 'api_secret': '...'}, ...}
    
    Returns:
        성공 여부
    """
    try:
        if not CRYPTO_AVAILABLE:
            logger.info("[Error] cryptography 라이브러리 없음")
            return False
        
        # 디렉토리 생성
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # JSON 직렬화
        json_data = json.dumps(config, ensure_ascii=False, indent=2)
        
        # 암호화
        machine_id = get_machine_id()
        key = _derive_key(machine_id)
        encrypted = _encrypt(json_data.encode('utf-8'), key)
        
        # 저장
        with open(API_KEYS_FILE, 'wb') as f:
            f.write(encrypted)
        
        # 검증
        if not verify_save(config):
            logger.info("[Error] 저장 검증 실패")
            return False
        
        logger.info(f"[Crypto] API 키 암호화 저장 완료: {API_KEYS_FILE}")
        return True
        
    except Exception as e:
        logger.info(f"[Error] API 키 저장 실패: {e}")
        return False


def load_api_keys() -> Dict:
    """
    API 키 복호화 로드
    
    Returns:
        복호화된 설정 dict (실패 시 빈 dict)
    """
    try:
        if not CRYPTO_AVAILABLE:
            # logger.info("[Warning] cryptography 없음, 레거시 파일 시도")
            return _load_legacy_config()
        
        if not API_KEYS_FILE.exists():
            # logger.info("[Crypto] 암호화 파일 없음, 레거시 마이그레이션 시도")
            return _migrate_legacy_config()
        
        # 파일 읽기
        with open(API_KEYS_FILE, 'rb') as f:
            encrypted = f.read()
        
        # 복호화
        machine_id = get_machine_id()
        key = _derive_key(machine_id)
        decrypted = _decrypt(encrypted, key)
        
        # JSON 파싱
        config = json.loads(decrypted.decode('utf-8'))
        logger.info(f"[Crypto] API 키 복호화 로드 완료 ({len(config)}개 거래소)")
        return config
        
    except Exception as e:
        logger.info(f"[Error] API 키 로드 실패: {e}")
        logger.info("다른 PC에서 복사한 파일이거나 손상됨")
        return {}


def verify_save(original: Dict) -> bool:
    """저장 직후 검증 (원본 == 로드)"""
    try:
        loaded = load_api_keys()
        
        # 키 비교
        for exchange, data in original.items():
            if exchange.startswith('_'):
                continue
            loaded_data = loaded.get(exchange, {})
            if data.get('api_key') != loaded_data.get('api_key'):
                return False
            if data.get('api_secret') != loaded_data.get('api_secret'):
                return False
        
        return True
    except Exception as e:
        logger.info(f"[Crypto] Verify save failed: {e}")
        return False


def _load_legacy_config() -> Dict:
    """레거시 exchange_config.json 로드 (평문)"""
    try:
        if LEGACY_CONFIG_FILE.exists():
            with open(LEGACY_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.info(f"[Warning] 레거시 설정 로드 실패: {e}")
    return {}


def _migrate_legacy_config() -> Dict:
    """레거시 설정 → 암호화 마이그레이션"""
    legacy = _load_legacy_config()
    
    if legacy:
        logger.info("[Crypto] 레거시 설정 발견, 암호화 마이그레이션 중...")
        if save_api_keys(legacy):
            # 백업 후 삭제
            backup_path = LEGACY_CONFIG_FILE.with_suffix('.json.bak')
            LEGACY_CONFIG_FILE.rename(backup_path)
            logger.info(f"[Crypto] 레거시 파일 백업: {backup_path}")
        return legacy
    
    return {}


def delete_encrypted_keys() -> bool:
    """암호화 파일 삭제 (초기화용)"""
    try:
        if API_KEYS_FILE.exists():
            API_KEYS_FILE.unlink()
            logger.info("[Crypto] 암호화 파일 삭제됨")
            return True
    except Exception as e:
        logger.info(f"[Error] 삭제 실패: {e}")
    return False


# ============ 테스트 ============
if __name__ == "__main__":
    logger.info("=== Crypto Manager Test ===")
    logger.info(f"Machine ID: {get_machine_id()[:16]}...")
    logger.info(f"Crypto Available: {CRYPTO_AVAILABLE}")
    
    # 테스트 저장/로드
    test_config = {
        'bybit': {'api_key': 'test_key_123', 'api_secret': 'test_secret_456'},
        'binance': {'api_key': 'bn_key', 'api_secret': 'bn_secret'}
    }
    
    logger.info("\n1. Saving...")
    save_api_keys(test_config)
    
    logger.info("\n2. Loading...")
    loaded = load_api_keys()
    logger.info(f"Loaded: {list(loaded.keys())}")
    
    logger.info("\n3. Verify...")
    if loaded.get('bybit', {}).get('api_key') == 'test_key_123':
        logger.info("✅ Test PASSED!")
    else:
        logger.info("❌ Test FAILED!")
