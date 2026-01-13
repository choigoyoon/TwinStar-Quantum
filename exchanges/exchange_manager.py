"""
통합 거래소 관리자 (v2)
"""

import ccxt
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

# [FIX] crypto_manager import (다중 경로 시도)
CRYPTO_MANAGER_AVAILABLE = False
try:
    from GUI.crypto_manager import load_api_keys, save_api_keys
    CRYPTO_MANAGER_AVAILABLE = True
except ImportError:
    try:
        from crypto_manager import load_api_keys, save_api_keys
        CRYPTO_MANAGER_AVAILABLE = True
    except ImportError as e:
        logging.warning(f"[ExchangeManager] crypto_manager 없음: {e}")

# [FIX] constants import (다중 경로 시도)
CONSTANTS_AVAILABLE = False
try:
    from GUI.constants import EXCHANGE_INFO, SPOT_EXCHANGES
    CONSTANTS_AVAILABLE = True
except ImportError:
    try:
        from constants import EXCHANGE_INFO, SPOT_EXCHANGES
        CONSTANTS_AVAILABLE = True
    except ImportError:
        EXCHANGE_INFO = {}
        SPOT_EXCHANGES = {'upbit', 'bithumb'}


# 지원 거래소 목록
SUPPORTED_EXCHANGES = {
    # 선물 거래소
    'bybit': {'type': 'futures', 'name': 'Bybit', 'testnet': True},
    'binance': {'type': 'futures', 'name': 'Binance Futures', 'testnet': True},
    'okx': {'type': 'futures', 'name': 'OKX', 'testnet': True},
    'bitget': {'type': 'futures', 'name': 'Bitget', 'testnet': False},
    'bingx': {'type': 'futures', 'name': 'BingX', 'testnet': False},
    
    # 현물 거래소 (한국) - 전용 라이브러리 사용
    'upbit': {'type': 'spot', 'name': '업비트', 'testnet': False, 'currency': 'KRW', 'native': True},
    'bithumb': {'type': 'spot', 'name': '빗썸', 'testnet': False, 'currency': 'KRW', 'native': True},
    
    # 현물 거래소 (글로벌)
    'binance_spot': {'type': 'spot', 'name': 'Binance Spot', 'testnet': True},
}


@dataclass
class ExchangeConfig:
    """거래소 설정"""
    name: str
    api_key: str
    api_secret: str
    testnet: bool = False
    passphrase: str = ""  # OKX 등


