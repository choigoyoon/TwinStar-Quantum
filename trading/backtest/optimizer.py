"""
최적화 모듈
===========

그리드 서치 기반 파라미터 최적화
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any
from itertools import product

from ..core.indicators import prepare_data
from ..core.constants import DEFAULT_SLIPPAGE, DEFAULT_FEE


class Optimizer:
    """
    파라미터 최적화기
    
    Example:
        optimizer = Optimizer()
        results = optimizer.grid_search(df, strategy, '1h', mode='quick')
    """
    
    # 모드별 그리드 범위
    GRID_RANGES = {
        'quick': {
            'atr_mult': [1.5, 2.0, 2.5],
            'trail_start': [1.0, 1.2, 1.5],
            'trail_dist': [0.02, 0.03],
            'tolerance': [0.08, 0.10],
            'adx_min': [10, 15],
        },
        'default': {
            'atr_mult': [1.5, 1.75, 2.0, 2.25, 2.5],
            'trail_start': [1.0, 1.1, 1.2, 1.3, 1.5],
            'trail_dist': [0.015, 0.02, 0.025, 0.03],
            'tolerance': [0.06, 0.08, 0.10, 0.12],
            'adx_min': [10, 12, 15, 18],
        },
        'deep': {
            'atr_mult': [1.5, 1.6, 1.75, 1.9, 2.0, 2.1, 2.25, 2.4, 2.5],
            'trail_start': [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
            'trail_dist': [0.01, 0.015, 0.02, 0.025, 0.03, 0.035],
            'tolerance': [0.05, 0.06, 0.08, 0.10, 0.12, 0.15],
            'adx_min': [8, 10, 12, 15, 18, 20],
        },
    }
    
    def __init__(
        self,
        slippage: float = DEFAULT_SLIPPAGE,
        fee: float = DEFAULT_FEE,
        min_trades: int = 30,
    ):
        self.slippage = slippage
        self.fee = fee
        self.min_trades = min_trades
    
    def grid_search(
        self,
        df: pd.DataFrame,
        strategy,
        timeframe: str = '1h',
        mode: str = 'quick',
        apply_filters: bool = True,
        verbose: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        그리드 서치 최적화
        
        Args:
            df: 원본 데이터프레임
            strategy: 전략 인스턴스
            timeframe: 타임프레임
            mode: 'quick', 'default', 'deep'
            apply_filters: 필터 적용 여부
            verbose: 진행 상황 출력
        
        Returns:
            정렬된 결과 리스트
        """
        from .engine import BacktestEngine
        
        # 데이터 준비 (지표 추가)
        df_tf = prepare_data(df, None)
        if len(df_tf) < 100:
            return []
        
        # 그리드 생성
        grid = self.GRID_RANGES.get(mode, self.GRID_RANGES['quick'])
        param_names = list(grid.keys())
        param_values = [grid[k] for k in param_names]
        combinations = list(product(*param_values))
        total = len(combinations)
        
        if verbose:
            print(f"[{strategy.name}] Optimization: {total} combinations ({mode})")
        
        results = []
        engine = BacktestEngine(slippage=self.slippage, fee=self.fee)
        
        for i, combo in enumerate(combinations):
            # 파라미터 설정
            test_params = strategy.params.copy()
            for name, val in zip(param_names, combo):
                test_params[name] = val
            
            # 전략 인스턴스 생성 (새 파라미터로)
            strategy_class = type(strategy)
            test_strategy = strategy_class(test_params)
            
            # 백테스트 실행
            result = engine.run(df, test_strategy, timeframe, apply_filters)
            
            if result['trades'] >= self.min_trades:
                result['params'] = test_params.copy()
                results.append(result)
            
            # 진행 상황
            if verbose and (i + 1) % 20 == 0:
                print(f"  Progress: {i+1}/{total} ({(i+1)/total*100:.0f}%)")
        
        # 정렬 (simple_pnl 기준)
        results.sort(key=lambda x: x['simple_pnl'], reverse=True)
        
        if verbose:
            print(f"  Complete: {len(results)} valid results")
        
        return results
