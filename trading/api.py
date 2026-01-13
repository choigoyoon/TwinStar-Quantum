"""
Trading API
===========

UI 연동을 위한 간편 API

사용법:
    from trading import run_backtest, run_optimization, compare_strategies
    
    # 백테스트
    result = run_backtest(df, strategy='macd', timeframe='1h')
    
    # 최적화
    results = run_optimization(df, strategy='macd', timeframe='1h', mode='quick')
    
    # 전략 비교
    comparison = compare_strategies(df, timeframe='1h')
"""

import pandas as pd
from typing import Dict, List, Any, Optional

from .strategies import get_strategy, list_strategies, STRATEGIES
from .core.presets import ALL_PRESETS, get_preset, list_presets
from .core.constants import AVAILABLE_TIMEFRAMES


def run_backtest(
    df: pd.DataFrame,
    strategy: str = 'macd',
    params: Optional[Dict] = None,
    preset: Optional[str] = None,
    timeframe: str = '1h',
    apply_filters: bool = True,
) -> Dict[str, Any]:
    """
    백테스트 실행 (UI용)
    
    Args:
        df: OHLCV 데이터프레임
        strategy: 전략명 ('macd' or 'adxdi')
        params: 파라미터 딕셔너리 (preset보다 우선)
        preset: 프리셋명 ('sandbox', 'filter_atr_optimal', etc.)
        timeframe: 타임프레임 ('1h', '2h', '4h', etc.)
        apply_filters: 필터 적용 여부
    
    Returns:
        백테스트 결과
    
    Example:
        # 기본 사용
        result = run_backtest(df, strategy='macd', timeframe='1h')
        
        # 프리셋 사용
        result = run_backtest(df, strategy='adxdi', preset='filter_atr_optimal')
        
        # 커스텀 파라미터
        result = run_backtest(df, params={'atr_mult': 2.0, 'trail_start': 1.3})
    """
    # 파라미터 결정
    if params is not None:
        use_params = params
    elif preset is not None:
        use_params = get_preset(preset)
    else:
        use_params = None  # 기본 프리셋 사용
    
    # 전략 인스턴스
    strat = get_strategy(strategy, use_params)
    
    # 백테스트 실행
    return strat.backtest(df, timeframe, apply_filters)


def run_optimization(
    df: pd.DataFrame,
    strategy: str = 'macd',
    timeframe: str = '1h',
    mode: str = 'quick',
    apply_filters: bool = True,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """
    최적화 실행 (UI용)
    
    Args:
        df: OHLCV 데이터프레임
        strategy: 전략명 ('macd' or 'adxdi')
        timeframe: 타임프레임
        mode: 'quick', 'default', 'deep'
        apply_filters: 필터 적용 여부
        verbose: 진행 상황 출력
    
    Returns:
        정렬된 결과 리스트
    
    Example:
        results = run_optimization(df, strategy='macd', mode='quick')
        print(f"Best: {results[0]['simple_pnl']}%")
    """
    strat = get_strategy(strategy)
    return strat.optimize(df, timeframe, mode, apply_filters, verbose)


def compare_strategies(
    df: pd.DataFrame,
    timeframe: str = '1h',
    apply_filters: bool = True,
) -> Dict[str, Any]:
    """
    전략 비교 (UI용)
    
    Args:
        df: OHLCV 데이터프레임
        timeframe: 타임프레임
        apply_filters: 필터 적용 여부
    
    Returns:
        비교 결과
    
    Example:
        comparison = compare_strategies(df, timeframe='1h')
        print(f"Winner: {comparison['winner']}")
    """
    results = {}
    
    for name in list_strategies():
        result = run_backtest(df, strategy=name, timeframe=timeframe, apply_filters=apply_filters)
        results[name] = result
    
    # 승자 결정
    best = None
    best_pnl = float('-inf')
    for name, result in results.items():
        if result['simple_pnl'] > best_pnl:
            best_pnl = result['simple_pnl']
            best = name
    
    return {
        'results': results,
        'winner': best,
        'timeframe': timeframe,
        'apply_filters': apply_filters,
        'pnl_diff': results.get('macd', {}).get('simple_pnl', 0) - results.get('adxdi', {}).get('simple_pnl', 0),
        'win_rate_diff': results.get('macd', {}).get('win_rate', 0) - results.get('adxdi', {}).get('win_rate', 0),
    }


def get_available_options() -> Dict[str, Any]:
    """
    사용 가능한 옵션 목록 (UI용)
    
    Returns:
        옵션 딕셔너리
    
    Example:
        options = get_available_options()
        print(f"Strategies: {options['strategies']}")
        print(f"Presets: {options['presets']}")
    """
    return {
        'strategies': list_strategies(),
        'strategy_descriptions': {
            'macd': 'MACD 히스토그램 부호 전환 기반',
            'adxdi': '+DI/-DI 크로스오버 기반',
        },
        'timeframes': AVAILABLE_TIMEFRAMES,
        'presets': list_presets(),
        'preset_descriptions': {
            name: get_preset(name) for name in list_presets()
        },
        'optimization_modes': ['quick', 'default', 'deep'],
    }


# =============================================================================
# UI 클래스 (상태 유지)
# =============================================================================
class TradingRunner:
    """
    UI용 트레이딩 러너 (상태 유지)
    
    Example:
        runner = TradingRunner()
        runner.load_data('data.parquet')
        result = runner.run_backtest('macd', '1h')
        results = runner.run_optimization('macd', '1h', 'quick')
    """
    
    def __init__(self):
        self.df = None
        self.last_result = None
    
    def load_data(self, path: str) -> int:
        """데이터 로드"""
        if path.endswith('.parquet'):
            self.df = pd.read_parquet(path)
        elif path.endswith('.csv'):
            self.df = pd.read_csv(path)
        else:
            raise ValueError(f"Unsupported format: {path}")
        return len(self.df)
    
    def set_data(self, df: pd.DataFrame):
        """데이터 설정"""
        self.df = df.copy()
    
    def run_backtest(
        self,
        strategy: str = 'macd',
        timeframe: str = '1h',
        preset: Optional[str] = None,
        apply_filters: bool = True,
    ) -> Dict[str, Any]:
        """백테스트 실행"""
        if self.df is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        self.last_result = run_backtest(
            self.df, strategy=strategy, preset=preset,
            timeframe=timeframe, apply_filters=apply_filters
        )
        return self.last_result
    
    def run_optimization(
        self,
        strategy: str = 'macd',
        timeframe: str = '1h',
        mode: str = 'quick',
        apply_filters: bool = True,
    ) -> List[Dict]:
        """최적화 실행"""
        if self.df is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        return run_optimization(
            self.df, strategy=strategy, timeframe=timeframe,
            mode=mode, apply_filters=apply_filters
        )
    
    def compare(
        self,
        timeframe: str = '1h',
        apply_filters: bool = True,
    ) -> Dict[str, Any]:
        """전략 비교"""
        if self.df is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        return compare_strategies(self.df, timeframe, apply_filters)
