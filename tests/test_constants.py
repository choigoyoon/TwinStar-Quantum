"""
config/constants 모듈 테스트
"""

import pytest


class TestExchangeConstants:
    """거래소 상수 테스트"""
    
    def test_exchange_info_structure(self):
        from config.constants import EXCHANGE_INFO
        
        # 필수 거래소 존재
        assert 'bybit' in EXCHANGE_INFO
        assert 'binance' in EXCHANGE_INFO
        assert 'upbit' in EXCHANGE_INFO
        
    def test_exchange_info_fields(self):
        from config.constants import EXCHANGE_INFO
        
        for name, info in EXCHANGE_INFO.items():
            assert 'icon' in info, f"{name} missing icon"
            assert 'type' in info, f"{name} missing type"
            assert 'market' in info, f"{name} missing market"
            assert 'symbols' in info, f"{name} missing symbols"
            
    def test_spot_exchanges(self):
        from config.constants import SPOT_EXCHANGES, is_spot_exchange
        
        assert 'upbit' in SPOT_EXCHANGES
        assert 'bithumb' in SPOT_EXCHANGES
        assert is_spot_exchange('upbit')
        assert not is_spot_exchange('bybit')
        
    def test_get_exchange_symbols(self):
        from config.constants import get_exchange_symbols
        
        symbols = get_exchange_symbols('bybit')
        assert 'BTCUSDT' in symbols
        assert 'ETHUSDT' in symbols
        
    def test_get_exchange_fees(self):
        from config.constants import get_exchange_fees
        
        fees = get_exchange_fees('bybit')
        assert 'maker' in fees
        assert 'taker' in fees
        assert fees['maker'] >= 0
        assert fees['taker'] >= 0


class TestTimeframeConstants:
    """타임프레임 상수 테스트"""
    
    def test_timeframes_list(self):
        from config.constants import TIMEFRAMES
        
        assert '1h' in TIMEFRAMES
        assert '4h' in TIMEFRAMES
        assert '1d' in TIMEFRAMES
        
    def test_tf_mapping(self):
        from config.constants import TF_MAPPING, get_entry_tf
        
        assert TF_MAPPING['4h'] == '1h'
        assert TF_MAPPING['1d'] == '4h'
        
        assert get_entry_tf('4h') == '1h'
        assert get_entry_tf('1d') == '4h'
        
    def test_normalize_timeframe(self):
        from config.constants import normalize_timeframe
        
        assert normalize_timeframe('15min') == '15m'
        assert normalize_timeframe('1H') == '1h'
        assert normalize_timeframe('1D') == '1d'


class TestTradingConstants:
    """거래 상수 테스트"""
    
    def test_directions(self):
        from config.constants import (
            DIRECTION_LONG, DIRECTION_SHORT, DIRECTION_BOTH
        )
        
        assert DIRECTION_LONG == 'Long'
        assert DIRECTION_SHORT == 'Short'
        assert DIRECTION_BOTH == 'Both'
        
    def test_direction_conversion(self):
        from config.constants import to_api_direction, from_api_direction
        
        assert to_api_direction('Long') == 'Buy'
        assert to_api_direction('Short') == 'Sell'
        
        assert from_api_direction('Buy') == 'Long'
        assert from_api_direction('sell') == 'Short'
        
    def test_cost_constants(self):
        from config.constants import SLIPPAGE, FEE, TOTAL_COST
        
        assert SLIPPAGE == 0.0006
        assert FEE == 0.00055
        assert TOTAL_COST == SLIPPAGE + FEE


class TestGradeConstants:
    """등급 상수 테스트"""
    
    def test_grade_limits(self):
        from config.constants import GRADE_LIMITS
        
        assert 'TRIAL' in GRADE_LIMITS
        assert 'PREMIUM' in GRADE_LIMITS
        
        assert GRADE_LIMITS['TRIAL']['positions'] == 1
        assert GRADE_LIMITS['PREMIUM']['positions'] == 10
        
    def test_grade_colors(self):
        from config.constants import GRADE_COLORS, get_tier_color
        
        assert GRADE_COLORS['PREMIUM'] == '#00e676'
        assert get_tier_color('PREMIUM') == '#00e676'
        assert get_tier_color('INVALID') == '#787b86'  # 기본값
        
    def test_is_coin_allowed(self):
        from config.constants import is_coin_allowed
        
        # TRIAL은 BTC만
        assert is_coin_allowed('TRIAL', 'BTCUSDT')
        assert not is_coin_allowed('TRIAL', 'ETHUSDT')
        
        # PREMIUM은 여러 코인
        assert is_coin_allowed('PREMIUM', 'BTCUSDT')
        assert is_coin_allowed('PREMIUM', 'ETHUSDT')
        
    def test_get_max_positions(self):
        from config.constants import get_max_positions
        
        assert get_max_positions('TRIAL') == 1
        assert get_max_positions('PREMIUM') == 10


class TestPathConstants:
    """경로 상수 테스트"""
    
    def test_path_constants(self):
        from config.constants import CACHE_DIR, PRESET_DIR, LOG_DIR
        
        assert CACHE_DIR == 'data/cache'
        assert PRESET_DIR == 'config/presets'
        assert LOG_DIR == 'logs'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
