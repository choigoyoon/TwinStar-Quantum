"""
통합 테스트
==========

모듈 간 통합 테스트 및 import 검증
"""

import pytest  # type: ignore


class TestModuleImports:
    """모듈 import 테스트"""
    
    def test_ui_design_system_import(self):
        """UI 디자인 시스템 import"""
        from ui.design_system import (
            Colors, Typography, Spacing, Radius, Shadow,
            get_gradient, ThemeGenerator
        )
        
        assert Colors.bg_base == '#0d1117'
        assert Typography.text_base == '14px'
        assert Spacing.space_4 == '16px'
        
    def test_config_constants_import(self):
        """상수 모듈 import"""
        from config.constants import (
            EXCHANGE_INFO, SPOT_EXCHANGES, KRW_EXCHANGES,
            TF_MAPPING, TIMEFRAMES,
            DIRECTION_LONG, DIRECTION_SHORT, SLIPPAGE, FEE,
            GRADE_LIMITS, GRADE_COLORS,
            CACHE_DIR, PRESET_DIR,
        )
        
        assert 'bybit' in EXCHANGE_INFO
        assert DIRECTION_LONG == 'Long'
        assert SLIPPAGE == 0.0006
        
    def test_utils_formatters_import(self):
        """포맷터 모듈 import"""
        from utils.formatters import (
            format_number, format_currency, format_percent,
            format_pnl, format_datetime, format_duration,
        )
        
        assert format_number(1234.56) == '1,234.56'
        assert format_currency(100) == '$100.00'
        
    def test_trading_core_import(self):
        """트레이딩 코어 import"""
        from trading.core import (
            TradeSignal, SignalGenerator,
            calculate_indicators, IndicatorSet,
            SLIPPAGE, FEE, DIRECTION_LONG,
        )
        
        assert SLIPPAGE == 0.0006
        
    def test_trading_backtest_import(self):
        """백테스트 모듈 import"""
        from trading.backtest import (
            calculate_mdd, calculate_backtest_metrics,
            calculate_sharpe_ratio, calculate_profit_factor,
            BacktestEngine, Optimizer,
        )
        
        assert calculate_mdd([]) == 0.0


class TestDesignSystemIntegration:
    """디자인 시스템 통합 테스트"""
    
    def test_theme_generator_output(self):
        """ThemeGenerator 출력 검증"""
        from ui.design_system import ThemeGenerator
        
        stylesheet = ThemeGenerator.generate()
        
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 10000  # 충분한 스타일
        assert 'QMainWindow' in stylesheet
        assert 'QPushButton' in stylesheet
        assert '#0d1117' in stylesheet  # bg_base 색상
        
    def test_component_styles(self):
        """컴포넌트 스타일 검증"""
        from ui.design_system.styles import (
            ButtonStyles, InputStyles, CardStyles, TableStyles,
        )
        
        button = ButtonStyles.primary()
        assert 'background' in button
        
        input_style = InputStyles.default()
        assert 'border' in input_style
        
        card = CardStyles.status_card()
        assert 'border-radius' in card


class TestConstantsIntegration:
    """상수 통합 테스트"""
    
    def test_exchange_constants_consistency(self):
        """거래소 상수 일관성"""
        from config.constants import EXCHANGE_INFO, get_exchange_symbols
        
        for name, info in EXCHANGE_INFO.items():
            symbols = get_exchange_symbols(name)
            assert info['symbols'] == symbols
            
    def test_grade_constants_consistency(self):
        """등급 상수 일관성"""
        from config.constants import (
            GRADE_LIMITS, GRADE_COLORS,
            is_coin_allowed, get_tier_color,
        )
        
        for grade in GRADE_LIMITS.keys():
            color = get_tier_color(grade)
            assert color == GRADE_COLORS.get(grade, '#787b86')


