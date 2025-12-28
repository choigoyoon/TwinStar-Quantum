# strategies/strategy_loader.py
# 전략 자동 로더 - 폴더에 .py 파일 추가하면 자동 인식

from dataclasses import dataclass
from typing import Dict, List, Optional, Type
import importlib
import importlib.util
import os
import sys
import inspect

from .common.strategy_interface import BaseStrategy, StrategyConfig


@dataclass
class StrategyInfo:
    """전략 정보"""
    strategy_id: str
    name: str
    version: str
    description: str
    timeframe: str
    tier_required: str = "basic"
    win_rate: float = 0.0
    profit_factor: float = 0.0


class StrategyLoader:
    """
    전략 자동 로더
    
    사용법:
    1. strategies/ 폴더에 new_strategy.py 파일 추가
    2. BaseStrategy를 상속받은 클래스 작성
    3. 자동으로 인식됨!
    
    예시:
        # strategies/my_strategy.py
        from .common.strategy_interface import BaseStrategy, StrategyConfig
        
        class MyStrategy(BaseStrategy):
            def _init_config(self):
                return StrategyConfig(
                    strategy_id="my_strategy_v1",
                    name="My Custom Strategy",
                    ...
                )
            
            def check_signal(self, candles):
                # 신호 로직
                pass
    """
    
    def __init__(self, auto_discover: bool = True):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._strategy_info: Dict[str, StrategyInfo] = {}
        self._loaded_modules: List[str] = []
        
        if auto_discover:
            self._auto_discover_strategies()
    
    def _auto_discover_strategies(self):
        """strategies 폴더에서 모든 전략 자동 발견"""
        strategies_dir = os.path.dirname(os.path.abspath(__file__))
        
        print(f"🔍 Scanning strategies folder: {strategies_dir}")
        
        # 제외할 파일들
        exclude_files = {
            '__init__.py',
            'strategy_loader.py',
            'parameter_optimizer.py',
        }
        
        # 제외할 폴더들
        exclude_dirs = {'__pycache__', 'common'}
        
        for filename in os.listdir(strategies_dir):
            filepath = os.path.join(strategies_dir, filename)
            
            # 디렉토리 스킵
            if os.path.isdir(filepath):
                if filename not in exclude_dirs:
                    # 서브폴더도 스캔 (선택적)
                    pass
                continue
            
            # .py 파일만
            if not filename.endswith('.py'):
                continue
            
            # 제외 파일 스킵
            if filename in exclude_files:
                continue
            
            # 모듈 로드 시도
            try:
                self._load_module(filepath, filename)
            except Exception as e:
                print(f"  ⚠️ Failed to load {filename}: {e}")
        
        print(f"✅ Discovered {len(self._strategies)} strategies")
    
    def _load_module(self, filepath: str, filename: str):
        """모듈에서 BaseStrategy 상속 클래스 찾기"""
        module_name = filename[:-3]  # .py 제거
        
        # 이미 로드됨
        if module_name in self._loaded_modules:
            return
        
        # 모듈 동적 로드
        spec = importlib.util.spec_from_file_location(
            f"strategies.{module_name}",
            filepath
        )
        
        if spec is None or spec.loader is None:
            return
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"strategies.{module_name}"] = module
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            # 임포트 에러 무시 (의존성 문제 등)
            return
        
        self._loaded_modules.append(module_name)
        
        # BaseStrategy 상속 클래스 찾기
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # BaseStrategy 자체는 제외
            if obj is BaseStrategy:
                continue
            
            # BaseStrategy 상속 확인
            if issubclass(obj, BaseStrategy) and obj.__module__ == module.__name__:
                try:
                    self.register_strategy(obj)
                    print(f"  ✅ {name} → {obj().config.strategy_id}")
                except Exception as e:
                    print(f"  ⚠️ {name}: {e}")
    
    def list_all(self) -> List[str]:
        """모든 전략 ID 목록"""
        return list(self._strategy_info.keys())
    
    def get_strategy_info(self, strategy_id: str) -> Optional[StrategyInfo]:
        """전략 정보 조회"""
        return self._strategy_info.get(strategy_id)
    
    def load_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        """전략 인스턴스 로드"""
        if strategy_id in self._strategies:
            return self._strategies[strategy_id]()
        return None
    
    def register_strategy(self, strategy_class: Type[BaseStrategy]):
        """전략 등록"""
        instance = strategy_class()
        config = instance.config
        
        self._strategies[config.strategy_id] = strategy_class
        self._strategy_info[config.strategy_id] = StrategyInfo(
            strategy_id=config.strategy_id,
            name=config.name,
            version=config.version,
            description=config.description,
            timeframe=config.timeframe,
            tier_required=config.tier_required,
            win_rate=getattr(config, 'win_rate', 0.0),
            profit_factor=getattr(config, 'profit_factor', 0.0)
        )
    
    def reload(self):
        """전략 다시 로드"""
        self._strategies.clear()
        self._strategy_info.clear()
        self._loaded_modules.clear()
        self._auto_discover_strategies()


# 전역 로더 인스턴스
_global_loader = None

def get_strategy_loader() -> StrategyLoader:
    """전역 전략 로더 얻기"""
    global _global_loader
    if _global_loader is None:
        _global_loader = StrategyLoader()
    return _global_loader


if __name__ == "__main__":
    # 테스트
    loader = StrategyLoader()
    
    print("\n📋 Discovered Strategies:")
    for sid in loader.list_all():
        info = loader.get_strategy_info(sid)
        print(f"  - {sid}: {info.name} (v{info.version})")
