"""
UI 연결용 인터페이스
====================

PyQt/Streamlit 등 UI에서 호출하기 쉽도록 단순화된 API 제공

주요 기능:
    1. run_strategy() - 단일 전략 백테스트
    2. compare_strategies() - 두 전략 비교
    3. run_optimization() - 최적화 실행
    4. get_available_options() - 사용 가능한 옵션 목록
"""

import pandas as pd
from typing import Dict, List, Optional, Any

from .strategies import MACDStrategy, ADXDIStrategy, get_strategy, list_strategies
from .presets import (
    ALL_PRESETS, 
    get_preset, 
    list_presets,
    save_preset_json,
    load_preset_json,
)
from .constants import (
    AVAILABLE_TIMEFRAMES,
    AVAILABLE_METHODS,
    DEFAULT_TIMEFRAME,
    DEFAULT_METHOD,
    calculate_grade,
)


# =============================================================================
# 메인 API - UI에서 직접 호출
# =============================================================================

def run_strategy(
    df: pd.DataFrame,
    strategy: str = 'macd',
    params: Optional[Dict] = None,
    timeframe: str = '1h',
    apply_filters: bool = True,
) -> Dict:
    """
    단일 전략 백테스트 실행
    
    Args:
        df: 15분 OHLCV 데이터프레임
        strategy: 'macd' 또는 'adxdi'
        params: 파라미터 (None이면 기본값)
        timeframe: '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d'
        apply_filters: 필터 적용 여부
    
    Returns:
        {
            'trades': int,
            'win_rate': float,
            'simple_pnl': float,
            'compound_pnl': float,
            'mdd': float,
            'grade': str,
            ...
        }
    
    Example:
        >>> result = run_strategy(df, strategy='macd', timeframe='1h')
        >>> print(f"승률: {result['win_rate']:.1f}%")
    """
    # 전략 선택
    StrategyClass = get_strategy(strategy)
    if StrategyClass is None:
        return {'error': f'Unknown strategy: {strategy}'}
    
    # 백테스트 실행
    strat = StrategyClass(params)
    result = strat.backtest(df, timeframe, apply_filters)
    
    # 등급 계산
    if result.get('trades', 0) > 0:
        result['grade'] = calculate_grade(
            result.get('win_rate', 0),
            result.get('simple_pnl', 0) / max(result.get('trades', 1), 1),  # 평균 PnL을 PF로 대체
            result.get('mdd', 0)
        )
    else:
        result['grade'] = 'N/A'
    
    return result


def compare_strategies(
    df: pd.DataFrame,
    params: Optional[Dict] = None,
    timeframe: str = '1h',
    apply_filters: bool = True,
) -> Dict:
    """
    MACD vs ADX/DI 전략 비교
    
    Args:
        df: 15분 OHLCV 데이터프레임
        params: 공통 파라미터
        timeframe: 타임프레임
        apply_filters: 필터 적용 여부
    
    Returns:
        {
            'macd': {...결과...},
            'adxdi': {...결과...},
            'comparison': {
                'winner': 'macd' or 'adxdi',
                'pnl_diff': float,
                'win_rate_diff': float,
            }
        }
    
    Example:
        >>> comp = compare_strategies(df, timeframe='1h')
        >>> print(f"승자: {comp['comparison']['winner']}")
    """
    macd_result = run_strategy(df, 'macd', params, timeframe, apply_filters)
    adxdi_result = run_strategy(df, 'adxdi', params, timeframe, apply_filters)
    
    # 비교 분석
    macd_pnl = macd_result.get('simple_pnl', 0)
    adxdi_pnl = adxdi_result.get('simple_pnl', 0)
    
    comparison = {
        'winner': 'macd' if macd_pnl > adxdi_pnl else 'adxdi',
        'pnl_diff': macd_pnl - adxdi_pnl,
        'win_rate_diff': macd_result.get('win_rate', 0) - adxdi_result.get('win_rate', 0),
        'trades_diff': macd_result.get('trades', 0) - adxdi_result.get('trades', 0),
    }
    
    return {
        'macd': macd_result,
        'adxdi': adxdi_result,
        'comparison': comparison,
    }


