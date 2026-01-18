"""
백테스트 엔진
=============

전략 백테스트 실행
(sandbox_optimization/base.py의 run_backtest_core와 동일한 로직)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List

from ..core.constants import DEFAULT_SLIPPAGE, DEFAULT_FEE, INITIAL_CAPITAL
from ..core.indicators import prepare_data
from ..core.execution import run_simulation, calculate_metrics
from ..strategies import get_strategy


class BacktestEngine:
    """
    백테스트 엔진
    
    Example:
        engine = BacktestEngine()
        result = engine.run(df, strategy, timeframe='1h')
    """
    
    def __init__(
        self,
        slippage: float = DEFAULT_SLIPPAGE,
        fee: float = DEFAULT_FEE,
        max_bars: int = 100,
    ):
        self.slippage = slippage
        self.fee = fee
        self.max_bars = max_bars
    
    def run(
        self,
        df: pd.DataFrame,
        strategy,
        timeframe: str = '1h',
        apply_filters: bool = True,
    ) -> Dict[str, Any]:
        """
        백테스트 실행
        
        Args:
            df: 원본 데이터프레임 (15분봉 등)
            strategy: 전략 인스턴스 또는 이름 (str 'macd', 'adxdi')
            timeframe: 목표 타임프레임
            apply_filters: 필터 적용 여부
        
        Returns:
            백테스트 결과
        """
        # 전략 문자열이면 인스턴스로 변환
        if isinstance(strategy, str):
            strategy = get_strategy(strategy)
        
        # 데이터 준비 (지표 추가)
        df_tf = prepare_data(df, None)
        
        if len(df_tf) < 100:
            return {
                'trades': 0, 'win_rate': 0, 'simple_pnl': 0,
                'error': 'Insufficient data'
            }
        
        # 패턴 탐지
        patterns = strategy.detect_patterns(df_tf)
        
        # run_backtest_core와 동일한 로직
        params = strategy.params
        stoch_long_max = params.get('stoch_long_max', 50)
        stoch_short_min = params.get('stoch_short_min', 50)
        use_downtrend_filter = params.get('use_downtrend_filter', True)
        
        stoch_k = df_tf['stoch_k'].values if 'stoch_k' in df_tf.columns else np.full(len(df_tf), 50)
        downtrend = df_tf['downtrend'].values if 'downtrend' in df_tf.columns else np.zeros(len(df_tf), dtype=bool)
        
        trades = []
        filtered_count = {'stoch': 0, 'downtrend': 0}
        
        for pattern in patterns:
            idx = pattern['idx']
            direction = pattern['direction']
            
            # 필터 적용
            if apply_filters:
                # Stochastic 필터
                if direction == 'Long' and stoch_long_max < 100:
                    if not np.isnan(stoch_k[idx]) and stoch_k[idx] > stoch_long_max:
                        filtered_count['stoch'] += 1
                        continue
                if direction == 'Short' and stoch_short_min > 0:
                    if not np.isnan(stoch_k[idx]) and stoch_k[idx] < stoch_short_min:
                        filtered_count['stoch'] += 1
                        continue
                
                # Downtrend 필터 (Short만)
                if use_downtrend_filter and direction == 'Short':
                    if not downtrend[idx]:
                        filtered_count['downtrend'] += 1
                        continue
            
            # 거래 시뮬레이션
            trade = run_simulation(
                df_tf, pattern, params,
                self.slippage, self.fee, self.max_bars
            )
            if trade:
                trades.append(trade)
        
        # 메트릭 계산
        result = calculate_metrics(trades)
        result['timeframe'] = timeframe
        result['strategy'] = strategy.name
        result['patterns_found'] = len(patterns)
        result['apply_filters'] = apply_filters
        result['filtered'] = filtered_count
        
        return result
