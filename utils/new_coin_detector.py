import os
import json
import ccxt
from datetime import datetime
from typing import List, Dict
import sys

# Logging
import logging
logger = logging.getLogger(__name__)

# 상위 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from paths import Paths
except ImportError:
    # Fallback
    class Paths:
        USER_CONFIG = "config"

class NewCoinDetector:
    """신규 상장 코인 감지기"""
    
    def __init__(self, exchange_id: str = 'bybit'):
        self.exchange_id = exchange_id.lower()
        self.tracker_file = os.path.join(Paths.USER_CONFIG, 'symbol_tracker.json')
        
        # CCXT 거래소 인스턴스
        try:
            self.exchange = getattr(ccxt, self.exchange_id)()
        except AttributeError:
            logger.info(f"Unsupported exchange: {self.exchange_id}")
            self.exchange = None

    def _load_tracker(self) -> Dict:
        """트래커 파일 로드"""
        if not os.path.exists(self.tracker_file):
            return self._init_tracker()
        
        try:
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self._init_tracker()

    def _init_tracker(self) -> Dict:
        """트래커 초기화"""
        return {
            self.exchange_id: {
                "last_check": None, 
                "symbols": [], 
                "pending": [], 
                "excluded": []
            }
        }

    def _save_tracker(self, data: Dict):
        """트래커 저장"""
        os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
        with open(self.tracker_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_exchange_symbols(self) -> List[str]:
        """거래소 상장 코인 조회 (USDT 선물 기준)"""
        if not self.exchange:
            return []
            
        try:
            self.exchange.load_markets()
            symbols = []
            
            # 거래소별 필터링
            for market in self.exchange.markets.values():
                # Linear(선물) & USDT Quote
                if market.get('linear') and market.get('quote') == 'USDT':
                    # ID 사용 (BTCUSDT)
                    symbols.append(market['id'])
            
            return symbols
        except Exception as e:
            logger.info(f"Error fetching symbols: {e}")
            return []

    def detect_new_coins(self) -> List[str]:
        """신규 코인 감지"""
        if not self.exchange:
            return []

        tracker = self._load_tracker()
        exchange_data = tracker.get(self.exchange_id, {})
        
        current_symbols = self.get_exchange_symbols()
        if not current_symbols:
            return []
            
        tracked = set(exchange_data.get('symbols', []))
        pending = set(exchange_data.get('pending', []))
        excluded = set(exchange_data.get('excluded', []))
        
        new_coins = []
        for s in current_symbols:
            # 기존에 없고, 펜딩도 아니고, 제외된 것도 아니면 신규
            if s not in tracked and s not in pending and s not in excluded:
                new_coins.append(s)
        
        return new_coins

    def register_new_coins(self, new_symbols: List[str]):
        """신규 코인을 Pending 리스트에 등록"""
        if not new_symbols:
            return
            
        tracker = self._load_tracker()
        if self.exchange_id not in tracker:
            tracker[self.exchange_id] = {"last_check": None, "symbols": [], "pending": [], "excluded": []}
            
        # 중복 제거 후 추가
        current_pending = set(tracker[self.exchange_id].get('pending', []))
        current_pending.update(new_symbols)
        
        tracker[self.exchange_id]['pending'] = list(current_pending)
        tracker[self.exchange_id]['last_check'] = datetime.now().isoformat()
        
        self._save_tracker(tracker)
