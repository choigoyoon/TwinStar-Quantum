"""
config/parameters.py
파라미터 Single Source of Truth (Phase 3 리팩토링)

모든 전략 파라미터는 이 파일에서만 정의합니다.
다른 모듈에서는 from config.parameters import ... 으로 사용합니다.
"""

import os
import json
from typing import Any, Optional


# ============ 기본 파라미터 (전체 프로젝트 공용) ============
# [OPTIMIZED] 중요 파라미터 중심 탐색(A-3) 결과 (2026.01.01)
# 성과: 수익 5,375% | 승률 84.3% | MDD 9.2% (3x 레버리지 기준)
DEFAULT_PARAMS = {
    # MACD 파라미터 (최적화됨)
    'macd_fast': 6,            # [OPT] 12 → 6 (매우 민감)
    'macd_slow': 18,           # [OPT] 26 → 18 (빠름)
    'macd_signal': 7,          # [OPT] 9 → 7 (민감)
    
    # EMA 필터 파라미터 (최적화됨)  
    'ema_period': 10,          # [OPT] 20 → 10 (민감)
    
    # ATR 파라미터 (최적화됨)
    'atr_mult': 1.25,          # [OPT] 2.2 → 1.25 (88.4% 프리셋 기준)
    'atr_period': 14,
    
    # RSI 파라미터 (최적화됨)
    'rsi_period': 14,          # [OPT] 14 (표준 유지)

    # ADX 파라미터 (Session 8 추가)
    'adx_period': 14,          # ADX 계산 기간 (표준)
    'adx_threshold': 25.0,     # 추세 강도 임계값 (>25: 강한 추세)
    'enable_adx_filter': False, # ADX 필터 활성화 여부 (기본 비활성)

    # 트레일링 파라미터
    'trail_start_r': 0.8,
    'trail_dist_r': 0.1,       # [OPT] 0.5 → 0.1 (88.4% 프리셋 기준)
    
    # 풀백 파라미터
    'pullback_rsi_long': 35,   # [OPT] 45 → 35 (88.4% 프리셋 기준)
    'pullback_rsi_short': 65,  # [OPT] 55 → 65 (88.4% 프리셋 기준)
    'enable_pullback': True,
    
    # 패턴 파라미터
    'pattern_tolerance': 0.05,
    'entry_validity_hours': 6.0,  # [OPT] 48 → 6 (88.4% 프리셋 기준)
    'max_adds': 1,
    'filter_tf': '4h',
    'entry_tf': '1h',  # [FIX v7.26] 15m → 1h (백테스트 기본값, 15m은 실시간용)
    'direction': 'Both',
    
    # 비용 파라미터 (v7.26.1: 진입/청산 분리)
    # 진입 (지정가 주문 - Limit/Maker)
    'entry_slippage': 0.0,      # 지정가 주문은 슬리피지 없음
    'entry_fee': 0.0002,        # Maker 수수료 0.02%
    # 청산 (시장가 주문 - Market/Taker, 손절/익절)
    'exit_slippage': 0.0006,    # 시장가 슬리피지 0.06%
    'exit_fee': 0.00055,        # Taker 수수료 0.055%
    # 레거시 필드 (하위 호환성, entry_* 값 사용)
    'slippage': 0.0,
    'fee': 0.0002,

    # 거래 파라미터
    'leverage': 10,
    'max_slippage': 0.01,  # 1%
}

# ============ 비용 상수 (프로젝트 공용) ============
# ============ SSOT: config.constants에서 임포트 ============
from config.constants.trading import (
    SLIPPAGE, FEE, TOTAL_COST,
    DIRECTION_LONG, DIRECTION_SHORT, DIRECTION_BOTH,
    to_api_direction, from_api_direction
)

# NOTE: 위 상수들은 config/constants/trading.py에서 관리됩니다 (SSOT)
# to_api_direction, from_api_direction 함수도 config/constants/trading.py에서 제공됩니다.