class ExchangeManager:
    """통합 거래소 관리자 (싱글톤)"""
    
    def __init__(self):
        self.exchanges: Dict[str, object] = {}  # 연결된 거래소 캐시
        self.configs: Dict[str, ExchangeConfig] = {}
        self._load_keys()
    
    def _load_keys(self):
        """암호화된 API 키 로드"""
        try:
            if CRYPTO_MANAGER_AVAILABLE:
                data = load_api_keys()
            else:
                # crypto_manager 없으면 빈 dict
                print("[ExchangeManager] crypto_manager 없음")
                data = {}
            
            for name, config in data.items():
                if name.startswith('_'):
                    continue
                if isinstance(config, dict) and config.get('api_key'):
                    self.configs[name] = ExchangeConfig(
                        name=name,
                        api_key=config.get('api_key', ''),
                        api_secret=config.get('api_secret', config.get('secret', '')), # [FIX] secret alias
                        testnet=config.get('testnet', False),
                        passphrase=config.get('password', config.get('passphrase', ''))
                    )
            
            print(f"[ExchangeManager] {len(self.configs)}개 거래소 키 로드됨")
            
        except Exception as e:
            print(f"[ExchangeManager] API 키 로드 오류: {e}")
    
    def _save_keys(self):
        """암호화된 API 키 저장"""
        data = {}
        for name, config in self.configs.items():
            data[name] = {
                'api_key': config.api_key,
                'api_secret': config.api_secret,
                'testnet': config.testnet,
                'password': config.passphrase
            }
        
        if CRYPTO_MANAGER_AVAILABLE:
            save_api_keys(data)
        else:
            print("[ExchangeManager] 저장 실패: crypto_manager 없음")
    
    def set_api_key(self, exchange_name: str, api_key: str, api_secret: str,
                    testnet: bool = False, passphrase: str = "") -> tuple:
        """API 키 설정 및 거래소 연결. Returns (success, error_msg)"""
        exchange_name = exchange_name.lower()
        
        if exchange_name not in SUPPORTED_EXCHANGES:
            return (False, f"지원하지 않는 거래소: {exchange_name}")
        
        # 설정 저장 (연결 성공 시에만 저장하도록 변경)
        temp_config = ExchangeConfig(
            name=exchange_name,
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
            passphrase=passphrase
        )
        
        # 거래소 연결 시도
        self.configs[exchange_name] = temp_config
        success, error = self._connect(exchange_name)
        
        if success:
            self._save_keys()  # 성공 시에만 저장
        else:
            del self.configs[exchange_name]  # 실패 시 설정 롤백
        
        return (success, error)
    
    def _connect(self, exchange_name: str) -> tuple:
        """거래소 연결 (캐싱). Returns (success, error_msg)"""
        if exchange_name not in self.configs:
            return (False, "설정되지 않은 거래소")
        
        # 이미 연결되어 있으면 재사용
        if exchange_name in self.exchanges:
            return (True, "")
        
        config = self.configs[exchange_name]
        info = SUPPORTED_EXCHANGES.get(exchange_name, {})

        # [DEBUG] Key Status Check
        masked_key = config.api_key[:4] + "***" if config.api_key else "None"
        has_secret = bool(config.api_secret)
        has_pass = bool(config.passphrase)
        print(f"[Connect] {exchange_name}: Key={masked_key}, Secret={'OK' if has_secret else 'MISSING'}, Pass={'OK' if has_pass else 'MISSING'}")
        
        try:
            # [NEW] 한국 거래소는 전용 라이브러리 사용
            if info.get('native'):
                return self._connect_native(exchange_name, config, info)
            
            # [FIX] Use Custom Adapter Classes
            exchange = None
            
            # Common config dictionary
            adapter_config = {
                'api_key': config.api_key,
                'api_secret': config.api_secret,
                'testnet': config.testnet,
                'passphrase': config.passphrase
            }
            
            if exchange_name == 'bybit':
                from exchanges.bybit_exchange import BybitExchange
                exchange = BybitExchange(adapter_config)
                
            elif exchange_name == 'binance':
                from exchanges.binance_exchange import BinanceExchange
                exchange = BinanceExchange(adapter_config)
                
            elif exchange_name == 'bitget':
                from exchanges.bitget_exchange import BitgetExchange
                exchange = BitgetExchange(adapter_config)
                
            elif exchange_name == 'okx':
                from exchanges.okx_exchange import OKXExchange
                exchange = OKXExchange(adapter_config)
                
            elif exchange_name == 'bingx':
                from exchanges.bingx_exchange import BingXExchange
                exchange = BingXExchange(adapter_config)
                
            else:
                 # Fallback to ccxt (should not happen for supported futures)
                exchange = exchange_class(options)
                exchange.load_markets()

            # Connect (Adapter classes usually connect in __init__ or have connect method)
            if hasattr(exchange, 'connect') and not getattr(exchange, 'is_connected', False):
                 exchange.connect()

            self.exchanges[exchange_name] = exchange
            
            print(f"✅ {info.get('name', exchange_name)} 연결 성공 (Adapter)")
            return (True, "")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ {exchange_name} 연결 실패: {error_msg}")
            return (False, error_msg)
    
    def _connect_native(self, exchange_name: str, config, info: dict) -> tuple:
        """한국 거래소 전용 연결 (pyupbit, pybithumb)"""
        try:
            if exchange_name == 'upbit':
                try:
                    import pyupbit
                    upbit = pyupbit.Upbit(config.api_key, config.api_secret)
                    # 연결 테스트 (잔고 조회)
                    balance = upbit.get_balance("KRW")
                    self.exchanges[exchange_name] = upbit
                    print(f"✅ 업비트 연결 성공 (잔고: {balance:,.0f}원)")
                    return (True, "")
                except ImportError:
                    return (False, "pyupbit 설치 필요: pip install pyupbit")
                    
            elif exchange_name == 'bithumb':
                try:
                    import pybithumb
                    bithumb = pybithumb.Bithumb(config.api_key, config.api_secret)
                    # 연결 테스트
                    balance = bithumb.get_balance("BTC")
                    self.exchanges[exchange_name] = bithumb
                    print(f"✅ 빗썸 연결 성공")
                    return (True, "")
                except ImportError:
                    # fallback to ccxt
                    exchange = ccxt.bithumb({
                        'apiKey': config.api_key,
                        'secret': config.api_secret,
                        'enableRateLimit': True,
                    })
                    exchange.load_markets()
                    self.exchanges[exchange_name] = exchange
                    print(f"✅ 빗썸 연결 성공 (ccxt)")
                    return (True, "")
                    
            return (False, f"지원하지 않는 네이티브 거래소: {exchange_name}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ {exchange_name} 연결 실패: {error_msg}")
            return (False, error_msg)
    
    def get_exchange(self, exchange_name: str) -> Optional[object]:
        """거래소 인스턴스 반환 (캐싱된 연결)"""
        exchange_name = exchange_name.lower()
        
        if exchange_name not in self.exchanges:
            if exchange_name in self.configs:
                self._connect(exchange_name)
        
        return self.exchanges.get(exchange_name)
    
    def get_all_connected(self) -> List[str]:
        """연결된 거래소 목록"""
        return list(self.exchanges.keys())
    
    def get_exchange_info(self, exchange_name: str) -> Dict:
        """거래소 정보"""
        return SUPPORTED_EXCHANGES.get(exchange_name.lower(), {})
    
    def test_connection(self, exchange_name: str) -> bool:
        """연결 테스트"""
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            return False
        
        try:
            # 한국 거래소는 네이티브 메서드 사용
            if exchange_name.lower() in ('upbit', 'bithumb'):
                if exchange_name.lower() == 'upbit':
                    balance = exchange.get_balance("KRW")
                else:
                    balance = exchange.get_balance("BTC")  # pybithumb
            else:
                balance = exchange.fetch_balance()
            print(f"✅ {exchange_name} 연결 확인됨")
            return True
        except Exception as e:
            print(f"❌ {exchange_name} 연결 테스트 실패: {e}")
            return False

    def get_positions(self, exchange_name: str) -> list:
        """거래소의 열린 포지션 목록 조회 (모든 어댑터 공통 규격)"""
        try:
            ex = self.get_exchange(exchange_name)
            if not ex: return []
            
            # 1. 어댑터 자체 get_positions가 있으면 우선 사용
            if hasattr(ex, 'get_positions'):
                pos_list = ex.get_positions()
                if pos_list:
                    normalized = []
                    for p in pos_list:
                        normalized.append({
                            'symbol': p.get('symbol', ''),
                            'side': p.get('side', 'Unknown'),
                            'size': float(p.get('size', 0)),
                            'entry': float(p.get('entry_price', p.get('entry', 0))),
                            'exchange': exchange_name
                        })
                    return normalized
            
            # 2. CCXT 기반 포지션 조회 (범용)
            if hasattr(ex, 'fetch_positions'):
                try:
                    raw_pos = ex.fetch_positions()
                    normalized = []
                    for p in raw_pos:
                        size = float(p.get('contracts', 0) or p.get('size', 0))
                        if size > 0:
                            normalized.append({
                                'symbol': p.get('symbol', ''),
                                'side': p.get('side', 'Unknown'),
                                'size': size,
                                'entry': float(p.get('entryPrice', 0)),
                                'exchange': exchange_name
                            })
                    return normalized
                except Exception as e:
                    logging.debug(f"[{exchange_name}] fetch_positions failed: {e}")

            return []
        except Exception as e:
            logging.error(f"[{exchange_name}] get_positions error: {e}")
            return []
    
    def get_balance(self, exchange_name: str, currency: str = None) -> float:
        """
        거래소 잔고 조회
        
        Args:
            exchange_name: 거래소명
            currency: 통화 (None=자동, 'USDT', 'KRW')
        
        Returns:
            잔고 (float)
        """
        try:
            ex = self.get_exchange(exchange_name)
            if not ex:
                return 0.0
            
            # KRW 거래소 판별
            is_krw = exchange_name.lower() in ['upbit', 'bithumb']
            
            # 통화 자동 선택
            if currency is None:
                currency = 'KRW' if is_krw else 'USDT'
            
            # [FIX] 한국 거래소는 네이티브 메서드 사용 (currency 인자 필요)
            if exchange_name.lower() == 'upbit':
                # pyupbit: get_balance("KRW") 형식
                return float(ex.get_balance(currency) or 0.0)
            elif exchange_name.lower() == 'bithumb':
                # pybithumb: get_balance("BTC") 형식 - KRW 잔고는 별도 처리
                if currency == 'KRW':
                    # pybithumb에서 KRW 잔고 조회 (KRW는 float로 반환될 수 있음)
                    try:
                        bal = ex.get_balance("KRW")
                        if isinstance(bal, tuple):
                            return float(bal[1]) if len(bal) >= 2 else 0.0
                        return float(bal or 0.0)
                    except Exception:

                        return 0.0
                else:
                    bal = ex.get_balance(currency)
                    if isinstance(bal, tuple) and len(bal) >= 2:
                        return float(bal[1])  # 사용가능
                    return float(bal) if bal else 0.0
            
            # [NEW] 어댑터별 잔고 데이터 확보
            if hasattr(ex, 'fetch_balance'):
                balance_data = ex.fetch_balance()
            elif hasattr(ex, 'get_balance'):
                balance_data = ex.get_balance()
            else:
                return 0.0

            
            # 잔고 추출 로직
            from utils.helpers import safe_float
            
            if isinstance(balance_data, dict):
                # 1. 'total' 또는 'free' 키가 있는 표준 ccxt 형식
                if currency in balance_data:
                    bal = balance_data[currency]
                    if isinstance(bal, dict):
                        return safe_float(bal.get('free', bal.get('total', 0)))
                    return safe_float(bal)
                
                # 2. total 계층 확인
                if 'total' in balance_data and isinstance(balance_data['total'], dict):
                    return safe_float(balance_data['total'].get(currency, 0))
                
                # 3. free 계층 확인
                if 'free' in balance_data and isinstance(balance_data['free'], dict):
                    return safe_float(balance_data['free'].get(currency, 0))
            
            # 4. dict가 아니거나 찾는 통화가 없는 경우 raw 값 반환 시도
            return safe_float(balance_data) if balance_data else 0.0
            
        except Exception as e:
            logging.error(f"[ExchangeManager] {exchange_name} 잔고 조회 실패: {e}")
            return 0.0

    def get_all_balances(self) -> dict:
        """모든 거래소 잔고 조회 (USDT + KRW 분리)"""
        result = {'usdt': 0.0, 'krw': 0.0, 'details': {}}
        
        # 해외 선물 (USDT)
        for name in ['bybit', 'binance', 'okx', 'bitget', 'bingx']:
            try:
                bal = self.get_balance(name, 'USDT')
                if bal > 0:
                    result['usdt'] += bal
                    if name not in result['details']: result['details'][name] = {}
                    result['details'][name]['USDT'] = bal
            except Exception:

                pass
        
        # 국내 현물 (KRW)
        for name in ['upbit', 'bithumb']:
            try:
                bal = self.get_balance(name, 'KRW')
                if bal > 0:
                    result['krw'] += bal
                    if name not in result['details']: result['details'][name] = {}
                    result['details'][name]['KRW'] = bal
            except Exception:

                pass
        
        return result
    
    def get_positions(self, exchange_name: str) -> List[dict]:
        """거래소 모든 포지션 조회"""
        try:
            ex = self.exchanges.get(exchange_name.lower())
            if not ex:
                # 연결 시도
                success, _ = self._connect(exchange_name)
                if success:
                    ex = self.exchanges.get(exchange_name.lower())
                else:
                    return []
            
            if hasattr(ex, 'get_positions'):
                return ex.get_positions()
            return []
        except Exception as e:
            logging.error(f"[ExchangeManager] {exchange_name} 포지션 조회 실패: {e}")
            return []

    def disconnect(self, exchange_name: str):
        """연결 해제"""
        if exchange_name in self.exchanges:
            del self.exchanges[exchange_name]
    
    def disconnect_all(self):
        """모든 연결 해제"""
        self.exchanges.clear()


