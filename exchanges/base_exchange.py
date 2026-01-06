# exchanges/base_exchange.py
"""
거래소 공통 인터페이스 (추상 클래스)
모든 거래소는 이 인터페이스를 구현해야 함
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import pandas as pd


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    side: str  # 'Long' or 'Short'
    entry_price: float
    size: float
    stop_loss: float
    initial_sl: float
    risk: float
    be_triggered: bool = False
    entry_time: datetime = None
    # ATR Trailing Fields
    atr: float = 0.0
    extreme_price: float = 0.0
    trail_start_price: float = 0.0
    trail_dist: float = 0.0
    # Tracking
    order_id: str = ""
    status: str = "open"
    take_profit: float = 0.0  # [NEW] TP tracking
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry': self.entry_price,
            'entry_price': self.entry_price, # [v1.5.2] Dashboard Compatibility
            'size': self.size,
            'sl': self.stop_loss,
            'initial_sl': self.initial_sl,
            'risk': self.risk,
            'be_triggered': self.be_triggered,
            'time': self.entry_time.isoformat() if self.entry_time else None,
            'atr': self.atr,
            'extreme_price': self.extreme_price,
            'trail_start_price': self.trail_start_price,
            'trail_dist': self.trail_dist,
            'order_id': self.order_id,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        return cls(
            symbol=data.get('symbol', ''),
            side=data.get('side', data.get('type', '')),
            entry_price=data.get('entry', 0),
            size=data.get('size', 0),
            stop_loss=data.get('sl', 0),
            initial_sl=data.get('initial_sl', 0),
            risk=data.get('risk', 0),
            be_triggered=data.get('be_triggered', False),
            entry_time=datetime.fromisoformat(data['time']) if data.get('time') else None,
            atr=data.get('atr', 0.0),
            extreme_price=data.get('extreme_price', 0.0),
            trail_start_price=data.get('trail_start_price', 0.0),
            trail_dist=data.get('trail_dist', 0.0),
            order_id=data.get('order_id', ''),
            status=data.get('status', 'open')
        )


@dataclass
class Signal:
    """매매 신호"""
    type: str  # 'Long' or 'Short'
    pattern: str  # 'W', 'M', 'Triangle'
    stop_loss: float
    atr: float
    timestamp: datetime = None


class BaseExchange(ABC):
    """거래소 공통 인터페이스"""
    
    def __init__(self, config: dict):
        """
        config: {
            'api_key': str,
            'api_secret': str,
            'symbol': str,
            'leverage': int,
            'amount_usd': float,
            'testnet': bool
        }
        """
        self.config = config
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.leverage = config.get('leverage', 3)
        self.amount_usd = config.get('amount_usd', 100)
        self.timeframe = config.get('timeframe', '4h')
        self.direction = config.get('direction', 'Both')  # [NEW] 방향 설정
        self.position: Optional[Position] = None
        self.capital = self.amount_usd
        
        # [NEW] 통화 통합 시스템 - 서브클래스에서 override
        self.quote_currency = 'USDT'  # 기준 통화 (USDT / KRW)
        self.market_type = 'futures'   # 시장 유형 (futures / spot)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """거래소 이름"""
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """API 연결"""
        pass
    
    @abstractmethod
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """
        캔들 데이터 조회
        interval: '1', '5', '15', '60' (분 단위)
        returns: DataFrame with columns [timestamp, open, high, low, close, volume]
        """
        pass
    
    @abstractmethod
    def get_current_price(self) -> float:
        """현재 가격"""
        pass
    
    @abstractmethod
    def place_market_order(self, side: str, size: float, stop_loss: float, take_profit: float = 0) -> bool:
        """
        시장가 주문
        side: 'Long' or 'Short'
        size: 수량
        stop_loss: 손절가
        take_profit: 익절가
        """
        pass
    
    @abstractmethod
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정"""
        pass
    
    @abstractmethod
    def close_position(self) -> bool:
        """포지션 청산"""
        pass

    @abstractmethod
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (불타기)"""
        pass
    
    @abstractmethod
    def get_balance(self) -> float:
        """잔고 조회"""
        pass
    
    @abstractmethod
    def sync_time(self) -> bool:
        """서버 시간 동기화"""
        pass
    
    # ========== 공통 메서드 ==========
    
    def get_quote_balance(self) -> float:
        """기준 통화 잔고 조회 (USDT 또는 KRW)
        
        Returns:
            float: 기준 통화 잔고 (safe_float 적용)
        """
        try:
            from utils.helpers import safe_float
            return safe_float(self.get_balance())
        except Exception:
            return 0.0
    
    def get_symbol_format(self, base: str = 'BTC') -> str:
        """거래소별 심볼 포맷 반환
        
        Args:
            base: 기준 코인 (BTC, ETH 등)
            
        Returns:
            str: 거래소별 심볼 포맷 (BTC-KRW, BTCUSDT 등)
        """
        if self.market_type == 'spot':
            return f"{base}-{self.quote_currency}"  # 현물: BTC-KRW
        else:
            return f"{base}{self.quote_currency}"   # 선물: BTCUSDT
    
    def is_spot_exchange(self) -> bool:
        """현물 거래소 여부"""
        return self.market_type == 'spot'
    
    def is_krw_exchange(self) -> bool:
        """KRW 거래소 여부"""
        return self.quote_currency == 'KRW'

    
    def get_swings(self, df: pd.DataFrame, length: int = 3) -> tuple:
        """스윙 고/저점 계산 (공통 로직)"""
        highs = df['high'].values
        lows = df['low'].values
        
        last_swing_low = 0
        last_swing_high = 999999
        
        for i in range(length * 2, len(df)):
            pivot_idx = i - length
            
            # Pivot Low
            is_low = True
            for k in range(pivot_idx - length, pivot_idx + length + 1):
                if 0 <= k < len(lows) and lows[k] < lows[pivot_idx]:
                    is_low = False
                    break
            if is_low:
                last_swing_low = lows[pivot_idx]
            
            # Pivot High
            is_high = True
            for k in range(pivot_idx - length, pivot_idx + length + 1):
                if 0 <= k < len(highs) and highs[k] > highs[pivot_idx]:
                    is_high = False
                    break
            if is_high:
                last_swing_high = highs[pivot_idx]
        
        return last_swing_low, last_swing_high
    
    def get_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """ATR 계산 (utils.indicators 모듈 위임)"""
        try:
            from utils.indicators import calculate_atr
            return calculate_atr(df, period=period, return_series=False)
        except ImportError:
            # Fallback for standalone execution
            import numpy as np
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            tr = []
            for i in range(1, len(df)):
                tr1 = high[i] - low[i]
                tr2 = abs(high[i] - close[i-1])
                tr3 = abs(low[i] - close[i-1])
                tr.append(max(tr1, tr2, tr3))
            
            if len(tr) >= period:
                return np.mean(tr[-period:])
            return np.mean(tr) if tr else 0
    
    def calculate_position_size(self, price: float) -> float:
        """포지션 크기 계산"""
        qty_usd = self.capital * self.leverage
        return qty_usd / price
    
    # ========== [NEW] 매매 히스토리 & 복리 자본 (공통) ==========
    
    def get_trade_history(self, limit: int = 50) -> list:
        """매매 히스토리 조회 - 하위 클래스에서 오버라이드 필요"""
        # 기본 구현: 로컬 파일에서 로드
        import os, json
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'trade_history', self.name.lower())
        log_file = os.path.join(log_dir, f"{self.symbol}_history.json")
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    trades = json.load(f)
                return trades[:limit]
            except Exception as e:
                logging.debug(f"Failed to load trade history from {log_file}: {e}")
        return []
    
    def get_realized_pnl(self, limit: int = 100) -> float:
        """누적 실현 손익 조회"""
        trades = self.get_trade_history(limit=limit)
        return sum(t.get('pnl', 0) for t in trades)
    
    def get_compounded_capital(self, initial_capital: float) -> float:
        """복리 자본 조회 (초기 자본 + 누적 수익)"""
        realized_pnl = self.get_realized_pnl()
        compounded = initial_capital + realized_pnl
        
        # 최소 자본 보장 (초기의 10%)
        min_capital = initial_capital * 0.1
        return max(compounded, min_capital)
    
    def save_trade_history_to_log(self, trades: list = None):
        """매매 내역을 로컬 로그 파일에 보관 (공통)"""
        import os, json
        
        try:
            if trades is None:
                trades = self.get_trade_history(limit=100)
            
            if not trades:
                return
            
            # 거래소/심볼별 분리
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'trade_history', self.name.lower())
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"{self.symbol}_history.json")
            
            # 기존 내역 로드
            existing = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            
            # 중복 제거 (created_time 또는 timestamp 기준)
            existing_keys = {t.get('created_time') or t.get('timestamp') for t in existing}
            new_trades = [t for t in trades if (t.get('created_time') or t.get('timestamp')) not in existing_keys]
            
            if new_trades:
                all_trades = existing + new_trades
                all_trades.sort(key=lambda x: x.get('created_time') or x.get('timestamp') or '0', reverse=True)
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(all_trades, f, indent=2, ensure_ascii=False)
                
                import logging
                logging.info(f"📝 Trade log saved: {len(new_trades)} new trades → {log_file}")
                
        except Exception as e:
            import logging
            logging.error(f"Trade log save error: {e}")

