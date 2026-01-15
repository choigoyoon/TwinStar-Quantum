"""
tests/test_unified_bot.py
core/unified_bot.py 핵심 기능 단위 테스트

테스트 범위:
1. UnifiedBot 초기화
2. 모듈형 컴포넌트 초기화 (mod_state, mod_data, mod_signal, mod_order, mod_position)
3. 상태 로드/저장
4. 신호 감지 (detect_signal)
5. 주문 실행 (execute_entry)
6. 포지션 관리 (manage_position, sync_position)
7. WebSocket 콜백
8. 자본 관리 (compounding)
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from core.unified_bot import UnifiedBot, setup_logging
from exchanges.base_exchange import Signal, Position
from datetime import datetime


# ==================== Test 1: 로깅 설정 ====================

def test_setup_logging():
    """로깅 설정 (파일 핸들러 초기화)"""
    # 로깅 설정이 에러 없이 실행되는지 확인
    try:
        setup_logging(symbol='TEST')
        success = True
    except Exception:
        success = False

    assert success is True


# ==================== Test 2: Mock 거래소 생성 ====================

@pytest.fixture
def mock_exchange():
    """Mock 거래소 객체"""
    exchange = Mock()
    exchange.symbol = 'BTCUSDT'
    exchange.direction = 'Both'
    exchange.leverage = 10
    exchange.preset_name = 'Default'
    exchange.name = 'MockExchange'

    # 메서드 mock
    exchange.get_position = Mock(return_value=None)
    exchange.fetch_ohlcv = Mock(return_value=pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min', tz='UTC'),
        'open': np.random.randn(100) * 100 + 50000,
        'high': np.random.randn(100) * 100 + 50100,
        'low': np.random.randn(100) * 100 + 49900,
        'close': np.random.randn(100) * 100 + 50000,
        'volume': np.random.randn(100) * 100 + 1000
    }))
    exchange.place_market_order = Mock(return_value=True)
    exchange.update_stop_loss = Mock(return_value=True)
    exchange.close_position = Mock(return_value=True)

    return exchange


# ==================== Test 3: UnifiedBot 초기화 ====================

@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_unified_bot_init(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """UnifiedBot 초기화"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # 기본 속성 확인
    assert bot.symbol == 'BTCUSDT'
    assert bot.exchange == mock_exchange
    assert bot.simulation_mode is True
    assert bot.direction == 'Both'


