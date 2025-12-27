# license_manager.py
"""
TwinStar Quantum 라이선스 관리
"""

import requests
import hashlib
import uuid
import platform
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# ========== 경로 설정 (EXE 호환) ==========
def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent

try:
    from paths import Paths
    CONFIG_PATH = Path(Paths.CONFIG)
except ImportError:
    CONFIG_PATH = get_base_path() / "config"

CONFIG_PATH.mkdir(parents=True, exist_ok=True)

# ========== 설정 ==========
API_URL = "https://youngstreet.co.kr/membership/api_license.php"
CACHE_FILE = CONFIG_PATH / "license_cache.json"
REQUEST_TIMEOUT = 10

# ========== 등급 정책 (PHP와 일치) ==========
DEFAULT_LIMITS = {
    'TRIAL': {'exchanges': 1, 'coins': ['BTC'], 'positions': 1, 'days': 7},
    'BASIC': {'exchanges': 2, 'coins': ['BTC'], 'positions': 1},
    'STANDARD': {'exchanges': 3, 'coins': ['BTC', 'ETH'], 'positions': 2},
    'PREMIUM': {'exchanges': 10, 'coins': ['ALL'], 'positions': 10},  # [v1.1.1] 전체 코인 허용
    'ADMIN': {'exchanges': 999, 'coins': ['ALL'], 'positions': 999}
}

# ========== 가격 정책 (라이센스 + 서버비 포함) ==========
PRICING = {
    'BASIC': {'1': 110, '3': 300, '6': 570, '12': 1080},
    'STANDARD': {'1': 210, '3': 570, '6': 1080, '12': 2040},
    'PREMIUM': {'1': 410, '3': 1110, '6': 2100, '12': 3960}
}

# 가격 구성
LICENSE_FEE = {
    'BASIC': 100,
    'STANDARD': 200,
    'PREMIUM': 400
}
SERVER_FEE = 10  # $10/월

# 할인율
DISCOUNTS = {
    '1': 0,
    '3': 0.10,   # 10%
    '6': 0.15,   # 15%
    '12': 0.20   # 20%
}

# 결제 안내
PAYMENT_NOTICE = "※ 오버입금 시 환불 불가. 초과 금액은 서버비로 충당됩니다."


def get_monthly_price(tier: str) -> float:
    """월 구독료 반환 (서버비 포함)"""
    base = LICENSE_FEE.get(tier, 0)
    return base + SERVER_FEE


def get_period_price(tier: str, months: int) -> float:
    """기간별 가격 반환 (할인 적용)"""
    monthly = get_monthly_price(tier)
    discount = DISCOUNTS.get(str(months), 0)
    total = monthly * months * (1 - discount)
    return total


def get_price_display(tier: str) -> dict:
    """가격 표시용 데이터 반환"""
    return {
        'tier': tier,
        'license_fee': LICENSE_FEE.get(tier, 0),
        'server_fee': SERVER_FEE,
        'monthly_total': get_monthly_price(tier),
        'prices': PRICING.get(tier, {}),
        'discounts': DISCOUNTS,
        'notice': PAYMENT_NOTICE
    }