# ============ 최적화 범위 ============
PARAM_RANGES = {
    # MACD (start, end, step)
    'macd_fast': (4, 12, 2),
    'macd_slow': (16, 30, 2),
    'macd_signal': (5, 11, 2),
    
    # EMA
    'ema_period': (8, 30, 2),
    
    # ATR
    'atr_mult': (1.0, 3.0, 0.2),
    'atr_period': (10, 21, 1),
    
    # RSI
    'rsi_period': (10, 21, 1),
    'pullback_rsi_long': (35, 50, 5),
    'pullback_rsi_short': (50, 65, 5),

    # ADX (Session 8 추가)
    'adx_period': (10, 21, 1),
    'adx_threshold': (20.0, 30.0, 5.0),

    # 트레일링
    'trail_start_r': (0.5, 1.5, 0.1),
    'trail_dist_r': (0.3, 0.8, 0.1),
    
    # 패턴
    'pattern_tolerance': (0.02, 0.08, 0.01),
    'entry_validity_hours': (12.0, 72.0, 12.0),
}


# ============ 모드별 최적화 범위 (v7.18 - 문서 권장사항 반영) ============
#
# 배경:
# - PARAM_RANGES는 튜플 형식으로 전체 범위만 정의 (모드 구분 없음)
# - optimizer.py의 generate_*_grid() 함수들이 실제 모드별 범위를 하드코딩
# - SSOT 원칙 위반: 모드별 범위가 optimizer.py에 중복 정의됨
#
# 목적:
# - 모드별 파라미터 범위를 config/ 모듈로 중앙화 (SSOT 복원)
# - filter_tf 범위 추가 (기존 누락)
# - entry_validity_hours 범위에 기본값 6.0 포함
#
# 조합 수 변화:
# - Quick:    4개 → 8개 (2×2×1×2)
# - Standard: 32개 → 60개
# - Deep:     ~540개 → ~1,080개
#
PARAM_RANGES_BY_MODE = {
    # 필터 타임프레임 (문자열 리스트)
    'filter_tf': {
        'quick': ['12h', '1d'],              # 문서 권장: 긴 TF로 필터 강화
        'standard': ['4h', '6h', '12h', '1d'],  # Quick ⊂ Standard 관계 유지
        'deep': ['2h', '4h', '6h', '12h', '1d']  # 전체 범위 탐색
    },

    # 진입 유효시간 (시간 단위)
    'entry_validity_hours': {
        'quick': [48, 72],                    # 문서 권장: 48~96h
        'standard': [6, 12, 24, 48, 72],      # 기본값 6.0 포함
        'deep': [6, 12, 24, 36, 48, 72, 96]   # 96h 추가
    },

    # ATR 배수 (손절 거리)
    'atr_mult': {
        'quick': [1.25, 2.0],                 # DEFAULT_PARAMS 포함
        'standard': [1.25, 1.5, 2.0, 2.5],
        'deep': [1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
    },

    # 트레일링 시작 배수
    'trail_start_r': {
        'quick': [1.0, 1.5],
        'standard': [1.0, 1.5, 2.0, 2.5],
        'deep': [0.8, 1.0, 1.5, 2.0, 2.5, 3.0]
    },

    # 트레일링 간격
    'trail_dist_r': {
        'quick': [0.2],
        'standard': [0.2, 0.3],
        'deep': [0.15, 0.2, 0.25, 0.3],
        'fine': [0.015, 0.018, 0.02, 0.022, 0.025, 0.03, 0.04, 0.05]  # Phase 1 영향도 분석 기준
    },
}


# ============ Fine-Tuning 범위 (영향도 기반 탐색) ============
# 배경: bybit_BTCUSDT_1h_optimal_phase1.json (Sharpe 29.81, 승률 86.7%, MDD 3.7%)
#
# 영향도 순위 (Phase 1 분석):
# 1. filter_tf: 4.01 (최고) → 넓게 탐색
# 2. trail_start_r: 3.51 → 넓게 탐색
# 3. trail_dist_r: 2.47 → 넓게 탐색
# 4. atr_mult: 1.15 (낮음) → 최적값만 고정
#
# 목표 필터:
# - MDD ≤ 20%
# - 승률 ≥ 85%
# - 거래당 평균 ≥ 0.5%
#
# 조합 수: 5 × 8 × 8 × 1 = 320개 (~2분, 8워커 기준)
FINE_TUNING_RANGES = {
    # Top 1: filter_tf (영향도 4.01, 최고)
    'filter_tf': ['2h', '3h', '4h', '6h', '12h'],  # 5개 (넓은 범위)

    # Top 2: trail_start_r (영향도 3.51)
    'trail_start_r': [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2],  # 8개 (넓은 범위)

    # Top 3: trail_dist_r (영향도 2.47)
    'trail_dist_r': [0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.07, 0.1],  # 8개 (넓은 범위)

    # Top 4: atr_mult (영향도 1.15, 낮음) → 최적값만
    'atr_mult': [0.5]  # 1개 (프리셋 최적값 고정)
}


def get_param_range_by_mode(key: str, mode: str = 'standard') -> list | None:
    """
    모드별 파라미터 범위 조회

    Args:
        key: 파라미터 키 (예: 'filter_tf', 'entry_validity_hours')
        mode: 최적화 모드 ('quick', 'standard', 'deep')

    Returns:
        파라미터 값 리스트 또는 None

    Examples:
        >>> get_param_range_by_mode('filter_tf', 'quick')
        ['12h', '1d']

        >>> get_param_range_by_mode('entry_validity_hours', 'deep')
        [6, 12, 24, 36, 48, 72, 96]
    """
    if key not in PARAM_RANGES_BY_MODE:
        return None

    mode_lower = mode.lower()
    if mode_lower not in PARAM_RANGES_BY_MODE[key]:
        return PARAM_RANGES_BY_MODE[key].get('standard')  # 기본값

    return PARAM_RANGES_BY_MODE[key][mode_lower]


# ============ 거래소별 파라미터 범위 (v7.23 - 수수료 기반) ============

def get_atr_range_by_exchange(exchange: str, mode: str = 'standard') -> list[float]:
    """
    거래소별 ATR 범위 반환 (수수료 기반 자동 조정)

    원칙:
    - 수수료 높음 → ATR 넓게 (손절 여유) → 거래 빈도 ↓
    - 수수료 낮음 → ATR 좁게 (빠른 손절) → 거래 빈도 ↑

    Args:
        exchange: 거래소명 ('bybit', 'binance', 'lighter', etc.)
        mode: 최적화 모드 ('quick', 'standard', 'deep', 'coarse')

    Returns:
        ATR 배수 리스트

    Examples:
        >>> get_atr_range_by_exchange('bybit', 'standard')
        [1.5, 2.0, 2.5, 3.0]  # 높은 수수료 → 넓은 ATR

        >>> get_atr_range_by_exchange('binance', 'standard')
        [1.0, 1.25, 1.5, 2.0]  # 낮은 수수료 → 좁은 ATR

        >>> get_atr_range_by_exchange('lighter', 'standard')
        [0.5, 1.0, 1.25, 1.5]  # 매우 낮은 수수료 → 매우 좁은 ATR

    Note:
        - 수수료 임계값: 0.001 (0.1%)
        - Bybit (0.115%) → 높은 수수료 범위
        - Binance (0.1%) → 경계선 (낮은 수수료 범위)
        - Lighter (0.07%) → 낮은 수수료 범위
    """
    from config.constants.trading import get_total_cost

    total_cost = get_total_cost(exchange)

    # 수수료 임계값: 0.001 (0.1%)
    if total_cost > 0.001:  # 높은 수수료 (Bybit, Bitget)
        base_ranges = {
            'quick': [1.5, 2.5],
            'standard': [1.5, 2.0, 2.5, 3.0],
            'deep': [1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
            'coarse': [1.5, 2.5, 3.5]  # Coarse Grid용
        }
    else:  # 낮은 수수료 (Binance, Lighter, OKX)
        base_ranges = {
            'quick': [1.0, 2.0],
            'standard': [1.0, 1.25, 1.5, 2.0],
            'deep': [0.5, 1.0, 1.25, 1.5, 2.0, 2.5],
            'coarse': [1.0, 2.0, 3.0]  # Coarse Grid용
        }

    return base_ranges.get(mode, base_ranges['standard'])


def get_filter_tf_range_by_exchange(exchange: str, mode: str = 'standard') -> list[str]:
    """
    거래소별 필터 타임프레임 범위 반환 (수수료 기반 자동 조정)

    원칙:
    - 수수료 높음 → 필터 강화 (긴 TF) → 거래 빈도 ↓ (0.3~0.5회/일)
    - 수수료 낮음 → 필터 완화 (짧은 TF) → 거래 빈도 ↑ (0.8~1.5회/일)

    Args:
        exchange: 거래소명
        mode: 최적화 모드 ('quick', 'standard', 'deep', 'coarse')

    Returns:
        필터 타임프레임 리스트

    Examples:
        >>> get_filter_tf_range_by_exchange('bybit', 'standard')
        ['12h', '1d']  # 높은 수수료 → 강한 필터 → 거래 적게

        >>> get_filter_tf_range_by_exchange('binance', 'standard')
        ['4h', '6h', '12h']  # 낮은 수수료 → 약한 필터 → 거래 많이

        >>> get_filter_tf_range_by_exchange('lighter', 'deep')
        ['2h', '4h', '6h', '12h']  # 매우 낮은 수수료 → 매우 약한 필터

    Note:
        - filter_tf가 길수록 필터가 강함 (상위 타임프레임 추세 확인)
        - 수수료 높으면 거래를 적게 해야 손익분기점 돌파 가능
        - 수수료 낮으면 거래를 많이 해도 수익성 유지 가능
    """
    from config.constants.trading import get_total_cost

    total_cost = get_total_cost(exchange)

    if total_cost > 0.001:  # 높은 수수료
        # 강한 필터 → 거래 적게 (0.3~0.5회/일)
        base_ranges = {
            'quick': ['12h', '1d'],
            'standard': ['12h', '1d'],
            'deep': ['6h', '12h', '1d'],
            'coarse': ['12h', '1d']  # Coarse Grid용
        }
    else:  # 낮은 수수료
        # 약한 필터 → 거래 많이 (0.8~1.5회/일)
        base_ranges = {
            'quick': ['4h', '6h'],
            'standard': ['4h', '6h', '12h'],
            'deep': ['2h', '4h', '6h', '12h'],
            'coarse': ['4h', '12h']  # Coarse Grid용
        }

    return base_ranges.get(mode, base_ranges['standard'])


# ============ 최적화 필터 기준 (SSOT) ============
# 사용자 목표:
# - 승률 ≥ 80%
# - MDD ≤ 20%
# - 전체 단리 수익률 ≥ 0.5%
# - 일평균 거래 빈도 ≥ 0.5회/일 (2일 1회)
OPTIMIZATION_FILTER = {
    'min_win_rate': 80.0,           # 승률 ≥ 80%
    'max_mdd': 20.0,                # MDD ≤ 20%
    'min_total_return': 0.5,        # 전체 단리 수익률 ≥ 0.5%
    'min_trades_per_day': 0.5,      # 일평균 거래 빈도 ≥ 0.5회/일
    'min_absolute_trades': 10       # 절대 최소 거래수 (샘플 크기)
}


# ============ 전략별 지표 파라미터 (MACD vs ADX) ============
# Phase 2: 전략 분리를 위한 지표별 파라미터 정의
STRATEGY_INDICATOR_PARAMS = {
    'macd': {
        'macd_fast': {
            'quick': [6],
            'standard': [6, 8],
            'deep': [6, 8, 12]
        },
        'macd_slow': {
            'quick': [18],
            'standard': [18, 21],
            'deep': [18, 21, 26]
        },
        'macd_signal': {
            'quick': [7],
            'standard': [7, 9],
            'deep': [7, 9, 11]
        },
    },
    'adx': {
        'adx_period': {
            'quick': [14],
            'standard': [14, 21],
            'deep': [14, 21, 28]
        },
        'adx_threshold': {
            'quick': [25],
            'standard': [20, 25],
            'deep': [20, 25, 30]
        },
        'di_threshold': {
            'quick': [20],
            'standard': [20, 25],
            'deep': [20, 25, 30]
        },
    }
}


# ============ 최적화 모드 정의 (v7.25 - Fine-Tuning 추가) ============
# Standard 모드 제거 (v7.21): Quick/Deep으로 충분, Meta가 가장 효율적
OPTIMIZATION_MODES = {
    'fine': {
        'name': '🎯 Fine-Tuning (영향도 기반 탐색)',
        'description': '영향도 높은 3개 파라미터 넓게 탐색 + 목표 필터 (MDD≤20%, 승률≥85%, 거래당≥0.5%)',
        'method': 'fine_tuning',
        'combinations': 320,
        'time_estimate': '~2분',
        'use_case': '목표 지표 달성 조합 탐색',
        'output': 'best_params.json',
        'target_filters': {
            'mdd': {'max': 20.0},
            'win_rate': {'min': 85.0},
            'avg_pnl': {'min': 0.5}
        },
        'baseline': {
            'atr_mult': 0.5,
            'filter_tf': '2h',
            'trail_start_r': 0.4,
            'trail_dist_r': 0.02,
            'sharpe': 29.81,
            'win_rate': 86.7,
            'mdd': 3.7
        }
    },
    'meta': {
        'name': '🔍 Meta (자동 범위 탐색)',
        'description': '3,000개 조합을 20초에 실행하여 최적 범위 자동 추출',
        'method': 'meta_optimization',
        'sample_size': 3000,
        'time_estimate': '~20초',
        'use_case': '심볼별 자동 파라미터 범위 추출',
        'output': 'extracted_ranges.json + best_params.json'
    },
    'quick': {
        'name': '⚡ Quick (빠른 검증)',
        'description': 'Meta 추출 범위의 양 끝만 테스트 (검증용)',
        'method': 'use_extracted_ranges',
        'density': 'endpoints',
        'time_estimate': '~2분',
        'use_case': 'Meta 결과 빠른 검증',
        'requires': 'meta_results'
    },
    'deep': {
        'name': '🔬 Deep (세부 최적화)',
        'description': 'Meta 추출 범위 전체 탐색 (최종 파라미터)',
        'method': 'use_extracted_ranges',
        'density': 'full',
        'time_estimate': '~2분',
        'use_case': '정밀 최적화 필요 시',
        'requires': 'meta_results'
    }
}

# ============ 필수 파라미터 (최적화 결과 필수) ============
REQUIRED_PARAMS = ['atr_mult', 'trail_start_r', 'trail_dist_r']


# ============ 파라미터 접근 함수 ============

def get_param(key: str, preset: Optional[dict] = None, default: Any = None) -> Any:
    """
    파라미터 조회 (프리셋 > 기본값 > default)
    
    Args:
        key: 파라미터 키
        preset: 프리셋 딕셔너리 (옵션)
        default: 기본값 (옵션)
    
    Returns:
        파라미터 값
    """
    if preset and key in preset:
        return preset[key]
    if key in DEFAULT_PARAMS:
        return DEFAULT_PARAMS[key]
    return default


def get_all_params(preset: Optional[dict] = None) -> dict:
    """
    전체 파라미터 반환 (프리셋으로 오버라이드)
    
    Args:
        preset: 프리셋 딕셔너리 (옵션)
    
    Returns:
        완전한 파라미터 딕셔너리
    """
    params = DEFAULT_PARAMS.copy()
    if preset:
        params.update(preset)
    return params


def validate_params(params: dict) -> tuple:
    """
    필수 파라미터 검증
    
    Args:
        params: 검증할 파라미터 딕셔너리
    
    Returns:
        (is_valid, missing_keys)
    """
    missing = [k for k in REQUIRED_PARAMS if k not in params or params.get(k) is None]
    return len(missing) == 0, missing


def get_param_range(key: str) -> Optional[tuple]:
    """
    파라미터 최적화 범위 조회
    
    Args:
        key: 파라미터 키
    
    Returns:
        (start, end, step) 또는 None
    """
    return PARAM_RANGES.get(key)


# ============ JSON 설정 로드/저장 ============

def _get_config_path() -> str:
    """설정 파일 경로"""
    try:
        from paths import Paths
        return os.path.join(str(Paths.USER_CONFIG), 'strategy_params.json')
    except ImportError:
        return os.path.join(os.path.dirname(__file__), 'strategy_params.json')


def load_params_from_json(config_path: Optional[str] = None) -> dict:
    """
    JSON 파일에서 파라미터 로드 (없으면 DEFAULT_PARAMS 반환)
    
    Args:
        config_path: 설정 파일 경로 (옵션)
    
    Returns:
        파라미터 딕셔너리
    """
    path = config_path or _get_config_path()
    
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            # DEFAULT_PARAMS 기반으로 업데이트 (누락된 키 보완)
            merged = DEFAULT_PARAMS.copy()
            merged.update(loaded)
            return merged
        except Exception as e:
            print(f"[WARN] JSON 설정 로드 실패: {e}")
    
    return DEFAULT_PARAMS.copy()


def save_params_to_json(params: dict, config_path: Optional[str] = None) -> bool:
    """
    파라미터를 JSON 파일로 저장
    
    Args:
        params: 저장할 파라미터
        config_path: 설정 파일 경로 (옵션)
    
    Returns:
        성공 여부
    """
    path = config_path or _get_config_path()
    
    try:
        config_dir = os.path.dirname(path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(params, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR] JSON 저장 실패: {e}")
        return False


# ============ 편의 함수 ============

def get_indicator_params(preset: Optional[dict] = None) -> dict:
    """지표 관련 파라미터만 추출"""
    all_params = get_all_params(preset)
    keys = ['macd_fast', 'macd_slow', 'macd_signal', 'ema_period', 
            'atr_period', 'atr_mult', 'rsi_period']
    return {k: all_params[k] for k in keys if k in all_params}


def get_trading_params(preset: Optional[dict] = None) -> dict:
    """거래 관련 파라미터만 추출"""
    all_params = get_all_params(preset)
    keys = ['leverage', 'slippage', 'fee', 'max_slippage', 
            'trail_start_r', 'trail_dist_r', 'direction']
    return {k: all_params[k] for k in keys if k in all_params}


def get_pattern_params(preset: Optional[dict] = None) -> dict:
    """패턴 관련 파라미터만 추출"""
    all_params = get_all_params(preset)
    keys = ['pattern_tolerance', 'entry_validity_hours', 'max_adds',
            'filter_tf', 'entry_tf']
    return {k: all_params[k] for k in keys if k in all_params}


# ============ 타임프레임 계층 검증 (v7.25) ============

# 타임프레임 순서 (SSOT)
TIMEFRAME_ORDER = ['15m', '30m', '1h', '2h', '3h', '4h', '6h', '8h', '12h', '1d', '1w']

# 타임프레임 계층 (entry_tf → 유효한 filter_tf)
TIMEFRAME_HIERARCHY = {
    '15m': ['30m', '1h', '2h', '4h', '6h', '12h', '1d'],
    '1h': ['2h', '4h', '6h', '12h', '1d'],
    '4h': ['12h', '1d', '1w'],
}


def get_valid_filter_tfs(entry_tf: str) -> list[str]:
    """진입 TF보다 큰 필터 TF 목록 반환

    Args:
        entry_tf: 진입 타임프레임 (예: '1h')

    Returns:
        유효한 필터 TF 리스트

    Examples:
        >>> get_valid_filter_tfs('1h')
        ['2h', '4h', '6h', '12h', '1d']

        >>> get_valid_filter_tfs('15m')
        ['30m', '1h', '2h', '4h', '6h', '12h', '1d']
    """
    return TIMEFRAME_HIERARCHY.get(entry_tf, ['4h', '6h'])


def validate_tf_hierarchy(entry_tf: str, filter_tf: str) -> bool:
    """filter_tf > entry_tf 검증

    Args:
        entry_tf: 진입 타임프레임
        filter_tf: 필터 타임프레임

    Returns:
        유효 여부 (True: filter_tf > entry_tf)

    Examples:
        >>> validate_tf_hierarchy('1h', '4h')
        True

        >>> validate_tf_hierarchy('1h', '15m')
        False
    """
    if entry_tf not in TIMEFRAME_ORDER or filter_tf not in TIMEFRAME_ORDER:
        return False

    entry_idx = TIMEFRAME_ORDER.index(entry_tf)
    filter_idx = TIMEFRAME_ORDER.index(filter_tf)

    return filter_idx > entry_idx


# ============ 민감도 기반 Fine-Tuning 가중치 (v7.26) ============
PARAMETER_SENSITIVITY_WEIGHTS = {
    'filter_tf': {
        'type': 'categorical',
        'expand_steps': 2,              # 전후 2단계 (총 5개)
        'correlation': 4.01,
        'timeframe_order': ['1h', '2h', '3h', '4h', '6h', '8h', '12h', '1d', '2d']
    },
    'trail_start_r': {
        'type': 'numeric',
        'expand_pct': 0.30,             # ±30% (기존 ±15%)
        'n_points': 9,                   # 7 → 9개
        'min_value': 0.2,
        'max_value': 1.5,
        'correlation': 3.51
    },
    'trail_dist_r': {
        'type': 'numeric',
        'expand_pct': 0.25,             # ±25% (기존 ±20%)
        'n_points': 7,
        'min_value': 0.01,
        'max_value': 0.12,
        'correlation': 2.47
    },
    'atr_mult': {
        'type': 'numeric',
        'expand_pct': 0.15,             # ±15% (기존 ±20%)
        'n_points': 5,                   # 7 → 5개 (축소)
        'min_value': 0.3,
        'max_value': 3.0,
        'correlation': 1.15
    },
    'entry_validity_hours': {
        'type': 'numeric',
        'fixed': True,
        'correlation': 0.80
    }
}


# ============ 파라미터 상호작용 규칙 (v7.26) ============
PARAMETER_INTERACTION_RULES = {
    # Rule 1: 손절-익절 조화
    'atr_trail_harmony': {
        'params': ['atr_mult', 'trail_start_r'],
        'min': 0.5,
        'max': 2.5,
        'description': 'atr_mult × trail_start_r ∈ [0.5, 2.5]'
    },

    # Rule 2: 필터-진입 균형
    'filter_entry_balance': {
        'params': ['filter_tf', 'entry_validity_hours'],
        'mapping': {
            '12h': {'max_hours': 24},
            '1d': {'max_hours': 48}
        },
        'description': '긴 필터는 짧은 진입 유효시간'
    },

    # Rule 3: 익절 시작-간격 균형
    'trail_ratio_balance': {
        'params': ['trail_start_r', 'trail_dist_r'],
        'min_ratio': 3.0,
        'max_ratio': 20.0,
        'description': 'trail_start_r / trail_dist_r ∈ [3, 20]'
    }
}


if __name__ == '__main__':
    # 테스트
    print("=== Parameters Test ===\n")
    
    # 1. 기본값 확인
    print(f"1. DEFAULT_PARAMS keys: {len(DEFAULT_PARAMS)}")
    print(f"   atr_mult: {get_param('atr_mult')}")
    
    # 2. 프리셋 오버라이드
    preset = {'atr_mult': 2.5, 'leverage': 5}
    print(f"\n2. With preset: atr_mult={get_param('atr_mult', preset)}, leverage={get_param('leverage', preset)}")
    
    # 3. 전체 파라미터
    all_p = get_all_params(preset)
    print(f"\n3. All params: {len(all_p)} keys")
    
    # 4. 검증
    valid, missing = validate_params(DEFAULT_PARAMS)
    print(f"\n4. Validation: valid={valid}, missing={missing}")
    
    # 5. 최적화 범위
    atr_range = get_param_range('atr_mult')
    print(f"\n5. atr_mult range: {atr_range}")
    
    # 6. 그룹별 파라미터
    print(f"\n6. Indicator params: {list(get_indicator_params().keys())}")
    print(f"   Trading params: {list(get_trading_params().keys())}")
    print(f"   Pattern params: {list(get_pattern_params().keys())}")
    
    print("\n✅ All tests passed!")