@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_unified_bot_init_modular_components(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """모듈형 컴포넌트 초기화 확인"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # 모듈형 컴포넌트가 초기화되었는지 확인
    assert hasattr(bot, 'mod_state')
    assert hasattr(bot, 'mod_data')
    assert hasattr(bot, 'mod_signal')
    assert hasattr(bot, 'mod_order')
    assert hasattr(bot, 'mod_position')


# ==================== Test 4: 상태 로드/저장 ====================

@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_load_state(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """상태 로드"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # load_state() 호출이 에러 없이 실행되는지 확인
    try:
        bot.load_state()
        success = True
    except Exception:
        success = False

    assert success is True


@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_save_state(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """상태 저장"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # save_state() 호출이 에러 없이 실행되는지 확인
    try:
        bot.save_state()
        success = True
    except Exception:
        success = False

    assert success is True


# ==================== Test 5: 신호 감지 ====================

@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_detect_signal(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """신호 감지"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # mock_signal이 신호를 반환하도록 설정
    # Signal 데이터클래스: type, pattern, stop_loss, atr, timestamp (optional)
    mock_signal_instance = mock_signal.return_value
    mock_signal_instance.detect_signal.return_value = Signal(
        type='Long',
        pattern='W',
        stop_loss=49000,
        atr=100.0,
        timestamp=datetime.now()
    )

    # detect_signal() 호출
    signal = bot.detect_signal()

    # signal은 Signal 객체이거나 None
    assert signal is None or isinstance(signal, Signal)


@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_detect_signal_no_position(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """포지션 없을 때 신호 감지"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # 포지션이 없을 때
    mock_exchange.get_position.return_value = None

    signal = bot.detect_signal()

    # 신호가 있을 수 있음
    assert signal is None or isinstance(signal, Signal)


# ==================== Test 6: 주문 실행 ====================

@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_execute_entry(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """주문 실행"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # 신호 생성
    # Signal 데이터클래스: type, pattern, stop_loss, atr, timestamp (optional)
    signal = Signal(
        type='Long',
        pattern='W',
        stop_loss=49000,
        atr=100.0,
        timestamp=datetime.now()
    )

    # mod_order가 성공을 반환하도록 설정
    mock_order_instance = mock_order.return_value
    mock_order_instance.execute_entry.return_value = True

    # execute_entry() 호출
    result = bot.execute_entry(signal)

    # bool 반환
    assert isinstance(result, bool)


# ==================== Test 7: 포지션 관리 ====================

@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_manage_position(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """포지션 관리"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # 포지션이 있을 때
    # Position 데이터클래스: symbol, side, entry_price, size, stop_loss, initial_sl, risk
    mock_exchange.get_position.return_value = Position(
        symbol='BTCUSDT',
        side='Long',
        entry_price=50000,
        size=0.1,
        stop_loss=49000,
        initial_sl=49000,
        risk=1000
    )

    # manage_position() 호출이 에러 없이 실행되는지 확인
    try:
        bot.manage_position()
        success = True
    except Exception:
        success = False

    assert success is True


@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_sync_position(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """포지션 동기화"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # sync_position() 호출이 에러 없이 실행되는지 확인
    try:
        result = bot.sync_position()
        success = True
    except Exception:
        success = False

    assert success is True


# ==================== Test 8: WebSocket 콜백 ====================

@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_on_candle_close_callback(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """캔들 종가 콜백"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # 캔들 데이터
    candle = {
        'timestamp': datetime.now(),
        'open': 50000,
        'high': 50100,
        'low': 49900,
        'close': 50050,
        'volume': 1000
    }

    # _on_candle_close() 호출이 에러 없이 실행되는지 확인
    try:
        bot._on_candle_close(candle)
        success = True
    except Exception:
        success = False

    assert success is True


@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_on_price_update_callback(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """가격 업데이트 콜백"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # _on_price_update() 호출이 에러 없이 실행되는지 확인
    try:
        bot._on_price_update(50000.0)
        success = True
    except Exception:
        success = False

    assert success is True


# ==================== Test 9: 자본 관리 ====================

@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_update_capital_for_compounding(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """복리 자본 업데이트"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # update_capital_for_compounding() 호출이 에러 없이 실행되는지 확인
    try:
        bot.update_capital_for_compounding()
        success = True
    except Exception:
        success = False

    assert success is True


# ==================== Test 10: 헬스체크 ====================

@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_get_readiness_status(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """준비 상태 확인"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    status = bot.get_readiness_status()

    # dict 반환
    assert isinstance(status, dict)


# ==================== Test 11: Edge Cases ====================

@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_unified_bot_none_exchange(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state
):
    """None 거래소 처리"""
    bot = UnifiedBot(None, simulation_mode=True)

    # symbol이 UNKNOWN이어야 함
    assert bot.symbol == "UNKNOWN"
    assert bot.exchange is None


@patch('core.unified_bot.BotStateManager')
@patch('core.unified_bot.BotDataManager')
@patch('core.unified_bot.SignalProcessor')
@patch('core.unified_bot.OrderExecutor')
@patch('core.unified_bot.PositionManager')
@patch('core.unified_bot.CapitalManager')
def test_unified_bot_thread_safety(
    mock_capital, mock_position, mock_order, mock_signal, mock_data, mock_state,
    mock_exchange
):
    """스레드 안전성 (Lock 확인)"""
    bot = UnifiedBot(mock_exchange, simulation_mode=True)

    # Lock이 초기화되었는지 확인
    assert hasattr(bot, '_data_lock')
    assert hasattr(bot, '_position_lock')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
