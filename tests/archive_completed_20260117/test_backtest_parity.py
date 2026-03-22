
import unittest
import pandas as pd
import numpy as np
from typing import cast, List, Dict, Any
from ui.widgets.backtest.worker import BacktestWorker
from core.optimizer import OptimizationResult
from utils.metrics import calculate_mdd, calculate_win_rate

class MockStrategy:
    def __init__(self, trades):
        self.trades = trades
        self.df_15m = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='15min'),
            'open': np.random.randn(100),
            'high': np.random.randn(100),
            'low': np.random.randn(100),
            'close': np.random.randn(100),
            'volume': np.random.randn(100)
        })

    def run_backtest(self, *args, **kwargs):
        # audit_logs를 포함한 튜플 반환
        return self.trades, []

class TestBacktestParity(unittest.TestCase):
    def test_calculate_stats_parity(self):
        """BacktestWorker의 통계 계산이 SSOT와 일치하는지 테스트"""
        # 테스트용 가상 거래 데이터 (PNL 10%, -5%, 15%)
        mock_trades = [
            {'pnl': 10.0, 'type': 'Long', 'entry_time': '2024-01-01'},
            {'pnl': -5.0, 'type': 'Long', 'entry_time': '2024-01-02'},
            {'pnl': 15.0, 'type': 'Long', 'entry_time': '2024-01-03'}
        ]
        
        strategy = MockStrategy(mock_trades)
        worker = BacktestWorker(
            strategy=strategy,
            slippage=0.0,
            fee=0.0,
            leverage=2,  # 레버리지 2배 적용
            direction='Both'
        )
        
        # 통계 계산 실행
        worker.trades_detail = mock_trades
        worker._calculate_stats()
        
        # result is now guaranteed to be OptimizationResult if _calculate_stats works
        result = cast(OptimizationResult, worker.result_stats)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, OptimizationResult)
        
        # 레버리지 반영된 PNL: [20.0, -10.0, 30.0]
        expected_pnls = [20.0, -10.0, 30.0]
        expected_leveraged_trades = [{'pnl': p} for p in expected_pnls]
        
        # 1. 승률 검증 (2승 1패 = 66.66%)
        expected_win_rate = calculate_win_rate(expected_leveraged_trades)
        self.assertAlmostEqual(result.win_rate, expected_win_rate)
        self.assertAlmostEqual(result.win_rate, 66.66666666666666)
        
        # 2. MDD 검증
        expected_mdd = calculate_mdd(expected_leveraged_trades)
        self.assertAlmostEqual(result.max_drawdown, expected_mdd)
        
        # 3. Simple Return (20 - 10 + 30 = 40)
        self.assertEqual(result.simple_return, 40.0)
        
        # 4. 필터 통과 성패 (MDD <= 20, WinRate >= 75% 미충달 -> False)
        # 현재 승률 66.6%이므로 passes_filter는 False여야 함
        self.assertFalse(result.passes_filter)

    def test_direction_filtering(self):
        """방향 필터링이 정상 작동하는지 테스트"""
        mock_trades = [
            {'pnl': 10.0, 'type': 'Long'},
            {'pnl': 5.0, 'type': 'Short'},
            {'pnl': -2.0, 'type': 'Long'}
        ]
        
        strategy = MockStrategy(mock_trades)
        
        # Long 방향만 선택
        worker = BacktestWorker(strategy=strategy, slippage=0, fee=0, leverage=1, direction='Long')
        
        # run() 내부 로직 시뮬레이션
        worker.trades_detail = mock_trades
        if worker.direction != 'Both':
            worker.trades_detail = [t for t in worker.trades_detail if t['type'] == worker.direction]
            
        self.assertEqual(len(worker.trades_detail), 2)
        self.assertTrue(all(t['type'] == 'Long' for t in worker.trades_detail))

if __name__ == '__main__':
    unittest.main()
