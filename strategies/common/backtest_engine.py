# strategies/common/backtest_engine.py
# 백테스트 엔진 - 기존 전략 로직 직접 호출

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from .strategy_interface import (
    BaseStrategy, Candle, TradeSignal, BacktestResult,
    SignalType, TradeStatus
)


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    initial_capital: float = 100.0  # $100
    leverage: int = 3
    commission: float = 0.0004
    slippage: float = 0.0006


class BacktestEngine:
    """백테스트 엔진 - 기존 전략 직접 호출"""
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
    
    def run(self, strategy: BaseStrategy, candles: List[Candle], progress_callback=None) -> BacktestResult:
        """백테스트 실행"""
        
        # 기존 전략(BreakevenStrategy) 래퍼인 경우 직접 호출
        if hasattr(strategy, 'run_legacy_backtest'):
            print("📊 기존 전략 로직(BreakevenStrategy) 사용")
            return strategy.run_legacy_backtest(candles, progress_callback=progress_callback)
        
        # 일반 전략인 경우 기본 백테스트
        return self._run_default_backtest(strategy, candles, progress_callback)
    
    def _run_default_backtest(self, strategy: BaseStrategy, candles: List[Candle], progress_callback=None) -> BacktestResult:
        """기본 백테스트 로직"""
        
        if hasattr(strategy, 'reset_state'):
            strategy.reset_state()
        
        strategy_config = strategy.get_config()
        
        result = BacktestResult(
            strategy_id=strategy_config.strategy_id,
            symbol=strategy_config.symbols[0] if strategy_config.symbols else "UNKNOWN",
            timeframe=strategy_config.timeframe,
            start_date=datetime.fromtimestamp(candles[0].timestamp / 1000) if candles else datetime.now(),
            end_date=datetime.fromtimestamp(candles[-1].timestamp / 1000) if candles else datetime.now()
        )
        
        capital = self.config.initial_capital
        peak_capital = capital
        max_dd = 0.0
        
        trades = []
        current_position = None
        
        for i in range(100, len(candles)):
            current_candle = candles[i]
            
            if current_position:
                signal = current_position
                
                if signal.signal_type == SignalType.LONG:
                    if current_candle.high >= signal.take_profit:
                        pnl = ((signal.take_profit - signal.entry_price) / signal.entry_price) * 100 * self.config.leverage
                        signal.pnl_percent = pnl
                        signal.status = TradeStatus.TP_HIT
                        capital *= (1 + pnl / 100)
                        trades.append(signal)
                        current_position = None
                    elif current_candle.low <= signal.stop_loss:
                        pnl = ((signal.stop_loss - signal.entry_price) / signal.entry_price) * 100 * self.config.leverage
                        signal.pnl_percent = pnl
                        signal.status = TradeStatus.SL_HIT
                        capital *= (1 + pnl / 100)
                        trades.append(signal)
                        current_position = None
                        
                elif signal.signal_type == SignalType.SHORT:
                    if current_candle.low <= signal.take_profit:
                        pnl = ((signal.entry_price - signal.take_profit) / signal.entry_price) * 100 * self.config.leverage
                        signal.pnl_percent = pnl
                        signal.status = TradeStatus.TP_HIT
                        capital *= (1 + pnl / 100)
                        trades.append(signal)
                        current_position = None
                    elif current_candle.high >= signal.stop_loss:
                        pnl = ((signal.entry_price - signal.stop_loss) / signal.entry_price) * 100 * self.config.leverage
                        signal.pnl_percent = pnl
                        signal.status = TradeStatus.SL_HIT
                        capital *= (1 + pnl / 100)
                        trades.append(signal)
                        current_position = None
            
            if not current_position:
                signal = strategy.check_signal(candles[:i+1])
                if signal and signal.signal_type in [SignalType.LONG, SignalType.SHORT]:
                    current_position = signal
                    signal.status = TradeStatus.ENTRY
            
            if capital > peak_capital:
                peak_capital = capital
            dd = (peak_capital - capital) / peak_capital * 100
            if dd > max_dd:
                max_dd = dd
        
        result.trades = trades
        result.total_trades = len(trades)
        result.win_count = sum(1 for t in trades if t.pnl_percent > 0)
        result.lose_count = sum(1 for t in trades if t.pnl_percent <= 0)
        result.win_rate = (result.win_count / result.total_trades * 100) if result.total_trades > 0 else 0
        result.total_pnl = ((capital - self.config.initial_capital) / self.config.initial_capital) * 100
        result.max_drawdown = max_dd
        
        gross_profit = sum(t.pnl_percent for t in trades if t.pnl_percent > 0)
        gross_loss = abs(sum(t.pnl_percent for t in trades if t.pnl_percent <= 0))
        result.profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        return result
