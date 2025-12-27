# C:\매매전략\gui\strategy_interface.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable
from enum import Enum
from datetime import datetime
import pandas as pd
import numpy as np

# ============================================================
# 신호 타입 정의
# ============================================================

class SignalType(Enum):
    NONE = "none"
    LONG = "long"
    SHORT = "short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

class TradeStatus(Enum):
    PENDING = "pending"      # 신호 발생, 진입 대기
    ENTRY = "entry"          # 진입 완료
    TP_HIT = "tp_hit"        # 익절
    SL_HIT = "sl_hit"        # 손절
    CLOSED = "closed"        # 청산 완료

# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class TradeSignal:
    """
    전략 → GUI 전달 신호
    (내부 로직은 숨기고 결과만 전달)
    """
    # 필수 정보
    signal_type: SignalType
    symbol: str
    timeframe: str
    
    # 가격 정보
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    
    # 타이밍
    signal_time: datetime = field(default_factory=datetime.now)
    candle_index: int = -1
    
    # 식별
    trade_id: str = ""
    
    # 결과 (백테스트/실매매 후 업데이트)
    status: TradeStatus = TradeStatus.PENDING
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    pnl_percent: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'signal_type': self.signal_type.value,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'signal_time': self.signal_time.isoformat(),
            'trade_id': self.trade_id,
            'status': self.status.value,
            'pnl_percent': self.pnl_percent
        }

@dataclass
class StrategyConfig:
    """
    전략 설정 (GUI 표시용)
    - 내부 파라미터는 포함하지 않음
    """
    strategy_id: str
    name: str
    version: str
    description: str
    
    # 지원 설정
    timeframe: str              # 기본 타임프레임
    symbols: List[str]          # 지원 심볼
    
    # 성과 지표 (백테스트 결과)
    win_rate: float = 0.0
    avg_profit: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    
    # 접근 권한
    tier_required: str = "basic"  # free, basic, pro, vip

@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_id: str
    symbol: str
    timeframe: str
    
    # 기간
    start_date: datetime
    end_date: datetime
    
    # 거래 목록
    trades: List[TradeSignal] = field(default_factory=list)
    
    # 통계
    total_trades: int = 0
    win_count: int = 0
    lose_count: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    
    # 차트용 데이터
    ohlcv: Optional[pd.DataFrame] = None
    equity_curve: List[float] = field(default_factory=list)

# ============================================================
# 베이스 전략 클래스
# ============================================================

class BaseStrategy(ABC):
    """
    모든 전략이 상속받는 베이스 클래스
    - 실제 로직은 .pyd로 컴파일하여 숨김
    """
    
    def __init__(self):
        self.config: StrategyConfig = self._init_config()
        self.last_signal_index: int = -100
        self.min_bars_between: int = 10
    
    @abstractmethod
    def _init_config(self) -> StrategyConfig:
        """전략 설정 초기화"""
        pass
    
    @abstractmethod
    def check_signal(self, ohlcv: pd.DataFrame) -> Optional[TradeSignal]:
        """
        신호 체크 (핵심 로직)
        
        Args:
            ohlcv: DataFrame with columns [timestamp, open, high, low, close, volume]
        
        Returns:
            TradeSignal or None
        """
        pass
    
    def get_config(self) -> StrategyConfig:
        """설정 반환"""
        return self.config
    
    def can_trade(self, current_index: int) -> bool:
        """최소 간격 체크"""
        return (current_index - self.last_signal_index) >= self.min_bars_between

# ============================================================
# Holy Grail 전략 구현
# ============================================================

