"""
trading.core 및 trading.backtest 모듈 테스트
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


class TestIndicators:
    """지표 계산 테스트"""
    
    @pytest.fixture
    def sample_df(self):
        """테스트용 샘플 데이터"""
        np.random.seed(42)
        n = 100
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        high = close + np.abs(np.random.randn(n) * 0.3)
        low = close - np.abs(np.random.randn(n) * 0.3)
        
        return pd.DataFrame({
            'open': close,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.randint(1000, 10000, n)
        })
    
    def test_calculate_rsi(self, sample_df):
        from trading.core.indicators import calculate_rsi
        
        rsi = calculate_rsi(sample_df['close'], period=14)
        
        assert len(rsi) == len(sample_df)
        assert all(0 <= r <= 100 for r in rsi.dropna())
        
    def test_calculate_ema(self, sample_df):
        from trading.core.indicators import calculate_ema
        
        ema = calculate_ema(sample_df['close'], period=20)
        
        assert len(ema) == len(sample_df)
        assert not ema.isna().all()
        
    def test_calculate_macd(self, sample_df):
        from trading.core.indicators import calculate_macd
        
        result = calculate_macd(sample_df['close'])
        
        assert 'macd' in result
        assert 'signal' in result
        assert 'histogram' in result
        assert len(result['macd']) == len(sample_df)
        
    def test_calculate_atr(self, sample_df):
        from trading.core.indicators import calculate_atr
        
        atr = calculate_atr(
            sample_df['high'],
            sample_df['low'],
            sample_df['close'],
            period=14
        )
        
        assert len(atr) == len(sample_df)
        assert all(a >= 0 for a in atr.dropna())
        
    def test_calculate_bollinger_bands(self, sample_df):
        from trading.core.indicators import calculate_bollinger_bands
        
        bb = calculate_bollinger_bands(sample_df['close'])
        
        assert 'upper' in bb
        assert 'middle' in bb
        assert 'lower' in bb
        # upper > middle > lower
        last_idx = len(sample_df) - 1
        assert bb['upper'].iloc[last_idx] >= bb['middle'].iloc[last_idx]
        assert bb['middle'].iloc[last_idx] >= bb['lower'].iloc[last_idx]
        
    def test_calculate_indicators(self, sample_df):
        from trading.core.indicators import calculate_indicators
        
        indicators = calculate_indicators(sample_df)
        
        assert indicators.rsi is not None
        assert indicators.ema is not None
        assert indicators.macd is not None
        assert indicators.atr is not None
        
    def test_add_indicators_to_df(self, sample_df):
        from trading.core.indicators import add_indicators_to_df
        
        result = add_indicators_to_df(sample_df)
        
        assert 'rsi' in result.columns
        assert 'ema' in result.columns
        assert 'macd' in result.columns
        assert 'atr' in result.columns


class TestSignals:
    """시그널 테스트"""
    
    def test_trade_signal_creation(self):
        from trading.core.signals import TradeSignal
        
        signal = TradeSignal(
            signal_type='Long',
            pattern='W',
            stop_loss=95.0,
            atr=1.5,
            timestamp=datetime.now(),
            entry_price=100.0,
        )
        
        assert signal.is_long()
        assert not signal.is_short()
        
    def test_trade_signal_to_dict(self):
        from trading.core.signals import TradeSignal
        
        signal = TradeSignal(
            signal_type='Short',
            pattern='M',
            stop_loss=105.0,
            atr=1.5,
            timestamp=datetime.now(),
        )
        
        data = signal.to_dict()
        
        assert data['signal_type'] == 'Short'
        assert data['pattern'] == 'M'
        
    def test_trade_signal_risk_reward(self):
        from trading.core.signals import TradeSignal
        
        signal = TradeSignal(
            signal_type='Long',
            pattern='W',
            stop_loss=95.0,
            atr=1.5,
            timestamp=datetime.now(),
            entry_price=100.0,
            take_profit=115.0,
        )
        
        rr = signal.risk_reward_ratio()
        
        assert rr is not None
        assert rr == 3.0  # (115-100) / (100-95) = 15/5 = 3
        
    def test_signal_generator(self):
        from trading.core.signals import SignalGenerator
        
        generator = SignalGenerator(params={
            'pullback_rsi_long': 35,
            'pullback_rsi_short': 65,
            'atr_mult': 2.0,
        })
        
        # 롱 시그널 조건
        indicators = {
            'rsi': 30,
            'macd': 0.002,
            'macd_signal': 0.001,
            'ema': 95.0,
            'atr': 1.5,
        }
        
        signal = generator.generate_signal(indicators, current_price=100.0)
        
        assert signal is not None
        assert signal.signal_type == 'Long'


class TestBacktestMetrics:
    """백테스트 메트릭 테스트"""
    
    @pytest.fixture
    def sample_trades(self):
        return [
            {'pnl': 5.0},
            {'pnl': -2.0},
            {'pnl': 3.0},
            {'pnl': -1.0},
            {'pnl': 4.0},
            {'pnl': 2.0},
            {'pnl': -3.0},
            {'pnl': 1.0},
        ]
    
    def test_calculate_mdd(self, sample_trades):
        from trading.backtest import calculate_mdd
        
        mdd = calculate_mdd(sample_trades)
        
        assert mdd >= 0
        assert mdd < 100
        
    def test_calculate_mdd_empty(self):
        from trading.backtest import calculate_mdd
        
        mdd = calculate_mdd([])
        assert mdd == 0.0
        
    def test_calculate_sharpe_ratio(self):
        from trading.backtest.metrics import calculate_sharpe_ratio
        
        returns = [0.01, -0.005, 0.02, 0.015, -0.01]
        sharpe = calculate_sharpe_ratio(returns)
        
        assert isinstance(sharpe, float)
        
    def test_calculate_profit_factor(self, sample_trades):
        from trading.backtest.metrics import calculate_profit_factor
        
        pf = calculate_profit_factor(sample_trades)
        
        assert pf > 0
        
    def test_calculate_win_rate(self, sample_trades):
        from trading.backtest.metrics import calculate_win_rate
        
        win_rate = calculate_win_rate(sample_trades)
        
        # 8개 중 5개 수익
        assert win_rate == 62.5
        
    def test_calculate_backtest_metrics(self, sample_trades):
        from trading.backtest import calculate_backtest_metrics
        
        metrics = calculate_backtest_metrics(sample_trades, leverage=1)
        
        assert 'total_return' in metrics
        assert 'trade_count' in metrics
        assert 'win_rate' in metrics
        assert 'profit_factor' in metrics
        assert 'max_drawdown' in metrics
        assert 'sharpe_ratio' in metrics
        
        assert metrics['trade_count'] == 8
        
    def test_calculate_backtest_metrics_with_leverage(self, sample_trades):
        from trading.backtest import calculate_backtest_metrics
        
        metrics_1x = calculate_backtest_metrics(sample_trades, leverage=1)
        metrics_10x = calculate_backtest_metrics(sample_trades, leverage=10)
        
        # 레버리지에 비례해서 수익률 증가
        assert metrics_10x['total_return'] == metrics_1x['total_return'] * 10


class TestIndicatorSet:
    """IndicatorSet 테스트"""
    
    def test_indicator_set_to_dict(self):
        from trading.core.indicators import IndicatorSet
        
        indicators = IndicatorSet(
            rsi=50.0,
            macd=0.001,
            ema=100.0,
            atr=1.5,
        )
        
        data = indicators.to_dict()
        
        assert data['rsi'] == 50.0
        assert data['macd'] == 0.001
        assert data['ema'] == 100.0
        assert data['atr'] == 1.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