class LicenseManager:
    """라이선스 관리 싱글톤"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # PC 정보
        self.hw_id = self._generate_hw_id()
        self.mac = self._get_mac()
        
        # 라이선스 상태
        self.email: Optional[str] = None
        self.tier: str = 'TRIAL'
        self.expires_at: Optional[str] = None
        self.days_left: int = 0
        self.limits: Dict = DEFAULT_LIMITS.get('TRIAL', {})
        
        # 서버 데이터
        self.prices: Dict = {}
        self.wallets: Dict = {}
        
        # 캐시 로드
        self._load_cache()
        
        logging.info(f"[LICENSE] 초기화: hw_id={self.hw_id[:8]}..., tier={self.tier}")
    
    # ========== PC ID 생성 ==========
    
    def _generate_hw_id(self) -> str:
        """PC 고유 ID 생성 (MAC + 머신명 해시)"""
        try:
            mac = uuid.getnode()
            machine = platform.node()
            system = platform.system()
            raw = f"{mac}-{machine}-{system}"
            return hashlib.sha256(raw.encode()).hexdigest()[:32]
        except Exception as e:
            logging.error(f"[LICENSE] hw_id 생성 오류: {e}")
            return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]
    
    def _get_mac(self) -> str:
        """MAC 주소 반환"""
        try:
            mac = uuid.getnode()
            return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        except Exception:
            return "00:00:00:00:00:00"
    
    # ========== 캐시 관리 ==========
    
    def _load_cache(self):
        """로컬 캐시 로드"""
        try:
            if CACHE_FILE.exists():
                data = json.loads(CACHE_FILE.read_text(encoding='utf-8'))
                self.email = data.get('email')
                self.tier = data.get('tier', 'TRIAL')
                self.expires_at = data.get('expires_at')
                self.days_left = data.get('days_left', 0)
                self.limits = data.get('limits', DEFAULT_LIMITS.get(self.tier, {}))
                logging.info(f"[LICENSE] 캐시 로드: {self.tier}, {self.days_left}일 남음")
        except Exception as e:
            logging.error(f"[LICENSE] 캐시 로드 오류: {e}")
    
    def _save_cache(self):
        """로컬 캐시 저장"""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'email': self.email,
                'tier': self.tier,
                'expires_at': self.expires_at,
                'days_left': self.days_left,
                'limits': self.limits,
                'hw_id': self.hw_id,
                'updated_at': datetime.now().isoformat()
            }
            CACHE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            logging.error(f"[LICENSE] 캐시 저장 오류: {e}")
    
    # ========== API 호출 ==========
    
    def check(self, email: str = None, password: str = None) -> Dict:
        """라이선스 확인"""
        check_email = email or self.email
        
        if not check_email:
            return {'success': False, 'error': '이메일 필요'}
        
        try:
            payload = {
                'action': 'check',
                'email': check_email,
                'hw_id': self.hw_id
            }
            if password:
                payload['password'] = password
            
            resp = requests.post(API_URL, data=payload, timeout=REQUEST_TIMEOUT)
            data = resp.json()
            
            if data.get('success') and data.get('valid'):
                self.email = check_email
                self.tier = data.get('tier', 'TRIAL').upper()
                self.expires_at = data.get('expires')
                self.days_left = data.get('days_left', 0)
                self.limits = data.get('limits', DEFAULT_LIMITS.get(self.tier, {}))
                self._save_cache()
                
                logging.info(f"[LICENSE] 서버 확인: {self.tier}, {self.days_left}일")
                return {
                    'success': True,
                    'tier': self.tier,
                    'days_left': self.days_left,
                    'limits': self.limits,
                    'is_admin': data.get('is_admin', False)
                }
            else:
                return {
                    'success': False,
                    'error': data.get('error', data.get('message', '확인 실패')),
                    'action_required': data.get('action_required')
                }
                
        except requests.exceptions.RequestException as e:
            logging.warning(f"[LICENSE] 서버 연결 실패: {e}, 캐시 사용")
            return {
                'success': True,
                'tier': self.tier,
                'days_left': self.days_left,
                'limits': self.limits,
                'cached': True
            }
        except Exception as e:
            logging.error(f"[LICENSE] check 오류: {e}")
            return {'success': False, 'error': str(e)}
    
    def register(self, name: str, email: str, phone: str = '') -> Dict:
        """신규 등록 (7일 체험)"""
        if not name or not email:
            return {'success': False, 'error': '이름과 이메일 필요'}
        
        try:
            resp = requests.post(API_URL, data={
                'action': 'register',
                'name': name,
                'email': email,
                'phone': phone,
                'hw_id': self.hw_id,
                'mac': self.mac
            }, timeout=REQUEST_TIMEOUT)
            
            data = resp.json()
            
            if data.get('success'):
                self.email = email
                self.tier = 'TRIAL'
                self.expires_at = data.get('expires')
                self.days_left = data.get('days_left', 7)
                self.limits = DEFAULT_LIMITS.get('TRIAL', {})
                self._save_cache()
                
                logging.info(f"[LICENSE] 등록 완료: {email}, 7일 체험 시작")
                return {
                    'success': True,
                    'message': '7일 체험판 시작!',
                    'tier': 'TRIAL',
                    'days_left': 7
                }
            else:
                return {
                    'success': False,
                    'error': data.get('error', data.get('message', '등록 실패'))
                }
                
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'서버 연결 실패: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def activate(self) -> Dict:
        """PC 바인딩 활성화"""
        if not self.email:
            return {'success': False, 'error': '이메일 필요'}
        
        try:
            resp = requests.post(API_URL, data={
                'action': 'activate',
                'email': self.email,
                'hw_id': self.hw_id,
                'mac': self.mac
            }, timeout=REQUEST_TIMEOUT)
            
            data = resp.json()
            
            if data.get('success'):
                self.tier = data.get('tier', 'TRIAL').upper()
                self.expires_at = data.get('expires')
                self.limits = data.get('limits', DEFAULT_LIMITS.get(self.tier, {}))
                self._save_cache()
                
                logging.info(f"[LICENSE] 활성화 완료: {self.tier}")
                return {
                    'success': True,
                    'tier': self.tier,
                    'expires': self.expires_at
                }
            else:
                return {
                    'success': False,
                    'error': data.get('error', '활성화 실패')
                }
                
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'서버 연결 실패: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def submit_payment(self, tx_hash: str, tier: str, months: int = 1, crypto: str = 'USDT_TRC20') -> Dict:
        """입금 신청"""
        if not self.email:
            return {'success': False, 'error': '먼저 가입 필요'}
        
        if not tx_hash:
            return {'success': False, 'error': 'TX Hash 필요'}
        
        # 예상 금액 계산
        expected_amount = PRICING.get(tier.upper(), {}).get(str(months), 0)
        
        try:
            resp = requests.post(API_URL, data={
                'action': 'payment',
                'email': self.email,
                'tx_hash': tx_hash,
                'tier': tier.upper(),
                'months': months,
                'crypto': crypto,
                'amount': expected_amount
            }, timeout=REQUEST_TIMEOUT)
            
            data = resp.json()
            
            if data.get('success'):
                logging.info(f"[LICENSE] 입금 신청 완료: {tier}, {months}개월")
                return {
                    'success': True,
                    'message': '입금 신청 완료. 관리자 확인 후 활성화됩니다.',
                    'payment_id': data.get('payment_id'),
                    'notice': data.get('notice', PAYMENT_NOTICE)
                }
            else:
                return {
                    'success': False,
                    'error': data.get('error', data.get('message', '입금 신청 실패'))
                }
                
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'서버 연결 실패: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def fetch_limits(self, tier: str = None) -> Dict:
        """등급별 제한 정책 조회"""
        try:
            params = {'action': 'limits'}
            if tier:
                params['tier'] = tier.upper()
            
            resp = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
            data = resp.json()
            
            if data.get('success'):
                if tier:
                    return data.get('limits', {})
                else:
                    return data.get('all_limits', DEFAULT_LIMITS)
            
            return DEFAULT_LIMITS
            
        except Exception as e:
            logging.error(f"[LICENSE] limits 조회 오류: {e}")
            return DEFAULT_LIMITS
    
    def fetch_prices(self) -> Dict:
        """가격표 조회"""
        try:
            resp = requests.get(API_URL, params={'action': 'prices'}, timeout=REQUEST_TIMEOUT)
            data = resp.json()
            
            if data.get('success'):
                self.prices = data.get('prices', {})
                return {
                    'success': True,
                    'prices': self.prices,
                    'breakdown': data.get('breakdown', {}),
                    'server_fee': data.get('server_fee', SERVER_FEE),
                    'currency': data.get('currency', 'USDT'),
                    'discounts': data.get('discounts', DISCOUNTS),
                    'notice': data.get('notice', PAYMENT_NOTICE)
                }
            
            # 서버 실패 시 로컬 데이터 반환
            return {
                'success': True,
                'prices': PRICING,
                'server_fee': SERVER_FEE,
                'currency': 'USDT',
                'cached': True
            }
            
        except Exception as e:
            logging.error(f"[LICENSE] prices 조회 오류: {e}")
            return {
                'success': True,
                'prices': PRICING,
                'server_fee': SERVER_FEE,
                'currency': 'USDT',
                'cached': True
            }
    
    def fetch_wallet(self, crypto: str = 'USDT_TRC20') -> str:
        """지갑 주소 조회"""
        try:
            resp = requests.get(API_URL, params={
                'action': 'wallet',
                'crypto': crypto.upper()
            }, timeout=REQUEST_TIMEOUT)
            
            data = resp.json()
            
            if data.get('success'):
                wallet = data.get('wallet', '')
                if wallet:
                    self.wallets[crypto] = wallet
                return wallet
            
            return ''
            
        except Exception as e:
            logging.error(f"[LICENSE] wallet 조회 오류: {e}")
            # [FIX] 하드코딩된 기본 지갑 주소 반환 (서버 실패 대비)
            if crypto.upper() == 'USDT_TRC20':
                return 'TPEzvE85juFiQLhmBACbFNJgUWTtv7TCk3'
            return ''
    
    def fetch_all_wallets(self) -> Dict:
        """모든 지갑 주소 조회"""
        try:
            resp = requests.get(API_URL, params={'action': 'wallet'}, timeout=REQUEST_TIMEOUT)
            data = resp.json()
            
            if data.get('success'):
                self.wallets = data.get('wallets', {})
                return self.wallets
            
            return {}
            
        except Exception as e:
            logging.error(f"[LICENSE] wallets 조회 오류: {e}")
            return {}
    
    # ========== Public API ==========
    
    def get_tier(self) -> str:
        """현재 등급 반환"""
        if self.days_left <= 0 and self.tier not in ['PREMIUM', 'ADMIN']:
            return 'EXPIRED'
        return self.tier.upper()
    
    def get_limits(self) -> Dict:
        """현재 등급 제한 반환"""
        tier = self.get_tier()
        if tier == 'EXPIRED':
            return DEFAULT_LIMITS.get('TRIAL', {})
        return self.limits or DEFAULT_LIMITS.get(tier, {})
    
    def get_max_exchanges(self) -> int:
        """최대 거래소 수"""
        return self.get_limits().get('exchanges', 1)
    
    def get_max_positions(self) -> int:
        """최대 포지션 수"""
        return self.get_limits().get('positions', 1)
    
    def get_allowed_coins(self) -> List[str]:
        """허용 코인 목록"""
        return self.get_limits().get('coins', ['BTC'])
    
    def is_coin_allowed(self, symbol: str) -> bool:
        """코인 허용 여부"""
        allowed = self.get_allowed_coins()
        
        # ALL 허용 (PREMIUM, ADMIN)
        if 'ALL' in allowed:
            return True
            
        clean = symbol.replace('USDT', '').replace('KRW-', '').replace('-USDT', '').upper()
        return clean in allowed
    
    def is_exchange_allowed(self, count: int) -> bool:
        """거래소 수 허용 여부"""
        return count <= self.get_max_exchanges()
    
    def is_position_allowed(self, count: int) -> bool:
        """포지션 수 허용 여부"""
        return count <= self.get_max_positions()
    
    def is_valid(self) -> bool:
        """라이선스 유효 여부"""
        return self.days_left > 0 or self.tier in ['PREMIUM', 'ADMIN']
    
    def is_registered(self) -> bool:
        """가입 여부"""
        return self.email is not None
    
    def get_days_left(self) -> int:
        """남은 일수"""
        if self.tier in ['PREMIUM', 'ADMIN']:
            return 99999
        return max(0, self.days_left)
    
    def get_email(self) -> Optional[str]:
        """등록된 이메일"""
        return self.email
    
    def get_hw_id(self) -> str:
        """PC ID"""
        return self.hw_id

    def is_admin(self) -> bool:
        """관리자 여부"""
        return self.tier == 'ADMIN' or self.email == 'Hakiosae@gmail.com'
    
    def refresh(self) -> bool:
        """서버에서 최신 정보 갱신 (로컬 캐시 먼저 재로드)"""
        self._load_cache()  # [NEW] 로컬 파일 변경사항 먼저 반영
        if self.email:
            result = self.check(self.email)
            return result.get('success', False)
        return False
    
    def get_payment_notice(self) -> str:
        """결제 안내 문구"""
        return PAYMENT_NOTICE
    
    def get_pricing_info(self) -> Dict:
        """가격 정보 전체 반환"""
        return {
            'pricing': PRICING,
            'license_fee': LICENSE_FEE,
            'server_fee': SERVER_FEE,
            'discounts': DISCOUNTS,
            'notice': PAYMENT_NOTICE
        }


# ========== 싱글톤 접근 ==========

_license_manager: Optional[LicenseManager] = None

def get_license_manager() -> LicenseManager:
    """LicenseManager 싱글톤 반환"""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


# ========== 테스트 ==========

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("LicenseManager 테스트")
    print("=" * 50)
    
    lm = get_license_manager()
    
    print(f"\n[INFO] PC ID: {lm.get_hw_id()}")
    print(f"[INFO] MAC: {lm.mac}")
    print(f"[INFO] 현재 등급: {lm.get_tier()}")
    print(f"[INFO] 남은 일수: {lm.get_days_left()}")
    print(f"[INFO] 제한: {lm.get_limits()}")
    
    # 가격 정보
    print("\n[INFO] 가격 정책:")
    for tier in ['BASIC', 'STANDARD', 'PREMIUM']:
        info = get_price_display(tier)
        print(f"  {tier}: ${info['monthly_total']}/월 (라이센스 ${info['license_fee']} + 서버 ${info['server_fee']})")
    
    # API 테스트
    print("\n[TEST] limits API...")
    limits = lm.fetch_limits()
    print(f"  결과: {list(limits.keys())}")
    
    print("\n[TEST] prices API...")
    prices = lm.fetch_prices()
    print(f"  결과: {prices.get('success')}, notice: {prices.get('notice', '')[:30]}...")
    
    print("\n[TEST] wallet API...")
    wallet = lm.fetch_wallet('USDT_TRC20')
    print(f"  결과: {wallet[:20]}..." if wallet else "  결과: (없음)")
    
    print(f"\n[INFO] 결제 안내: {lm.get_payment_notice()}")
    
    print("\n" + "=" * 50)
    print("테스트 완료")