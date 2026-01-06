"""
strategies/base_strategy.py - 전략 기본 클래스
새 전략 추가 시 이 클래스를 상속
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd


@dataclass
class Signal:
    """거래 신호"""
    timestamp: datetime
    signal_type: str  # 'Long', 'Short'
    entry_price: float
    stop_loss: float
    pattern: str  # 'W', 'M', etc.
    confidence: float = 1.0
    metadata: Dict = None


@dataclass
class BacktestResult:
    """백테스트 결과"""
    total_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    profit_factor: float
    trades: List[Dict]


class BaseStrategy(ABC):
    """
    전략 기본 클래스
    
    새 전략을 만들려면:
    1. 이 클래스를 상속
    2. name 속성 정의
    3. check_signal() 구현
    4. run_backtest() 구현 (선택)
    
    Example:
        class MyStrategy(BaseStrategy):
            name = "my_strategy"
            
            def check_signal(self, df, params):
                # 신호 로직
                return Signal(...)
    """
    
    # 전략 이름 (필수)
    name: str = "base"
    
    # 전략 버전
    version: str = "1.0.0"
    
    # 기본 파라미터
    default_params: Dict[str, Any] = {}
    
    # 필수 파라미터 목록
    required_params: List[str] = []
    
    def __init__(self, params: Dict = None):
        """
        Args:
            params: 전략 파라미터 (None이면 default_params 사용)
        """
        self.params = {**self.default_params, **(params or {})}
        self._validate_params()
    
    def _validate_params(self):
        """필수 파라미터 검증"""
        for param in self.required_params:
            if param not in self.params:
                raise ValueError(f"필수 파라미터 누락: {param}")
    
    @abstractmethod
    def check_signal(
        self,
        df_pattern: pd.DataFrame,
        df_entry: pd.DataFrame = None,
        **kwargs
    ) -> Optional[Signal]:
        """
        신호 확인 (필수 구현)
        
        Args:
            df_pattern: 패턴 탐지용 데이터 (예: 4H)
            df_entry: 진입 타이밍용 데이터 (예: 15m)
            **kwargs: 추가 인자
            
        Returns:
            Signal 객체 또는 None
        """
        pass
    
    def run_backtest(
        self,
        df: pd.DataFrame,
        start_date: datetime = None,
        end_date: datetime = None,
        **kwargs
    ) -> Optional[BacktestResult]:
        """
        백테스트 실행 (선택 구현)
        
        기본 구현은 check_signal을 반복 호출하는 방식
        성능이 필요하면 오버라이드
        """
        # 기본 구현 (서브클래스에서 최적화 가능)
        return None
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """파라미터 조회"""
        return self.params.get(key, default)
    
    def set_param(self, key: str, value: Any):
        """파라미터 설정"""
        self.params[key] = value
    
    def describe(self) -> Dict:
        """전략 정보 반환"""
        return {
            'name': self.name,
            'version': self.version,
            'params': self.params,
            'required_params': self.required_params
        }
    
    def __repr__(self):
        return f"<Strategy: {self.name} v{self.version}>"


class StrategyRegistry:
    """전략 레지스트리 - 등록된 전략 관리"""
    
    _strategies: Dict[str, type] = {}
    
    @classmethod
    def register(cls, strategy_class: type):
        """전략 등록"""
        if not issubclass(strategy_class, BaseStrategy):
            raise TypeError("BaseStrategy를 상속해야 합니다")
        
        name = getattr(strategy_class, 'name', strategy_class.__name__)
        cls._strategies[name] = strategy_class
        return strategy_class
    
    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """전략 클래스 조회"""
        return cls._strategies.get(name)
    
    @classmethod
    def list_all(cls) -> List[str]:
        """등록된 전략 목록"""
        return list(cls._strategies.keys())
    
    @classmethod
    def create(cls, name: str, params: Dict = None) -> Optional[BaseStrategy]:
        """전략 인스턴스 생성"""
        strategy_class = cls.get(name)
        if strategy_class:
            return strategy_class(params)
        return None


def register_strategy(cls):
    """전략 등록 데코레이터"""
    StrategyRegistry.register(cls)
    return cls


if __name__ == '__main__':
    # 테스트
    @register_strategy
    class TestStrategy(BaseStrategy):
        name = "test_strategy"
        version = "1.0.0"
        default_params = {'threshold': 0.5}
        
        def check_signal(self, df_pattern, df_entry=None, **kwargs):
            return None
    
    print(f"Registered: {StrategyRegistry.list_all()}")
    
    strategy = StrategyRegistry.create("test_strategy")
    print(f"Created: {strategy}")
    print(f"Describe: {strategy.describe()}")
