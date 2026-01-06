# security.py - 보안 관리자

import json
import hashlib
import base64
from pathlib import Path
from datetime import datetime

# Logging
import logging
logger = logging.getLogger(__name__)


class SecurityManager:
    """API 키 및 인증 관리"""
    
    CONFIG_FILE = Path(__file__).parent / "security_config.json"
    
    def __init__(self):
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        """설정 로드"""
        try:
            if self.CONFIG_FILE.exists():
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            pass
        return {}
    
    def _save_config(self):
        """설정 저장"""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            logger.info(f"Security config save error: {e}")
    
    def encrypt_key(self, key: str) -> str:
        """API 키 암호화 (Base64 인코딩)
        
        주의: 실제 프로덕션에서는 더 강력한 암호화 사용 필요
        """
        return base64.b64encode(key.encode()).decode()
    
    def decrypt_key(self, encrypted: str) -> str:
        """API 키 복호화"""
        try:
            return base64.b64decode(encrypted.encode()).decode()
        except (ValueError, UnicodeDecodeError):
            return ""
    
    def save_api_keys(self, exchange: str, api_key: str, api_secret: str, 
                      testnet: bool = False):
        """API 키 저장"""
        if 'exchanges' not in self._config:
            self._config['exchanges'] = {}
        
        self._config['exchanges'][exchange] = {
            'api_key': self.encrypt_key(api_key),
            'api_secret': self.encrypt_key(api_secret),
            'testnet': testnet,
            'saved_at': datetime.now().isoformat()
        }
        
        self._save_config()
    
    def get_api_keys(self, exchange: str) -> dict:
        """API 키 조회"""
        exchanges = self._config.get('exchanges', {})
        if exchange not in exchanges:
            return {}
        
        data = exchanges[exchange]
        return {
            'api_key': self.decrypt_key(data.get('api_key', '')),
            'api_secret': self.decrypt_key(data.get('api_secret', '')),
            'testnet': data.get('testnet', False)
        }
    
    def has_api_keys(self, exchange: str) -> bool:
        """API 키 존재 여부"""
        keys = self.get_api_keys(exchange)
        return bool(keys.get('api_key'))
    
    def delete_api_keys(self, exchange: str):
        """API 키 삭제"""
        if 'exchanges' in self._config and exchange in self._config['exchanges']:
            del self._config['exchanges'][exchange]
            self._save_config()
    
    def validate_session(self, session_token: str) -> bool:
        """세션 유효성 검증 (스텁)"""
        # 개발 모드: 항상 유효
        return True
    
    def create_session(self, user_info: dict) -> str:
        """세션 생성 (스텁)"""
        return "dev_session_token"
    
    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호 해싱"""
        return hashlib.sha256(password.encode()).hexdigest()


# 테스트
if __name__ == "__main__":
    sm = SecurityManager()
    
    # API 키 저장 테스트
    sm.save_api_keys('bybit', 'test_api_key_123', 'test_secret_456', testnet=True)
    
    # API 키 조회 테스트
    keys = sm.get_api_keys('bybit')
    logger.info(f"API Key: ***{keys.get('api_key', '')[-4:]}")
    logger.info(f"Secret: ***{keys.get('api_secret', '')[-4:]}")
    logger.info(f"Testnet: {keys.get('testnet')}")
