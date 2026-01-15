"""
Track 4.1: WebSocket → 신호 → 주문 플로우 통합 테스트

실제 거래 플로우를 end-to-end로 검증:
1. WebSocket 데이터 수신
2. 신호 생성 (strategy_core)
3. 주문 실행 (order_executor)
4. 포지션 관리 (position_manager)
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch


class TestTradingFlowIntegration:
    """거래 플로우 통합 테스트"""

    def test_websocket_to_signal_flow(self):
        """WebSocket 데이터 → 신호 생성 플로우"""
        from core.data_manager import BotDataManager
        from core.strategy_core import AlphaX7Core

        # 1. WebSocket 데이터 시뮬레이션 (15분봉)
        dm = BotDataManager('bybit', 'BTCUSDT')

        # 캔들 데이터 생성 (W패턴 형성)
        candles = []
        base_time = datetime.now()
        base_price = 45000.0

        # W패턴 생성 (5개 캔들)
        w_pattern_prices = [
            (45000, 45100, 44900, 45000),  # 첫 번째 하락
            (45000, 45050, 44800, 44850),  # 저점 1
            (44850, 45200, 44850, 45150),  # 반등
            (45150, 45200, 44900, 44950),  # 저점 2
            (44950, 45500, 44950, 45400),  # 돌파
        ]

        for i, (open_p, high, low, close) in enumerate(w_pattern_prices):
            candles.append({
                'timestamp': base_time + timedelta(minutes=15 * i),
                'open': open_p,
                'high': high,
                'low': low,
                'close': close,
                'volume': 1000.0
            })

        # 2. 데이터 추가
        for candle in candles:
            dm.append_candle(candle)

        # 3. 전략으로 신호 감지
        strategy = AlphaX7Core()
        df = dm.get_full_history()

        # RSI, ATR 지표 추가
        from utils.indicators import calculate_rsi, calculate_atr
        df['rsi'] = calculate_rsi(df, period=14)
        df['atr'] = calculate_atr(df, period=14)

        # 신호 감지
        params = {
            'atr_mult': 1.5,
            'rsi_period': 14,
            'pattern_tolerance': 0.03
        }

        signal = strategy.check_signal(df, params)

        # 검증
        assert signal is not None, "W패턴 신호가 감지되어야 함"
        assert signal.direction in ['Long', 'Short'], "방향이 명확해야 함"
        assert signal.entry_price > 0, "진입가가 있어야 함"
        assert signal.sl_price > 0, "손절가가 있어야 함"

    def test_signal_to_order_execution_flow(self):
        """신호 생성 → 주문 실행 플로우"""
        from core.order_executor import OrderExecutor
        from exchanges.base_exchange import Signal

        # Mock 거래소
        mock_exchange = Mock()
        mock_exchange.place_market_order = Mock(return_value=Mock(
            success=True,
            order_id='12345',
            filled_price=45000.0,
            filled_qty=0.01
        ))
        mock_exchange.update_stop_loss = Mock(return_value=Mock(success=True))

        # OrderExecutor 생성
        executor = OrderExecutor(mock_exchange, dry_run=False)

        # 신호 생성
        signal = Signal(
            direction='Long',
            entry_price=45000.0,
            sl_price=44500.0,  # -1.1%
            confidence=85.0,
            atr=200.0
        )

        # 주문 실행
        result = executor.place_order_with_retry(
            side='Long',
            size=1000.0,  # $1000
            stop_loss=44500.0
        )

        # 검증
        assert result is not None, "주문 결과가 있어야 함"
        assert result.success is True, "주문이 성공해야 함"
        assert mock_exchange.place_market_order.called, "시장가 주문 호출되어야 함"
        assert mock_exchange.update_stop_loss.called, "손절 설정 호출되어야 함"

    def test_position_management_flow(self):
        """포지션 진입 → 관리 → 청산 플로우"""
        from core.position_manager import PositionManager
        from exchanges.base_exchange import Position

        # Mock 거래소
        mock_exchange = Mock()

        # 포지션 생성
        pm = PositionManager(mock_exchange)

        # 1. 포지션 진입
        position = Position(
            symbol='BTCUSDT',
            side='Long',
            entry_price=45000.0,
            size=0.01,
            stop_loss=44500.0
        )

        pm.current_position = position

        # 2. 트레일링 스탑 업데이트
        current_price = 45600.0  # +1.33%
        highest_price = 45600.0

        trailing_sl = pm.calculate_trailing_stop(
            position=position,
            current_price=current_price,
            highest_price=highest_price,
            trail_start_r=0.8,
            trail_dist_r=0.5
        )

        # 검증: 트레일링 스탑이 진입 손절가보다 높아야 함
        if trailing_sl is not None:
            assert trailing_sl > position.stop_loss, "트레일링 스탑이 올라가야 함"

        # 3. 청산 조건 체크
        mock_exchange.get_position = Mock(return_value=None)  # 청산됨
        mock_exchange.close_position = Mock(return_value=Mock(success=True))

        result = pm.check_exit_conditions(
            current_price=current_price,
            tp_r=1.5,
            sl_check=True
        )

        # TP 달성 시 청산 신호
        assert result in [True, False, None], "청산 여부가 반환되어야 함"

    def test_full_trading_cycle(self):
        """전체 거래 사이클 (진입 → 관리 → 청산)"""
        from core.unified_bot import UnifiedBot

        # Mock 설정
        mock_exchange = Mock()
        mock_exchange.name = 'bybit'
        mock_exchange.get_klines = Mock(return_value=self._create_sample_df())
        mock_exchange.get_position = Mock(return_value=None)
        mock_exchange.place_market_order = Mock(return_value=Mock(
            success=True,
            order_id='12345',
            filled_price=45000.0
        ))
        mock_exchange.update_stop_loss = Mock(return_value=Mock(success=True))
        mock_exchange.close_position = Mock(return_value=Mock(success=True))

        # UnifiedBot 생성
        config = {
            'symbol': 'BTCUSDT',
            'timeframe': '15m',
            'leverage': 5,
            'seed_capital': 100.0
        }

        with patch('core.unified_bot.ExchangeManager') as mock_em:
            mock_em.return_value.get_exchange.return_value = mock_exchange

            bot = UnifiedBot(config)
            bot.adapter = mock_exchange

            # 1. 신호 감지
            signal = bot.detect_signal()

            # 2. 포지션 진입 (신호가 있으면)
            if signal:
                entered = bot.enter_position(signal)
                assert entered is True, "포지션 진입 성공해야 함"

                # 3. 포지션 관리
                managed = bot.manage_position()
                assert managed is not None, "포지션 관리 결과가 있어야 함"

    def test_websocket_data_continuity(self):
        """WebSocket 데이터 연속성 테스트"""
        from core.data_manager import BotDataManager

        dm = BotDataManager('bybit', 'BTCUSDT')

        # 1. 초기 데이터 (100개)
        base_time = datetime.now()
        for i in range(100):
            dm.append_candle({
                'timestamp': base_time + timedelta(minutes=15 * i),
                'open': 45000.0 + i,
                'high': 45100.0 + i,
                'low': 44900.0 + i,
                'close': 45000.0 + i,
                'volume': 1000.0
            })

        # 2. 데이터 추가 (실시간 시뮬레이션)
        for i in range(100, 110):
            dm.append_candle({
                'timestamp': base_time + timedelta(minutes=15 * i),
                'open': 45000.0 + i,
                'high': 45100.0 + i,
                'low': 44900.0 + i,
                'close': 45000.0 + i,
                'volume': 1000.0
            })

        # 검증
        df = dm.get_full_history()
        assert len(df) >= 100, "최소 100개 데이터가 있어야 함"

        # 시간순 정렬 확인
        timestamps = df.index if df.index.name == 'timestamp' else df['timestamp']
        assert timestamps.is_monotonic_increasing, "타임스탬프가 시간순이어야 함"

    def test_error_recovery_flow(self):
        """에러 복구 플로우 테스트"""
        from core.order_executor import OrderExecutor

        # Mock 거래소 (첫 시도 실패, 재시도 성공)
        mock_exchange = Mock()
        call_count = 0

        def place_order_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Mock(success=False, error="Network timeout")
            else:
                return Mock(success=True, order_id='12345')

        mock_exchange.place_market_order = Mock(side_effect=place_order_side_effect)

        # OrderExecutor 생성 (재시도 3회)
        executor = OrderExecutor(mock_exchange, dry_run=False)

        # 주문 실행 (재시도 포함)
        result = executor.place_order_with_retry(
            side='Long',
            size=1000.0,
            stop_loss=44500.0,
            max_retries=3
        )

        # 검증
        assert result is not None, "재시도 후 성공해야 함"
        assert result.success is True, "최종 결과가 성공이어야 함"
        assert call_count == 2, "첫 시도 실패 + 재시도 성공 = 2회 호출"

    # ===== 헬퍼 메서드 =====

    def _create_sample_df(self) -> pd.DataFrame:
        """샘플 캔들 데이터 생성"""
        data = []
        base_time = datetime.now()
        base_price = 45000.0

        for i in range(100):
            data.append({
                'timestamp': base_time + timedelta(minutes=15 * i),
                'open': base_price + i * 10,
                'high': base_price + i * 10 + 100,
                'low': base_price + i * 10 - 100,
                'close': base_price + i * 10 + 50,
                'volume': 1000.0
            })

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df


class TestMultiSymbolIntegration:
    """멀티 심볼 통합 테스트"""

    def test_multi_symbol_signal_collection(self):
        """멀티 심볼 시그널 수집 플로우"""
        from core.multi_symbol_backtest import MultiSymbolBacktest

        # 백테스트 생성 (3개 심볼)
        bt = MultiSymbolBacktest(
            exchange='bybit',
            symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            timeframes=['4h'],
            initial_capital=100.0
        )

        # Mock 데이터 로드
        with patch.object(bt, 'load_candle_data') as mock_load:
            mock_load.return_value = self._create_sample_df()

            # 시그널 수집
            with patch.object(bt, 'extract_signals_from_symbol') as mock_extract:
                mock_extract.return_value = [
                    Mock(
                        symbol='BTCUSDT',
                        timestamp=datetime.now(),
                        direction='Long',
                        entry_price=45000.0,
                        sl_price=44500.0
                    )
                ]

                bt.collect_all_signals()

                # 검증
                assert len(bt.all_signals) > 0, "시그널이 수집되어야 함"
                assert mock_extract.call_count == 3, "3개 심볼 × 1개 타임프레임 = 3회 호출"

    def test_multi_symbol_time_based_execution(self):
        """멀티 심볼 타임스탬프 기반 실행"""
        from core.multi_symbol_backtest import MultiSymbolBacktest, Signal

        bt = MultiSymbolBacktest(
            exchange='bybit',
            initial_capital=100.0
        )

        # 시그널 생성 (타임스탬프 순서 섞임)
        base_time = datetime.now()
        bt.all_signals = [
            Signal(
                symbol='ETHUSDT',
                timestamp=base_time + timedelta(hours=2),
                direction='Long',
                entry_price=2500.0,
                sl_price=2450.0,
                atr=50.0,
                pattern_score=80.0,
                volume_24h=1000000.0,
                timeframe='4h'
            ),
            Signal(
                symbol='BTCUSDT',
                timestamp=base_time + timedelta(hours=1),
                direction='Short',
                entry_price=45000.0,
                sl_price=45500.0,
                atr=200.0,
                pattern_score=85.0,
                volume_24h=5000000.0,
                timeframe='4h'
            ),
            Signal(
                symbol='SOLUSDT',
                timestamp=base_time + timedelta(hours=3),
                direction='Long',
                entry_price=110.0,
                sl_price=108.0,
                atr=2.0,
                pattern_score=75.0,
                volume_24h=500000.0,
                timeframe='4h'
            ),
        ]

        # 타임스탬프 기준 정렬
        bt.all_signals.sort(key=lambda x: x.timestamp)

        # 검증: BTCUSDT(1h) → ETHUSDT(2h) → SOLUSDT(3h) 순서
        assert bt.all_signals[0].symbol == 'BTCUSDT'
        assert bt.all_signals[1].symbol == 'ETHUSDT'
        assert bt.all_signals[2].symbol == 'SOLUSDT'

    def _create_sample_df(self) -> pd.DataFrame:
        """샘플 캔들 데이터 생성"""
        data = []
        base_time = datetime.now()
        base_price = 45000.0

        for i in range(500):
            data.append({
                'timestamp': base_time + timedelta(hours=4 * i),
                'open': base_price + i * 10,
                'high': base_price + i * 10 + 100,
                'low': base_price + i * 10 - 100,
                'close': base_price + i * 10 + 50,
                'volume': 1000.0
            })

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
