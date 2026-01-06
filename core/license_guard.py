"""
license_guard.py - 라이센스 보안 및 서버 연결 관리

기능:
- 서버 상태 확인 (장애 vs 고의 차단 구분)
- 토큰 발급/갱신
- 암호화된 파라미터 관리
- 유예 모드 관리
"""

import requests
import time
import json
import base64
import hashlib
import uuid

# Logging
import logging
logger = logging.getLogger(__name__)

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.info("⚠️ pycryptodome 없음 - pip install pycryptodome")

# 설정 (난독화)
# API URL은 base64 인코딩으로 분산 저장
_U = ['YUhSMGNITTZMeTk1YjNWdVoz', 'TjBjbVZsZEM1amJ5NXJjaTl0', 'WlcxaVpYSnphR2x3TDJGd2FW', 'OXNhV05sYm5ObExuQm9jQT09']
BACKUP_SERVERS = [
    "https://youngstreet.co.kr/membership/ping.php",
]
DECRYPT_KEY = b'YOUR_SECRET_KEY_32_BYTES_LONG!!'  # 서버와 동일 (32바이트)

def _get_api_url():
    """난독화된 URL 복호화"""
    import base64
    encoded = ''.join(_U)
    return base64.b64decode(base64.b64decode(encoded)).decode()


def get_hardware_id():
    """PC 고유 ID 생성"""
    mac = uuid.getnode()
    return hashlib.md5(str(mac).encode()).hexdigest()


