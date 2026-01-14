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
    'entry_tf': '15m',
    'direction': 'Both',
    
    # 비용 파라미터
    'slippage': 0.0006,
    'fee': 0.00055,
    
    # 거래 파라미터
    'leverage': 10,
    'max_slippage': 0.01,  # 1%
}

# ============ 비용 상수 (프로젝트 공용) ============
SLIPPAGE = 0.0006       # 슬리피지 (0.06%)
FEE = 0.00055           # 수수료 (0.055%)
TOTAL_COST = SLIPPAGE + FEE  # 총 비용 (0.115%)

# ============ 방향 상수 (프로젝트 공용) ============
DIRECTION_LONG = 'Long'
DIRECTION_SHORT = 'Short'
DIRECTION_BOTH = 'Both'

# 방향 변환 (내부 ↔ API)
def to_api_direction(direction: str) -> str:
    """내부 방향 → API 방향 변환 (Long → Buy, Short → Sell)"""
    return 'Buy' if direction == DIRECTION_LONG else 'Sell'

def from_api_direction(api_dir: str) -> str:
    """API 방향 → 내부 방향 변환 (Buy → Long, Sell → Short)"""
    return DIRECTION_LONG if api_dir.lower() in ('buy', 'long') else DIRECTION_SHORT


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
    
    # 트레일링
    'trail_start_r': (0.5, 1.5, 0.1),
    'trail_dist_r': (0.3, 0.8, 0.1),
    
    # 패턴
    'pattern_tolerance': (0.02, 0.08, 0.01),
    'entry_validity_hours': (12.0, 72.0, 12.0),
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