# ============ 싱글톤 ============
_exchange_manager: Optional[ExchangeManager] = None

def get_exchange_manager() -> ExchangeManager:
    """ExchangeManager 싱글톤"""
    global _exchange_manager
    if _exchange_manager is None:
        _exchange_manager = ExchangeManager()
    return _exchange_manager


# ============ 편의 함수 ============
def connect_exchange(exchange_name: str, api_key: str, api_secret: str,
                     testnet: bool = False, passphrase: str = "") -> tuple:
    """거래소 연결 (단축). Returns (success, error_msg)"""
    em = get_exchange_manager()
    return em.set_api_key(exchange_name, api_key, api_secret, testnet, passphrase)


def get_exchange(exchange_name: str):
    """거래소 가져오기 (단축)"""
    em = get_exchange_manager()
    return em.get_exchange(exchange_name)


def test_connection(exchange_name: str, api_key: str = None, api_secret: str = None,
                    testnet: bool = False) -> bool:
    """연결 테스트 (단축)"""
    em = get_exchange_manager()
    
    # 새 키가 제공되면 임시 연결
    if api_key and api_secret:
        result = em.set_api_key(exchange_name, api_key, api_secret, testnet)
        # [FIX] set_api_key returns tuple (bool, str), extract bool
        return result[0] if isinstance(result, tuple) else result
    
    return em.test_connection(exchange_name)


# ============ 테스트 ============
if __name__ == "__main__":
    print("=== Exchange Manager v2 ===")
    print(f"Crypto Manager: {CRYPTO_MANAGER_AVAILABLE}")
    print(f"Constants: {CONSTANTS_AVAILABLE}")
    
    em = get_exchange_manager()
    
    print(f"\n로드된 거래소: {list(em.configs.keys())}")
    
    # 연결 테스트
    for name in em.configs:
        print(f"\n{name} 연결 테스트...")
        if em.test_connection(name):
            print(f"  잔고: ${em.get_balance(name, 'USDT'):,.2f}")
