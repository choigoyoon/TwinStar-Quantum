"""
Trading Package v2.1.0
======================

UI 연동용 통합 트레이딩 패키지 (v1.8.3 호환)

패키지 구조:
    trading/
    ├── __init__.py          ← 이 파일 (패키지 진입점)
    ├── api.py               ← UI용 API 함수
    ├── core/                ← 공통 모듈
    │   ├── constants.py     ← 상수 (비용, 타임프레임, 등급)
    │   ├── indicators.py    ← 기술적 지표 계산
    │   ├── filters.py       ← 진입 필터
    │   ├── execution.py     ← 거래 시뮬레이션
    │   └── presets.py       ← 파라미터 프리셋
    ├── strategies/          ← 전략 모듈
    │   ├── base.py          ← BaseStrategy 추상 클래스
    │   ├── macd.py          ← MACD W/M 패턴
    │   └── adxdi.py         ← ADX/DI W/M 패턴
    └── backtest/            ← 백테스트/최적화
        ├── engine.py        ← BacktestEngine
        └── optimizer.py     ← Optimizer

임포트 가이드:
    # 1) 간단한 사용 (권장)
    from trading import run_backtest, MACDStrategy, SANDBOX_PARAMS
    result = run_backtest(df, strategy='macd', timeframe='1h')
    
    # 2) 전략 클래스 직접 사용
    from trading.strategies import MACDStrategy, ADXDIStrategy
    macd = MACDStrategy()
    result = macd.backtest(df, timeframe='1h')
    
    # 3) 상수/프리셋만 필요한 경우
    from trading.core import SLIPPAGE, FEE, TF_MAPPING, SANDBOX_PARAMS
    
    # 4) 백테스트 엔진 직접 사용
    from trading.backtest import BacktestEngine, Optimizer
"""

__version__ = "2.1.0"


# =============================================================================
# 1. API 함수 (UI에서 가장 많이 사용)
# =============================================================================
from .api import (
    run_backtest,
    run_optimization,
    compare_strategies,
    get_available_options,
)


# =============================================================================
# 2. 전략 클래스
# =============================================================================
from .strategies import (
    BaseStrategy,
    MACDStrategy,
    ADXDIStrategy,
    get_strategy,
    list_strategies,
)


# =============================================================================
# 3. 핵심 상수/프리셋 (자주 사용됨)
# =============================================================================
from .core import (
    # 비용
    SLIPPAGE,
    FEE,
    INITIAL_CAPITAL,
    # 타임프레임
    AVAILABLE_TIMEFRAMES,
    TF_MAPPING,
    TF_RESAMPLE_MAP,
    # 방향
    DIRECTION_LONG,
    DIRECTION_SHORT,
    DIRECTION_BOTH,
    to_api_direction,
    from_api_direction,
    # 등급
    calculate_grade,
    # 거래소
    EXCHANGE_INFO,
    # 프리셋
    SANDBOX_PARAMS,
    ALL_PRESETS,
    get_preset,
    list_presets,
    save_preset_json,
    load_preset_json,
    list_preset_files,
)


# =============================================================================
# 4. 백테스트 모듈
# =============================================================================
from .backtest import (
    BacktestEngine,
    Optimizer,
)


# =============================================================================
# __all__ - 명시적 공개 API
# =============================================================================
__all__ = [
    # 버전
    '__version__',
    # API 함수
    'run_backtest',
    'run_optimization',
    'compare_strategies',
    'get_available_options',
    # 전략
    'BaseStrategy',
    'MACDStrategy',
    'ADXDIStrategy',
    'get_strategy',
    'list_strategies',
    # 상수
    'SLIPPAGE',
    'FEE',
    'INITIAL_CAPITAL',
    'AVAILABLE_TIMEFRAMES',
    'TF_MAPPING',
    'TF_RESAMPLE_MAP',
    'DIRECTION_LONG',
    'DIRECTION_SHORT',
    'DIRECTION_BOTH',
    'to_api_direction',
    'from_api_direction',
    'calculate_grade',
    'EXCHANGE_INFO',
    # 프리셋
    'SANDBOX_PARAMS',
    'ALL_PRESETS',
    'get_preset',
    'list_presets',
    'save_preset_json',
    'load_preset_json',
    'list_preset_files',
    # 백테스트
    'BacktestEngine',
    'Optimizer',
]