def optimize_strategy(
    df: pd.DataFrame,
    strategy: str = 'macd',
    timeframe: str = '1h',
    mode: str = 'quick',
    apply_filters: bool = True,
    verbose: bool = True,
) -> List[Dict]:
    """
    전략 최적화 실행
    
    Args:
        df: 15분 OHLCV 데이터프레임
        strategy: 'macd' 또는 'adxdi'
        timeframe: 타임프레임
        mode: 'quick', 'default', 'deep'
        apply_filters: 필터 적용 여부
        verbose: 진행 상황 출력
    
    Returns:
        정렬된 결과 리스트 (PnL 기준 내림차순)
    
    Example:
        >>> results = optimize_strategy(df, strategy='macd', mode='quick')
        >>> best = results[0]
        >>> print(f"최적 파라미터: {best['params']}")
    """
    StrategyClass = get_strategy(strategy)
    if StrategyClass is None:
        return [{'error': f'Unknown strategy: {strategy}'}]
    
    strat = StrategyClass()
    return strat.optimize(df, timeframe, mode, apply_filters, verbose)


# =============================================================================
# 옵션/메타 정보 API
# =============================================================================

def get_available_options() -> Dict:
    """
    UI에서 사용 가능한 모든 옵션 반환
    
    Returns:
        {
            'strategies': ['macd', 'adxdi'],
            'timeframes': ['15m', '30m', '1h', ...],
            'presets': {...},
            'optimization_modes': ['quick', 'default', 'deep'],
        }
    """
    return {
        'strategies': list(list_strategies().keys()),
        'strategy_details': list_strategies(),
        'timeframes': AVAILABLE_TIMEFRAMES,
        'default_timeframe': DEFAULT_TIMEFRAME,
        'presets': list_presets(),
        'optimization_modes': ['quick', 'default', 'deep'],
        'filter_options': {
            'stoch_long_max': {'min': 0, 'max': 100, 'default': 50},
            'stoch_short_min': {'min': 0, 'max': 100, 'default': 50},
            'use_downtrend_filter': {'default': True},
        },
    }


def get_preset_params(preset_name: str) -> Dict:
    """프리셋 파라미터 반환"""
    return get_preset(preset_name)


def save_custom_preset(name: str, params: Dict, filepath: Optional[str] = None) -> bool:
    """커스텀 프리셋 저장"""
    if not filepath:
        return False
    save_preset_json(filepath, params, name)
    return True


def load_custom_preset(filepath: str) -> Dict:
    """커스텀 프리셋 로드"""
    return load_preset_json(filepath)


# =============================================================================
# 결과 포매팅 API
# =============================================================================

def format_result_summary(result: Dict) -> str:
    """결과를 읽기 쉬운 문자열로 포맷"""
    if 'error' in result:
        return f"Error: {result['error']}"
    
    return (
        f"전략: {result.get('strategy', 'N/A')}\n"
        f"타임프레임: {result.get('timeframe', 'N/A')}\n"
        f"등급: {result.get('grade', 'N/A')}\n"
        f"---\n"
        f"거래 수: {result.get('trades', 0):,}건\n"
        f"승률: {result.get('win_rate', 0):.1f}%\n"
        f"단리 PnL: {result.get('simple_pnl', 0):+,.1f}%\n"
        f"복리 PnL: {result.get('compound_pnl', 0):+,.1f}%\n"
        f"MDD: {result.get('mdd', 0):.1f}%\n"
        f"---\n"
        f"롱 거래: {result.get('long_trades', 0):,}건\n"
        f"숏 거래: {result.get('short_trades', 0):,}건\n"
    )


