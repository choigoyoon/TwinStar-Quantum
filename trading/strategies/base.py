"""
기본 전략 클래스
================

모든 전략이 상속하는 추상 클래스
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from ..core.constants import DEFAULT_SLIPPAGE, DEFAULT_FEE
from ..core.indicators import prepare_data
from ..core.presets import SANDBOX_PARAMS


class BaseStrategy(ABC):
    """
    전략 기본 클래스
    
    모든 전략은 이 클래스를 상속하고 detect_patterns()를 구현해야 함
    
    Example:
        class MyStrategy(BaseStrategy):
            name = "MyStrategy"
            
            def detect_patterns(self, df):
                # 패턴 탐지 로직
                return patterns
    """
    
    name: str = "Base"
    description: str = ""
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Args:
            params: 파라미터 딕셔너리 (None이면 기본값)
        """
        self.params = params.copy() if params else SANDBOX_PARAMS.copy()
    
    @abstractmethod
    def detect_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        패턴 탐지 (각 전략에서 구현)
        
        Args:
            df: 지표가 계산된 데이터프레임
        
        Returns:
            패턴 리스트 [{'idx', 'direction', 'entry_price', 'swing'}, ...]
        """
        pass
    
    def backtest(
        self,
        df: pd.DataFrame,
        timeframe: str = '1h',
        apply_filters: bool = True,
        slippage: float = DEFAULT_SLIPPAGE,
        fee: float = DEFAULT_FEE,
    ) -> Dict[str, Any]:
        """
        백테스트 실행
        
        Args:
            df: 원본 데이터프레임 (15분봉 등)
            timeframe: 목표 타임프레임
            apply_filters: 필터 적용 여부
            slippage: 슬리피지
            fee: 수수료
        
        Returns:
            백테스트 결과
        """
        from ..backtest.engine import BacktestEngine
        
        engine = BacktestEngine(slippage=slippage, fee=fee)
        return engine.run(df, self, timeframe, apply_filters)
    
    def optimize(
        self,
        df: pd.DataFrame,
        timeframe: str = '1h',
        mode: str = 'quick',
        apply_filters: bool = True,
        verbose: bool = True,
    ) -> List[Dict]:
        """
        최적화 실행
        
        Args:
            df: 원본 데이터프레임
            timeframe: 타임프레임
            mode: 'quick', 'default', 'deep'
            apply_filters: 필터 적용 여부
            verbose: 진행 상황 출력
        
        Returns:
            정렬된 결과 리스트
        """
        from ..backtest.optimizer import Optimizer
        
        optimizer = Optimizer()
        return optimizer.grid_search(
            df, self, timeframe, mode, apply_filters, verbose
        )