class TestTradingIntegration:
    """트레이딩 모듈 통합 테스트"""
    
    def test_indicator_and_signal(self):
        """지표와 시그널 연동"""
        import pandas as pd
        import numpy as np
        
        from trading.core.indicators import calculate_indicators, add_indicators_to_df
        from trading.core.signals import SignalGenerator
        
        # 샘플 데이터
        np.random.seed(42)
        n = 100
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        
        df = pd.DataFrame({
            'open': close,
            'high': close + 0.5,
            'low': close - 0.5,
            'close': close,
            'volume': np.random.randint(1000, 10000, n),
        })
        
        # 지표 계산
        indicators = calculate_indicators(df)
        
        # 시그널 생성
        generator = SignalGenerator(params={
            'pullback_rsi_long': 35,
            'pullback_rsi_short': 65,
            'atr_mult': 2.0,
        })
        
        signal = generator.generate_signal(
            indicators.to_dict(),
            current_price=float(df['close'].iloc[-1])
        )
        
        # 시그널이 None이거나 유효한 TradeSignal
        if signal:
            assert signal.signal_type in ('Long', 'Short')
            
    def test_backtest_metrics_with_trades(self):
        """백테스트 메트릭 계산"""
        from trading.backtest import calculate_backtest_metrics
        
        trades = [
            {'pnl': 5.0, 'entry_price': 100, 'exit_price': 105},
            {'pnl': -2.0, 'entry_price': 105, 'exit_price': 103},
            {'pnl': 3.0, 'entry_price': 103, 'exit_price': 106},
        ]
        
        metrics = calculate_backtest_metrics(trades, leverage=1)
        
        assert metrics['trade_count'] == 3
        assert metrics['total_return'] == 6.0
        assert metrics['win_rate'] == pytest.approx(66.67, rel=0.1)


class TestCrossModuleCompatibility:
    """모듈 간 호환성 테스트"""
    
    def test_config_and_trading_constants(self):
        """config와 trading 상수 동기화"""
        from config.constants import SLIPPAGE as CONFIG_SLIPPAGE
        from config.constants import FEE as CONFIG_FEE
        from trading.core import SLIPPAGE as TRADING_SLIPPAGE
        from trading.core import FEE as TRADING_FEE
        
        assert CONFIG_SLIPPAGE == TRADING_SLIPPAGE
        assert CONFIG_FEE == TRADING_FEE
        
    def test_design_tokens_and_grade_colors(self):
        """디자인 토큰과 등급 색상 호환"""
        from ui.design_system.tokens import Colors, get_grade_color
        from config.constants import GRADE_COLORS
        
        # 디자인 시스템 등급 색상
        design_trial = get_grade_color('TRIAL')
        design_premium = get_grade_color('PREMIUM')
        
        # 상수 모듈 등급 색상
        const_trial = GRADE_COLORS['TRIAL']
        const_premium = GRADE_COLORS['PREMIUM']
        
        assert design_trial == const_trial
        assert design_premium == const_premium


class TestExportsConsistency:
    """Export 일관성 테스트"""
    
    def test_ui_design_system_exports(self):
        """ui.design_system exports"""
        import ui.design_system as ds
        
        assert hasattr(ds, 'Colors')
        assert hasattr(ds, 'Typography')
        assert hasattr(ds, 'ThemeGenerator')
        assert hasattr(ds, 'get_gradient')
        
    def test_config_constants_exports(self):
        """config.constants exports"""
        import config.constants as cc
        
        assert hasattr(cc, 'EXCHANGE_INFO')
        assert hasattr(cc, 'TIMEFRAMES')
        assert hasattr(cc, 'DIRECTION_LONG')
        assert hasattr(cc, 'SLIPPAGE')
        assert hasattr(cc, 'GRADE_LIMITS')
        
    def test_trading_exports(self):
        """trading 패키지 exports"""
        import trading
        
        assert hasattr(trading, 'run_backtest')
        assert hasattr(trading, 'MACDStrategy')
        assert hasattr(trading, 'SLIPPAGE')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