def format_comparison_summary(comparison: Dict) -> str:
    """비교 결과를 읽기 쉬운 문자열로 포맷"""
    macd = comparison.get('macd', {})
    adxdi = comparison.get('adxdi', {})
    comp = comparison.get('comparison', {})
    
    return (
        f"{'='*50}\n"
        f"MACD vs ADX/DI 전략 비교\n"
        f"{'='*50}\n\n"
        f"{'항목':<15} {'MACD':>15} {'ADX/DI':>15}\n"
        f"{'-'*50}\n"
        f"{'거래 수':<15} {macd.get('trades', 0):>15,} {adxdi.get('trades', 0):>15,}\n"
        f"{'승률':<15} {macd.get('win_rate', 0):>14.1f}% {adxdi.get('win_rate', 0):>14.1f}%\n"
        f"{'PnL':<15} {macd.get('simple_pnl', 0):>+14.1f}% {adxdi.get('simple_pnl', 0):>+14.1f}%\n"
        f"{'MDD':<15} {macd.get('mdd', 0):>14.1f}% {adxdi.get('mdd', 0):>14.1f}%\n"
        f"{'등급':<15} {macd.get('grade', 'N/A'):>15} {adxdi.get('grade', 'N/A'):>15}\n"
        f"{'-'*50}\n"
        f"승자: {comp.get('winner', 'N/A').upper()}\n"
        f"PnL 차이: {comp.get('pnl_diff', 0):+.1f}%\n"
    )


# =============================================================================
# UI 콜백용 래퍼 (PyQt/Streamlit 호환)
# =============================================================================

class StrategyRunner:
    """
    UI에서 사용하기 편한 클래스 기반 인터페이스
    
    Example (PyQt):
        runner = StrategyRunner()
        runner.load_data('parquet/bybit_btcusdt_15m.parquet')
        result = runner.run('macd', '1h')
    
    Example (Streamlit):
        runner = StrategyRunner()
        runner.set_data(uploaded_df)
        result = runner.run('adxdi', '2h', filters=False)
    """
    
    def __init__(self):
        self.df = None
        self.last_result = None
    
    def load_data(self, filepath: str) -> bool:
        """파일에서 데이터 로드"""
        try:
            if filepath.endswith('.parquet'):
                self.df = pd.read_parquet(filepath)
            elif filepath.endswith('.csv'):
                self.df = pd.read_csv(filepath)
            else:
                return False
            return True
        except Exception as e:
            print(f"데이터 로드 실패: {e}")
            return False
    
    def set_data(self, df: pd.DataFrame) -> None:
        """데이터프레임 직접 설정"""
        self.df = df
    
    def run(
        self,
        strategy: str = 'macd',
        timeframe: str = '1h',
        preset: Optional[str] = None,
        params: Optional[Dict] = None,
        filters: bool = True,
    ) -> Dict:
        """백테스트 실행"""
        if self.df is None:
            return {'error': 'No data loaded'}
        
        if preset:
            params = get_preset(preset)
        
        self.last_result = run_strategy(
            self.df, strategy, params, timeframe, filters
        )
        return self.last_result
    
    def compare(
        self,
        timeframe: str = '1h',
        params: Optional[Dict] = None,
        filters: bool = True,
    ) -> Dict:
        """두 전략 비교"""
        if self.df is None:
            return {'error': 'No data loaded'}
        
        return compare_strategies(self.df, params, timeframe, filters)
    
    def optimize(
        self,
        strategy: str = 'macd',
        timeframe: str = '1h',
        mode: str = 'quick',
        filters: bool = True,
    ) -> List[Dict]:
        """최적화 실행"""
        if self.df is None:
            return [{'error': 'No data loaded'}]
        
        return optimize_strategy(self.df, strategy, timeframe, mode, filters)
    
    def get_summary(self) -> str:
        """마지막 결과 요약"""
        if self.last_result is None:
            return "No result available"
        return format_result_summary(self.last_result)