class LicenseGuard:
    """라이센스 검증 및 서버 연결 관리"""
    
    def __init__(self):
        self.token = None
        self.email = None
        self.hw_id = get_hardware_id()
        self.tier = 'free'
        self.days_left = 0
        self.name = ''
        
        # 암호화된 파라미터
        self.encrypted_params = None
        self.decrypted_params = None
        self.params_expires = 0
        
        # 유예 모드
        self.grace_mode = False
        self.grace_until = 0
        self.last_valid_params = None  # 유예 시 사용할 백업
    
    # ==================== 서버 상태 확인 ====================
    
    def check_server_status(self) -> dict:
        """
        서버 상태 확인 - 장애 vs 고의 차단 구분
        
        Returns:
            {
                'status': 'ok' | 'server_issue' | 'internet_issue' | 'blocked',
                'message': str,
                'allow_trading': bool,
                'grace_hours': int (유예 시간)
            }
        """
        # 1. 인터넷 연결 확인
        internet_ok = self._check_internet()
        
        if not internet_ok:
            return {
                'status': 'internet_issue',
                'message': '인터넷 연결 확인 필요',
                'allow_trading': True,
                'grace_hours': 6
            }
        
        # 2. 우리 서버 확인
        our_server_ok = self._check_our_servers()
        
        if our_server_ok >= 1:
            return {
                'status': 'ok',
                'message': '서버 정상',
                'allow_trading': True,
                'grace_hours': 0
            }
        
        # 3. 인터넷 되는데 우리 서버만 안 됨
        # 추가 확인: 잠시 후 재시도
        time.sleep(2)
        our_server_ok_retry = self._check_our_servers()
        
        if our_server_ok_retry >= 1:
            return {
                'status': 'ok',
                'message': '서버 정상 (재시도 성공)',
                'allow_trading': True,
                'grace_hours': 0
            }
        
        # 서버 장애인지 고의 차단인지 구분 어려움 → 일단 유예
        return {
            'status': 'server_issue',
            'message': '서버 연결 불가 - 유예 모드',
            'allow_trading': True,
            'grace_hours': 6
        }
    
    def _check_internet(self) -> bool:
        """외부 사이트로 인터넷 연결 확인"""
        test_urls = [
            "https://www.google.com",
            "https://www.cloudflare.com",
            "https://www.microsoft.com"
        ]
        
        for url in test_urls:
            try:
                r = requests.head(url, timeout=5)
                if r.status_code < 400:
                    return True
            except requests.RequestException as e:
                logging.debug(f"Internet check failed for {url}: {e}") # Changed from continue
                continue # Keep trying other URLs
        
        return False
    
    def _check_our_servers(self) -> int:
        """우리 서버 연결 확인, 성공 개수 반환"""
        servers = [_get_api_url() + "?action=ping"] + BACKUP_SERVERS
        success_count = 0
        
        for url in servers:
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    try:
                        data = r.json()
                        if data.get('status') == 'ok':
                            success_count += 1
                    except (ValueError, KeyError):
                        # JSON 아니어도 200이면 성공
                        success_count += 1
            except requests.RequestException as e:
                logging.debug(f"Our server check failed for {url}: {e}")
                continue # Keep trying other servers
        
        return success_count
    
    # ==================== 인증 ====================
    
    def login(self, email: str) -> dict:
        """
        로그인 및 라이센스 확인
        
        Returns:
            {'success': bool, 'tier': str, 'days_left': int, 'error': str}
        """
        self.email = email
        
        try:
            response = requests.post(_get_api_url(), data={
                'action': 'check',
                'email': email,
                'hw_id': self.hw_id
            }, timeout=10)
            
            result = response.json()
            
            if result.get('success') and result.get('valid'):
                self.tier = result.get('tier', 'free')
                self.days_left = result.get('days_left', 0)
                self.name = result.get('name', '')
                
                return {
                    'success': True,
                    'name': self.name,
                    'tier': self.tier,
                    'days_left': self.days_left,
                    'expires': result.get('expires')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', '인증 실패'),
                    'action_required': result.get('action_required')
                }
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '서버 응답 시간 초과'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': '서버 연결 실패'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ==================== 토큰 관리 ====================
    
    def get_token(self) -> dict:
        """서버에서 토큰 발급"""
        if not self.email:
            return {'success': False, 'error': '로그인 필요'}
        
        try:
            response = requests.post(_get_api_url(), data={
                'action': 'get_token',
                'email': self.email,
                'hw_id': self.hw_id
            }, timeout=10)
            
            result = response.json()
            
            if result.get('success'):
                self.token = result.get('token')
                self.tier = result.get('tier', self.tier)
                self.days_left = result.get('days_left', 0)
                
                return {
                    'success': True,
                    'token': self.token,
                    'tier': self.tier,
                    'days_left': self.days_left
                }
            else:
                return {'success': False, 'error': result.get('error')}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def refresh_token(self) -> bool:
        """토큰 갱신"""
        if not self.token:
            return False
        
        try:
            response = requests.post(_get_api_url(), data={
                'action': 'refresh_token',
                'token': self.token
            }, timeout=10)
            
            result = response.json()
            
            if result.get('success'):
                self.token = result.get('token', self.token)
                return True
                
        except requests.RequestException as e:
            logging.debug(f"Token refresh failed: {e}")
        
        return False
    
    # ==================== 암호화된 파라미터 ====================
    
    def get_encrypted_params(self) -> dict:
        """서버에서 암호화된 파라미터 받기"""
        if not self.token:
            # 토큰 없으면 먼저 발급
            token_result = self.get_token()
            if not token_result.get('success'):
                return token_result
        
        try:
            response = requests.post(_get_api_url(), data={
                'action': 'get_encrypted_params',
                'token': self.token,
                'hw_id': self.hw_id
            }, timeout=10)
            
            result = response.json()
            
            if result.get('success'):
                self.encrypted_params = result.get('encrypted_params')
                
                if self.encrypted_params:
                    self.decrypted_params = self._decrypt_params(self.encrypted_params)
                else:
                    # 암호화 없이 직접 파라미터 받은 경우
                    self.decrypted_params = result.get('params', {})
                
                self.params_expires = time.time() + result.get('expires_in', 3600)
                
                # 유효한 파라미터 백업 (유예 모드용)
                if self.decrypted_params:
                    self.last_valid_params = self.decrypted_params.copy()
                
                return {
                    'success': True,
                    'params': self.decrypted_params,
                    'expires_in': result.get('expires_in', 3600)
                }
            else:
                return {'success': False, 'error': result.get('error')}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _decrypt_params(self, encrypted: str) -> dict:
        """암호화된 파라미터 복호화"""
        if not HAS_CRYPTO:
            logger.info("⚠️ 복호화 라이브러리 없음")
            return None
        
        try:
            data = base64.b64decode(encrypted)
            iv = data[:16]
            encrypted_data = data[16:]
            
            cipher = AES.new(DECRYPT_KEY, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(encrypted_data), AES.block_size)
            
            params = json.loads(decrypted.decode('utf-8'))
            
            # 만료 시간 체크
            if params.get('expires', 0) < time.time():
                logger.info("⚠️ 파라미터 만료됨")
                return None
            
            # HW ID 체크
            if params.get('hw_id') and params.get('hw_id') != self.hw_id:
                logger.info("⚠️ PC 불일치")
                return None
            
            return params
            
        except Exception as e:
            logger.info(f"복호화 실패: {e}")
            return None
    
    def get_params(self) -> dict:
        """현재 유효한 파라미터 반환"""
        # 1. 유효한 파라미터 있으면 반환
        if self.decrypted_params and time.time() < self.params_expires:
            return self.decrypted_params
        
        # 2. 유예 모드면 백업 파라미터 반환
        if self.is_in_grace() and self.last_valid_params:
            return self.last_valid_params
        
        # 3. 없음
        return None
    
    def is_params_valid(self) -> bool:
        """파라미터 유효성 체크"""
        if self.decrypted_params and time.time() < self.params_expires:
            return True
        
        if self.is_in_grace() and self.last_valid_params:
            return True
        
        return False
    
    # ==================== 유예 모드 ====================
    
    def enter_grace_mode(self, hours: int = 6):
        """유예 모드 진입 (서버 장애 시)"""
        self.grace_mode = True
        self.grace_until = time.time() + (hours * 3600)
        logger.warning(f"⚠️ 유예 모드 진입 ({hours}시간)")
    
    def exit_grace_mode(self):
        """유예 모드 종료"""
        self.grace_mode = False
        self.grace_until = 0
    
    def is_in_grace(self) -> bool:
        """유예 모드 중인지 확인"""
        if not self.grace_mode:
            return False
        
        if time.time() > self.grace_until:
            self.grace_mode = False
            return False
        
        return True
    
    def get_grace_remaining(self) -> int:
        """유예 남은 시간 (초)"""
        if not self.is_in_grace():
            return 0
        
        return max(0, int(self.grace_until - time.time()))
    
    def get_grace_remaining_str(self) -> str:
        """유예 남은 시간 (문자열)"""
        seconds = self.get_grace_remaining()
        if seconds <= 0:
            return "0분"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}시간 {minutes}분"
        return f"{minutes}분"
    
    # ==================== 업그레이드 ====================
    
    def create_upgrade_session(self) -> dict:
        """업그레이드 세션 생성"""
        if not self.email:
            return {'success': False, 'error': '로그인 필요'}
        
        try:
            response = requests.post(_get_api_url(), data={
                'action': 'create_upgrade_session',
                'email': self.email,
                'hw_id': self.hw_id
            }, timeout=10)
            
            result = response.json()
            
            if result.get('success'):
                session_id = result.get('session_id')
                return {
                    'success': True,
                    'session_id': session_id,
                    'url': f"https://youngstreet.co.kr/membership/upgrade.php?sid={session_id}"
                }
            else:
                return {'success': False, 'error': result.get('error')}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ==================== 매매 가능 여부 ====================
    
    def can_trade(self) -> dict:
        """
        매매 가능 여부 확인
        
        Returns:
            {
                'can_trade': bool,
                'reason': str,
                'tier': str,
                'grace_mode': bool
            }
        """
        # 1. Free 등급 체크
        if self.tier == 'free':
            if self.days_left <= 0:
                return {
                    'can_trade': False,
                    'reason': '무료 체험 만료',
                    'tier': self.tier,
                    'grace_mode': False
                }
        
        # 2. 유예 모드 체크
        if self.is_in_grace():
            return {
                'can_trade': True,
                'reason': f'유예 모드 ({self.get_grace_remaining_str()} 남음)',
                'tier': self.tier,
                'grace_mode': True
            }
        
        # 3. 정상
        return {
            'can_trade': True,
            'reason': '정상',
            'tier': self.tier,
            'grace_mode': False
        }
    
    # ==================== 등급별 제한 ====================
    
    def get_tier_limits(self) -> dict:
        """현재 등급의 제한 사항"""
        limits = {
            'free': {'exchanges': 1, 'symbols': 1, 'trial': True},
            'basic': {'exchanges': 1, 'symbols': 1, 'trial': False},
            'standard': {'exchanges': 2, 'symbols': 3, 'must_include': ['BTCUSDT'], 'trial': False},
            'premium': {'exchanges': 10, 'symbols': 50, 'trial': False},
            'admin': {'exchanges': 9999, 'symbols': 9999, 'trial': False}
        }
        
        return limits.get(self.tier, limits['free'])
    
    def check_symbol_limit(self, symbols: list) -> dict:
        """심볼 개수 제한 체크"""
        limits = self.get_tier_limits()
        max_symbols = limits.get('symbols', 1)
        
        if len(symbols) > max_symbols:
            return {
                'allowed': False,
                'reason': f'{self.tier} 등급은 최대 {max_symbols}개 코인',
                'max': max_symbols,
                'current': len(symbols)
            }
        
        # Standard는 BTC 필수
        must_include = limits.get('must_include', [])
        for required in must_include:
            if required not in symbols:
                return {
                    'allowed': False,
                    'reason': f'{required} 필수 포함',
                    'max': max_symbols,
                    'current': len(symbols)
                }
        
        return {'allowed': True}
    
    def check_exchange_limit(self, exchanges: list) -> dict:
        """거래소 개수 제한 체크"""
        limits = self.get_tier_limits()
        max_exchanges = limits.get('exchanges', 1)
        
        if len(exchanges) > max_exchanges:
            return {
                'allowed': False,
                'reason': f'{self.tier} 등급은 최대 {max_exchanges}개 거래소',
                'max': max_exchanges,
                'current': len(exchanges)
            }
        
        return {'allowed': True}
    
    # ==================== 상태 정보 ====================
    
    def get_status_info(self) -> dict:
        """현재 상태 정보 반환"""
        return {
            'email': self.email,
            'name': self.name,
            'tier': self.tier,
            'days_left': self.days_left,
            'has_token': bool(self.token),
            'params_valid': self.is_params_valid(),
            'grace_mode': self.is_in_grace(),
            'grace_remaining': self.get_grace_remaining_str() if self.is_in_grace() else None
        }
    
    # ==================== 멀티코인 스나이퍼 권한 ====================
    
    def can_use_sniper(self) -> bool:
        """멀티코인 스나이퍼 사용 가능 여부"""
        return self.tier.lower() in ["premium", "admin"]
    
    def get_sniper_limits(self) -> dict:
        """스나이퍼 제한 설정"""
        limits = {
            "free": {
                "enabled": False,
                "max_coins": 0,
                "max_positions": 0
            },
            "basic": {
                "enabled": False,
                "max_coins": 0,
                "max_positions": 0
            },
            "standard": {
                "enabled": False,
                "max_coins": 0,
                "max_positions": 0
            },
            "premium": {
                "enabled": True,
                "max_coins": 50,
                "max_positions": 20
            },
            "admin": {
                "enabled": True,
                "max_coins": 999,
                "max_positions": 9999
            }
        }
        
        return limits.get(self.tier.lower(), limits["free"])
    
    def get_current_tier(self) -> str:
        """현재 등급 반환 (호환용)"""
        return self.tier


    def record_payment(self, user_id: int, amount_usd: float, crypto_type: str, tx_hash: str) -> int:
        """결제 기록 전송 (서버)"""
        try:
            response = requests.post(_get_api_url(), data={
                'action': 'record_payment',
                'user_id': user_id,
                'amount': amount_usd,
                'crypto': crypto_type,
                'tx_hash': tx_hash,
                'hw_id': self.hw_id
            }, timeout=10)
            
            result = response.json()
            if result.get('success'):
                return result.get('payment_id', 0)
            return 0
        except Exception:
            return 0


# ==================== 싱글톤 ====================

_guard_instance = None

def get_license_guard() -> LicenseGuard:
    """싱글톤 인스턴스 반환"""
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = LicenseGuard()
    return _guard_instance


# ==================== 테스트 ====================

if __name__ == "__main__":
    guard = get_license_guard()
    
    logger.info(f"Hardware ID: {guard.hw_id}")
    logger.info(f"Server status: {guard.check_server_status()}")