class HolyGrailStrategy(BaseStrategy):
    """
    Holy Grail 전략 (MACD 기반 추세선 돌파)
    - bot_bybit.py 로직 통합
    """
    
    def __init__(self, tp_pct: float = 2.0, sl_pct: float = 2.0):
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        
        # MACD 파라미터
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        
        super().__init__()
    
    def _init_config(self) -> StrategyConfig:
        return StrategyConfig(
            strategy_id="holy_grail_v1",
            name="Holy Grail",
            version="1.0.0",
            description="MACD 기반 추세선 돌파 전략 (15분봉)",
            timeframe="15m",
            symbols=["BTCUSDT", "ETHUSDT"],
            tier_required="basic"
        )
    
    def _calculate_macd(self, close: pd.Series) -> tuple:
        """MACD 계산"""
        exp1 = close.ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = close.ewm(span=self.macd_slow, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=self.macd_signal, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def _label_peaks(self, hist: pd.Series) -> pd.Series:
        """MACD 히스토그램 H/L 라벨링"""
        labels = pd.Series(index=hist.index, dtype=str)
        labels[:] = ''
        
        for i in range(2, len(hist) - 1):
            # H: 양수이고 이전/이후보다 큼
            if hist.iloc[i] > 0:
                if hist.iloc[i] > hist.iloc[i-1] and hist.iloc[i] > hist.iloc[i+1]:
                    labels.iloc[i] = 'H'
            # L: 음수이고 이전/이후보다 작음
            elif hist.iloc[i] < 0:
                if hist.iloc[i] < hist.iloc[i-1] and hist.iloc[i] < hist.iloc[i+1]:
                    labels.iloc[i] = 'L'
        
        return labels
    
    def _find_trendline(self, df: pd.DataFrame, labels: pd.Series, 
                        current_idx: int, lookback: int = 50) -> Optional[dict]:
        """추세선 찾기"""
        start_idx = max(0, current_idx - lookback)
        
        # 최근 H점들 찾기
        h_indices = [i for i in range(start_idx, current_idx) 
                     if labels.iloc[i] == 'H']
        
        if len(h_indices) < 2:
            return None
        
        # 마지막 2개 H점으로 하향 추세선
        h1_idx, h2_idx = h_indices[-2], h_indices[-1]
        h1_price = df['high'].iloc[h1_idx]
        h2_price = df['high'].iloc[h2_idx]
        
        # 하향 추세인지 확인
        if h2_price >= h1_price:
            return None
        
        # 기울기 계산
        slope = (h2_price - h1_price) / (h2_idx - h1_idx)
        
        return {
            'type': 'down',
            'p1': (h1_idx, h1_price),
            'p2': (h2_idx, h2_price),
            'slope': slope,
            'get_price': lambda idx: h2_price + slope * (idx - h2_idx)
        }
    
    def check_signal(self, ohlcv: pd.DataFrame) -> Optional[TradeSignal]:
        """
        Holy Grail 신호 체크
        
        Returns:
            TradeSignal if breakout detected, else None
        """
        if len(ohlcv) < 50:
            return None
        
        df = ohlcv.copy()
        current_idx = len(df) - 2  # 완성된 마지막 캔들
        
        # 최소 간격 체크
        if not self.can_trade(current_idx):
            return None
        
        # MACD 계산
        macd, signal, hist = self._calculate_macd(df['close'])
        
        # H/L 라벨링
        labels = self._label_peaks(hist)
        
        # 추세선 찾기
        trendline = self._find_trendline(df, labels, current_idx)
        
        if trendline is None:
            return None
        
        # 돌파 체크 (현재 캔들이 추세선 위로 종가 마감)
        tl_price = trendline['get_price'](current_idx)
        current_close = df['close'].iloc[current_idx]
        prev_close = df['close'].iloc[current_idx - 1]
        
        # 돌파 조건: 이전 종가 < 추세선 AND 현재 종가 > 추세선
        if prev_close < tl_price and current_close > tl_price:
            entry_price = current_close
            
            signal = TradeSignal(
                signal_type=SignalType.LONG,
                symbol=self.config.symbols[0],
                timeframe=self.config.timeframe,
                entry_price=entry_price,
                stop_loss=entry_price * (1 - self.sl_pct / 100),
                take_profit=entry_price * (1 + self.tp_pct / 100),
                candle_index=current_idx,
                trade_id=f"HG_{current_idx}_{int(datetime.now().timestamp())}"
            )
            
            self.last_signal_index = current_idx
            return signal
        
        return None

# ============================================================
# 전략 매니저 (여러 전략 관리)
# ============================================================

class StrategyManager:
    """전략 등록 및 관리"""
    
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_strategy: Optional[BaseStrategy] = None
    
    def register(self, strategy: BaseStrategy):
        """전략 등록"""
        config = strategy.get_config()
        self.strategies[config.strategy_id] = strategy
        print(f"✅ 전략 등록: {config.name} v{config.version}")
    
    def activate(self, strategy_id: str) -> bool:
        """전략 활성화"""
        if strategy_id in self.strategies:
            self.active_strategy = self.strategies[strategy_id]
            print(f"🎯 전략 활성화: {strategy_id}")
            return True
        return False
    
    def get_list(self) -> List[StrategyConfig]:
        """등록된 전략 목록"""
        return [s.get_config() for s in self.strategies.values()]
    
    def check_signal(self, ohlcv: pd.DataFrame) -> Optional[TradeSignal]:
        """활성 전략으로 신호 체크"""
        if self.active_strategy:
            return self.active_strategy.check_signal(ohlcv)
        return None


# ============================================================
# 테스트
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Strategy Interface 테스트")
    print("=" * 50)
    
    # 전략 생성
    strategy = HolyGrailStrategy(tp_pct=2.0, sl_pct=2.0)
    config = strategy.get_config()
    
    print(f"\n📋 전략 정보:")
    print(f"  - ID: {config.strategy_id}")
    print(f"  - 이름: {config.name}")
    print(f"  - 버전: {config.version}")
    print(f"  - 타임프레임: {config.timeframe}")
    print(f"  - 설명: {config.description}")
    
    # 더미 데이터로 테스트
    print(f"\n📊 더미 데이터 신호 테스트...")
    
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='15min')
    dummy_data = pd.DataFrame({
        'timestamp': [int(d.timestamp() * 1000) for d in dates],
        'open': 100 + np.cumsum(np.random.randn(100) * 0.5),
        'high': 0,
        'low': 0,
        'close': 0,
        'volume': np.random.randint(100, 1000, 100)
    })
    dummy_data['high'] = dummy_data['open'] + abs(np.random.randn(100) * 0.3)
    dummy_data['low'] = dummy_data['open'] - abs(np.random.randn(100) * 0.3)
    dummy_data['close'] = dummy_data['open'] + np.random.randn(100) * 0.2
    
    signal = strategy.check_signal(dummy_data)
    
    if signal:
        print(f"  ✅ 신호 발생!")
        print(f"  - 타입: {signal.signal_type.value}")
        print(f"  - 진입가: {signal.entry_price:.2f}")
        print(f"  - 손절가: {signal.stop_loss:.2f}")
        print(f"  - 익절가: {signal.take_profit:.2f}")
    else:
        print(f"  ⏳ 신호 없음 (정상)")
    
    # 전략 매니저 테스트
    print(f"\n🎯 전략 매니저 테스트...")
    manager = StrategyManager()
    manager.register(strategy)
    manager.activate("holy_grail_v1")
    
    strategies = manager.get_list()
    print(f"  등록된 전략: {len(strategies)}개")
    
    print("\n✅ 테스트 완료!")
