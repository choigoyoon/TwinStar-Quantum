# strategies/wm_pattern_strategy.py
# 기존 strategy_breakeven.py를 래핑하여 GUI에서 사용
# DataFrame 직접 전달로 성능 최적화 (I/O 제거)

import os
import sys
import tempfile
from dataclasses import dataclass
from typing import List, Optional, Any, cast
from datetime import datetime
import pandas as pd
import numpy as np

# 상위 디렉토리 추가 (strategy_breakeven 임포트용)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .common.strategy_interface import (
    BaseStrategy, StrategyConfig, TradeSignal, Candle,
    SignalType, TradeStatus, BacktestResult
)


@dataclass
class WMStrategyParams:
    slippage: float = 0.06  # 왕복 0.12%
    trigger_mult: float = 1.5
    leverage: float = 3.0
    
    # Missing fields expected by developer_mode_widget.py
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    swing_length: int = 3
    atr_period: int = 14
    atr_multiplier: float = 1.5
    be_trigger_mult: float = 1.5
    pattern_tolerance: float = 0.03
    
    def to_dict(self) -> dict:
        return vars(self)


class WMPatternStrategy(BaseStrategy):
    """
    기존 BreakevenStrategy 래퍼 (최적화 버전)
    
    simulate_final_compounding.py와 동일한 로직 사용:
    - strategy_breakeven.BreakevenStrategy
    - 3x 레버리지 복리
    """
    
    def __init__(self, params: Optional[WMStrategyParams] = None):
        self.params = params or WMStrategyParams()
        super().__init__()
    
    def _init_config(self) -> StrategyConfig:
        return StrategyConfig(
            strategy_id="wm_pattern_v1",
            name="W/M Pattern Strategy",
            version="6.1.0",  # I/O 최적화 버전
            description="기존 BreakevenStrategy 래퍼 (68% 승률, I/O 없음)",
            timeframe="15m",
            symbols=["BTCUSDT"],
            tier_required="basic"
        )
    
    def reset_state(self):
        pass
    
    def check_signal(self, candles: List[Candle]) -> Optional[TradeSignal]:
        return None
    
    def run_legacy_backtest(self, candles: List[Candle], progress_callback=None) -> BacktestResult:
        """
        기존 BreakevenStrategy 백테스트 실행 (메모리 전송)
        """
        if progress_callback:
            progress_callback(5) # 초기화 단계
            
        print(f"🔄 데이터 변환 중... ({len(candles)}개 캔들)")
        
        # 1. 캔들을 DataFrame으로 변환
        data_list = [{
            'timestamp': datetime.fromtimestamp(c.timestamp / 1000),
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume
        } for c in candles]
        
        df = pd.DataFrame(data_list)
        
        if progress_callback:
            progress_callback(10) # 변환 완료
            
        print(f"📊 BreakevenStrategy 실행 (메모리 내 처리)...")
        
        # 2. BreakevenStrategy 실행 (Direct DataFrame)
        try:
            from strategy_breakeven import BreakevenStrategy # type: ignore
            # CSV 경로 대신 df 직접 전달
            strategy = BreakevenStrategy(df=df)
            
            trades_pnl = strategy.run_backtest(
                slippage=self.params.slippage,
                trigger_mult=self.params.trigger_mult,
                progress_callback=progress_callback
            )
        except Exception as e:
            print(f"❌ BreakevenStrategy 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            trades_pnl = []
        
        # 3. 복리 계산
        if progress_callback:
            progress_callback(95)
        capital = 100.0
        peak = 100.0
        mdd = 0.0
        leverage = self.params.leverage
        
        trades = []
        for i, pnl in enumerate(trades_pnl):
            roe = pnl * leverage
            old_cap = capital
            capital *= (1 + roe / 100)
            
            if capital <= 0:
                capital = 0
                break
            
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak * 100
            if dd > mdd:
                mdd = dd
            
            signal = TradeSignal(
                signal_type=SignalType.LONG if pnl > 0 else SignalType.SHORT, # 단순화
                symbol=self.config.symbols[0],
                timeframe=self.config.timeframe,
                entry_price=0,
                stop_loss=0,
                take_profit=0,
                candle_index=i,
                trade_id=f"BE_{i}"
            )
            signal.pnl_percent = roe
            signal.status = TradeStatus.TP_HIT if roe > 0 else TradeStatus.SL_HIT
            trades.append(signal)
        
        # 4. 결과 생성
        result = BacktestResult(
            strategy_id=self.config.strategy_id,
            symbol=self.config.symbols[0],
            timeframe=self.config.timeframe,
            start_date=data_list[0]['timestamp'] if data_list else datetime.now(),
            end_date=data_list[-1]['timestamp'] if data_list else datetime.now()
        )
        
        result.trades = trades
        result.total_trades = len(trades)
        result.win_count = sum(1 for t in trades if t.pnl_percent > 0)
        result.lose_count = sum(1 for t in trades if t.pnl_percent <= 0)
        result.win_rate = (result.win_count / result.total_trades * 100) if result.total_trades > 0 else 0
        result.total_pnl = ((capital - 100) / 100) * 100
        result.max_drawdown = mdd
        
        gross_profit = sum(t.pnl_percent for t in trades if t.pnl_percent > 0)
        gross_loss = abs(sum(t.pnl_percent for t in trades if t.pnl_percent <= 0))
        result.profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        print(f"✅ 백테스트 완료: {result.total_trades}개 거래, 승률 {result.win_rate:.1f}%, 수익 {result.total_pnl:.1f}%")
        
        return result
    
    def update_params(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.params, key):
                setattr(self.params, key, value)


def create_strategy(params: Optional[dict] = None) -> WMPatternStrategy:
    if params:
        p = WMStrategyParams(**params)
        return WMPatternStrategy(p)
    return WMPatternStrategy()
