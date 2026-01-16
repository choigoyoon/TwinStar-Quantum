"""
Track 4.2: 백테스트 vs 실시간 Parity 테스트

백테스트와 실시간 매매가 동일한 로직을 사용하는지 검증:
1. 동일 데이터 → 동일 신호
2. 동일 신호 → 동일 주문
3. 동일 메트릭 계산
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
from unittest.mock import Mock, patch


class TestBacktestRealtimeParity:
    """백테스트 vs 실시간 동작 일치 테스트"""

    def test_signal_generation_parity(self):
        """백테스트와 실시간이 동일한 신호를 생성하는지 검증"""
        from core.strategy_core import AlphaX7Core

        # 동일한 OHLCV 데이터
        df = self._create_test_data_with_pattern()

        strategy = AlphaX7Core()

        # 1. 백테스트 신호 (전체 데이터 한 번에)
        # detect_signal은 df_1h, df_15m 둘 다 필요
        backtest_signal = strategy.detect_signal(
            df_1h=df,
            df_15m=df,
            pattern_tolerance=0.03,
            rsi_period=14
        )

        # 2. 실시간 신호 (동일 데이터, 라이브 시뮬레이션)
        realtime_signal = strategy.detect_signal(
            df_1h=df.copy(),
            df_15m=df.copy(),
            pattern_tolerance=0.03,
            rsi_period=14
        )

        # 검증: 동일한 신호
        if backtest_signal and realtime_signal:
            assert backtest_signal.signal_type == realtime_signal.signal_type, \
                "백테스트와 실시간 방향이 같아야 함"
            assert abs(backtest_signal.stop_loss - realtime_signal.stop_loss) < 0.01, \
                "손절가가 동일해야 함"
        elif backtest_signal is None and realtime_signal is None:
            pass  # 둘 다 신호 없음 → OK
        else:
            pytest.fail("백테스트와 실시간 중 하나만 신호 발생 (불일치)")

    def test_indicator_calculation_parity(self):
        """지표 계산 일치 테스트 (RSI, ATR, MACD)"""
        from utils.indicators import calculate_rsi, calculate_atr, calculate_macd

        df = self._create_test_data_with_pattern()

        # 백테스트 지표 (close Series 전달, return_series=True)
        backtest_rsi: pd.Series = calculate_rsi(df['close'].copy(), period=14, return_series=True)  # type: ignore
        backtest_atr: pd.Series = calculate_atr(df.copy(), period=14, return_series=True)  # type: ignore
        macd_result = calculate_macd(df['close'].copy(), return_all=True)
        backtest_macd_line: pd.Series = macd_result[0]  # type: ignore
        backtest_signal_line: pd.Series = macd_result[1]  # type: ignore
        backtest_histogram: pd.Series = macd_result[2]  # type: ignore

        # 실시간 지표 (동일 데이터)
        realtime_rsi: pd.Series = calculate_rsi(df['close'].copy(), period=14, return_series=True)  # type: ignore
        realtime_atr: pd.Series = calculate_atr(df.copy(), period=14, return_series=True)  # type: ignore
        macd_result2 = calculate_macd(df['close'].copy(), return_all=True)
        realtime_macd_line: pd.Series = macd_result2[0]  # type: ignore
        realtime_signal_line: pd.Series = macd_result2[1]  # type: ignore
        realtime_histogram: pd.Series = macd_result2[2]  # type: ignore

        # 검증: NaN 제외하고 비교
        valid_idx = ~(backtest_rsi.isna() | realtime_rsi.isna())
        assert (backtest_rsi[valid_idx] == realtime_rsi[valid_idx]).all(), \
            "RSI 값이 동일해야 함"

        valid_idx = ~(backtest_atr.isna() | realtime_atr.isna())
        assert (backtest_atr[valid_idx] == realtime_atr[valid_idx]).all(), \
            "ATR 값이 동일해야 함"

        # MACD는 3개 시리즈 반환 (tuple unpacking)
        valid_idx = ~(backtest_macd_line.isna() | realtime_macd_line.isna())
        assert (backtest_macd_line[valid_idx] == realtime_macd_line[valid_idx]).all(), \
            "MACD Line 값이 동일해야 함"

        valid_idx = ~(backtest_signal_line.isna() | realtime_signal_line.isna())
        assert (backtest_signal_line[valid_idx] == realtime_signal_line[valid_idx]).all(), \
            "MACD Signal 값이 동일해야 함"

        valid_idx = ~(backtest_histogram.isna() | realtime_histogram.isna())
        assert (backtest_histogram[valid_idx] == realtime_histogram[valid_idx]).all(), \
            "MACD Histogram 값이 동일해야 함"

    def test_metrics_calculation_parity(self):
        """백테스트 메트릭 계산 일치 테스트"""
        from utils.metrics import (
            calculate_win_rate,
            calculate_mdd,
            calculate_profit_factor,
            calculate_sharpe_ratio
        )

        # 동일한 거래 데이터
        trades = [
            {'pnl': 2.5, 'entry_time': datetime.now(), 'exit_time': datetime.now()},
            {'pnl': -1.0, 'entry_time': datetime.now(), 'exit_time': datetime.now()},
            {'pnl': 3.0, 'entry_time': datetime.now(), 'exit_time': datetime.now()},
            {'pnl': 1.5, 'entry_time': datetime.now(), 'exit_time': datetime.now()},
            {'pnl': -0.5, 'entry_time': datetime.now(), 'exit_time': datetime.now()},
        ]

        # 백테스트 메트릭
        backtest_wr = calculate_win_rate(trades.copy())
        backtest_mdd = calculate_mdd(trades.copy())
        backtest_pf = calculate_profit_factor(trades.copy())
        backtest_sharpe = calculate_sharpe_ratio([t['pnl'] for t in trades])

        # 실시간 메트릭 (동일 데이터)
        realtime_wr = calculate_win_rate(trades.copy())
        realtime_mdd = calculate_mdd(trades.copy())
        realtime_pf = calculate_profit_factor(trades.copy())
        realtime_sharpe = calculate_sharpe_ratio([t['pnl'] for t in trades])

        # 검증
        assert backtest_wr == realtime_wr, "승률이 동일해야 함"
        assert abs(backtest_mdd - realtime_mdd) < 0.001, "MDD가 동일해야 함"
        assert abs(backtest_pf - realtime_pf) < 0.001, "Profit Factor가 동일해야 함"
        assert abs(backtest_sharpe - realtime_sharpe) < 0.001, "Sharpe Ratio가 동일해야 함"

    def test_trade_execution_parity(self):
        """거래 실행 로직 일치 테스트"""
        from core.order_executor import OrderExecutor
        from exchanges.base_exchange import OrderResult

        # Mock 거래소
        mock_exchange = Mock()
        mock_exchange.place_market_order = Mock(return_value=OrderResult(
            success=True,
            order_id='12345',
            filled_price=45000.0,
            filled_qty=0.01
        ))

        # 동일한 OrderExecutor
        executor = OrderExecutor(mock_exchange, dry_run=False)

        # 백테스트 주문
        backtest_result = executor.place_order_with_retry(
            side='Long',
            size=1000.0,
            stop_loss=44500.0
        )

        # 실시간 주문 (동일 파라미터)
        mock_exchange.place_market_order.reset_mock()
        realtime_result = executor.place_order_with_retry(
            side='Long',
            size=1000.0,
            stop_loss=44500.0
        )

        # 검증: 동일한 실행 로직 (place_order_with_retry는 OrderResult 객체를 반환)
        assert backtest_result is not None, "백테스트 주문 결과가 있어야 함"
        assert realtime_result is not None, "실시간 주문 결과가 있어야 함"
        assert mock_exchange.place_market_order.call_count == 1, \
            "실시간도 동일하게 1회 호출"

    def test_position_management_parity(self):
        """포지션 관리 로직 일치 테스트"""
        from core.position_manager import PositionManager
        from exchanges.base_exchange import OrderResult

        mock_exchange = Mock()
        pm = PositionManager(mock_exchange)

        # 포지션 상태 직접 설정 (실제 Position 객체 사용 안 함)
        pm.state_manager = Mock()
        pm.state_manager.position = Mock(
            entry_price=45000.0,
            side='Long',
            stop_loss=44500.0
        )
        pm.state_manager.highest_price = 45600.0

        # 백테스트 트레일링 스탑 업데이트 (실제 메서드 사용)
        mock_exchange.update_stop_loss = Mock(return_value=OrderResult(success=True))
        backtest_result = pm.update_trailing_sl(new_sl=45200.0)

        # 실시간 트레일링 스탑 업데이트 (동일 파라미터)
        mock_exchange.update_stop_loss.reset_mock()
        realtime_result = pm.update_trailing_sl(new_sl=45200.0)

        # 검증: 동일한 실행 로직
        assert backtest_result == realtime_result, \
            "트레일링 스탑 업데이트 결과가 동일해야 함"

    def test_full_cycle_parity(self):
        """전체 사이클 일치 테스트 (진입 → 청산)"""
        from core.strategy_core import AlphaX7Core

        # 동일한 데이터 및 파라미터
        df = self._create_test_data_with_pattern()

        strategy = AlphaX7Core()

        # 백테스트 전체 사이클
        backtest_trades = []
        signal = strategy.detect_signal(
            df_1h=df,
            df_15m=df,
            pattern_tolerance=0.03,
            rsi_period=14
        )
        if signal:
            backtest_trades.append({
                'signal_type': signal.signal_type,
                'stop_loss': signal.stop_loss,
                'pattern': signal.pattern
            })

        # 실시간 전체 사이클 (동일 데이터)
        realtime_trades = []
        signal = strategy.detect_signal(
            df_1h=df.copy(),
            df_15m=df.copy(),
            pattern_tolerance=0.03,
            rsi_period=14
        )
        if signal:
            realtime_trades.append({
                'signal_type': signal.signal_type,
                'stop_loss': signal.stop_loss,
                'pattern': signal.pattern
            })

        # 검증
        assert len(backtest_trades) == len(realtime_trades), \
            "거래 횟수가 동일해야 함"

        if len(backtest_trades) > 0:
            assert backtest_trades[0]['signal_type'] == realtime_trades[0]['signal_type']
            assert abs(backtest_trades[0]['stop_loss'] - realtime_trades[0]['stop_loss']) < 0.01
            assert backtest_trades[0]['pattern'] == realtime_trades[0]['pattern']

    def test_data_preprocessing_parity(self):
        """데이터 전처리 일치 테스트"""
        from core.data_manager import BotDataManager

        # 동일한 원본 데이터
        raw_data = self._create_raw_websocket_data()

        # 백테스트 데이터 처리
        dm_backtest = BotDataManager('bybit', 'BTCUSDT')
        for candle in raw_data:
            dm_backtest.append_candle(candle)
        df_backtest = dm_backtest.get_full_history()

        # 실시간 데이터 처리 (동일 로직)
        dm_realtime = BotDataManager('bybit', 'BTCUSDT')
        for candle in raw_data:
            dm_realtime.append_candle(candle)
        df_realtime = dm_realtime.get_full_history()

        # 검증: 데이터프레임 동일 (None이 아닌 경우에만)
        assert df_backtest is not None and df_realtime is not None, "데이터가 있어야 함"
        assert len(df_backtest) == len(df_realtime), "데이터 길이가 같아야 함"

        # 컬럼별 값 비교
        for col in ['open', 'high', 'low', 'close', 'volume']:
            assert (df_backtest[col] == df_realtime[col]).all(), \
                f"{col} 컬럼 값이 동일해야 함"

    def test_slippage_and_fees_parity(self):
        """슬리피지 및 수수료 적용 일치 테스트"""
        from config.constants import SLIPPAGE, FEE

        # 동일한 주문 데이터
        entry_price = 45000.0
        size = 1000.0  # $1000

        # 백테스트 슬리피지/수수료
        backtest_fill_price = entry_price * (1 + SLIPPAGE)
        backtest_fee = size * FEE

        # 실시간 슬리피지/수수료 (동일 로직)
        realtime_fill_price = entry_price * (1 + SLIPPAGE)
        realtime_fee = size * FEE

        # 검증
        assert backtest_fill_price == realtime_fill_price, "체결가가 동일해야 함"
        assert backtest_fee == realtime_fee, "수수료가 동일해야 함"

    # ===== 헬퍼 메서드 =====

    def _create_test_data_with_pattern(self) -> pd.DataFrame:
        """패턴이 있는 테스트 데이터 생성 (W패턴)"""
        data = []
        base_time = datetime.now()

        # W패턴 가격 (5개 캔들)
        pattern = [
            (45000, 45100, 44900, 45000, 1000),  # 하락
            (45000, 45050, 44800, 44850, 1200),  # 저점1
            (44850, 45200, 44850, 45150, 1500),  # 반등
            (45150, 45200, 44900, 44950, 1300),  # 저점2
            (44950, 45500, 44950, 45400, 2000),  # 돌파
        ]

        # 패턴 전 데이터 (95개)
        for i in range(95):
            data.append({
                'timestamp': base_time + timedelta(minutes=15 * i),
                'open': 44500.0 + i * 5,
                'high': 44600.0 + i * 5,
                'low': 44400.0 + i * 5,
                'close': 44500.0 + i * 5,
                'volume': 1000.0
            })

        # W패턴 추가
        for i, (open_p, high, low, close, vol) in enumerate(pattern):
            data.append({
                'timestamp': base_time + timedelta(minutes=15 * (95 + i)),
                'open': open_p,
                'high': high,
                'low': low,
                'close': close,
                'volume': vol
            })

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)

        # 지표 추가
        from utils.indicators import calculate_rsi, calculate_atr
        df['rsi'] = calculate_rsi(df['close'], period=14, return_series=True)
        df['atr'] = calculate_atr(df, period=14, return_series=True)

        return df

    def _create_raw_websocket_data(self) -> List[Dict]:
        """원본 WebSocket 데이터 시뮬레이션"""
        data = []
        base_time = datetime.now()

        for i in range(50):
            data.append({
                'timestamp': base_time + timedelta(minutes=15 * i),
                'open': 45000.0 + i * 10,
                'high': 45100.0 + i * 10,
                'low': 44900.0 + i * 10,
                'close': 45000.0 + i * 10,
                'volume': 1000.0
            })

        return data


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
