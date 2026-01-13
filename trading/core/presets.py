"""
프리셋 관리
==========

v1.8.3 형식 호환 프리셋 저장/로드
- JSON 파일 저장/로드
- 메타정보 (_meta, _result) 포함
- config/presets/ 폴더 호환
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


# =============================================================================
# 기본 프리셋 (계산용)
# =============================================================================
SANDBOX_PARAMS: Dict = {
    'atr_mult': 1.5,
    'trail_start': 1.2,
    'trail_dist': 0.03,
    'tolerance': 0.10,
    'adx_min': 10,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}

FILTER_ATR_OPTIMAL: Dict = {
    'atr_mult': 2.0,
    'trail_start': 1.3,
    'trail_dist': 0.025,
    'tolerance': 0.08,
    'adx_min': 15,
    'stoch_long_max': 60,
    'stoch_short_min': 40,
    'use_downtrend_filter': True,
}

BALANCED_OPTIMAL: Dict = {
    'atr_mult': 1.8,
    'trail_start': 1.2,
    'trail_dist': 0.02,
    'tolerance': 0.12,
    'adx_min': 12,
    'stoch_long_max': 55,
    'stoch_short_min': 45,
    'use_downtrend_filter': True,
}

STABLE_OPTIMAL: Dict = {
    'atr_mult': 1.6,
    'trail_start': 1.1,
    'trail_dist': 0.018,
    'tolerance': 0.10,
    'adx_min': 10,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}

HYBRID_OPTIMAL: Dict = {
    'atr_mult': 2.2,
    'trail_start': 1.4,
    'trail_dist': 0.03,
    'tolerance': 0.08,
    'adx_min': 18,
    'stoch_long_max': 65,
    'stoch_short_min': 35,
    'use_downtrend_filter': True,
}

LOCAL_V23_PARAMS: Dict = {
    'atr_mult': 2.5,
    'trail_start': 1.5,
    'trail_dist': 0.025,
    'tolerance': 0.05,
    'adx_min': 20,
    'stoch_long_max': 70,
    'stoch_short_min': 30,
    'use_downtrend_filter': True,
}

MAX_PROFIT_PARAMS: Dict = {
    'atr_mult': 2.25,
    'trail_start': 1.5,
    'trail_dist': 0.035,
    'tolerance': 0.06,
    'adx_min': 15,
    'stoch_long_max': 60,
    'stoch_short_min': 40,
    'use_downtrend_filter': True,
}

# 내장 프리셋 모음
ALL_PRESETS: Dict[str, Dict] = {
    'sandbox': SANDBOX_PARAMS,
    'filter_atr_optimal': FILTER_ATR_OPTIMAL,
    'balanced_optimal': BALANCED_OPTIMAL,
    'stable_optimal': STABLE_OPTIMAL,
    'hybrid_optimal': HYBRID_OPTIMAL,
    'local_v23': LOCAL_V23_PARAMS,
    'max_profit': MAX_PROFIT_PARAMS,
}


# =============================================================================
# 프리셋 JSON 형식 (v1.8.3 호환)
# =============================================================================
def _convert_to_json_serializable(obj):
    """numpy 타입을 JSON 직렬화 가능한 타입으로 변환"""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_json_serializable(i) for i in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def create_preset_json(
    params: Dict,
    name: str,
    symbol: str = "BTCUSDT",
    exchange: str = "bybit",
    timeframe: str = "1h",
    strategy: str = "macd",
    result: Dict = None,
) -> Dict:
    """
    v1.8.3 형식의 프리셋 JSON 생성
    
    Args:
        params: 전략 파라미터
        name: 프리셋 이름
        symbol: 심볼 (BTCUSDT)
        exchange: 거래소 (bybit)
        timeframe: 타임프레임 (1h)
        strategy: 전략명 (macd, adxdi)
        result: 백테스트 결과 (선택)
    
    Returns:
        v1.8.3 형식 JSON 딕셔너리
    """
    from .constants import calculate_grade
    
    # numpy 타입 변환
    result = _convert_to_json_serializable(result) if result else None
    params = _convert_to_json_serializable(params)
    
    # 등급 계산
    grade = 'C'
    if result:
        win_rate = result.get('win_rate', 0)
        pf = result.get('profit_factor', 0)
        mdd = result.get('max_drawdown', result.get('mdd', 100))
        grade = calculate_grade(win_rate, pf, mdd)
    
    return {
        "_meta": {
            "symbol": symbol,
            "exchange": exchange,
            "timeframe": timeframe,
            "strategy": strategy,
            "optimized_at": datetime.now().isoformat(),
            "version": "2.0.0",
            "verified": result is not None,
            "verified_date": datetime.now().strftime("%Y-%m-%d") if result else None,
            "verification_stats": {
                "passed": result.get('win_rate', 0) >= 60 if result else False,
                "win_rate": result.get('win_rate', 0) if result else 0,
            },
            "name": name,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "_result": {
            "trades": result.get('trades', 0) if result else 0,
            "win_rate": result.get('win_rate', 0) if result else 0,
            "simple_pnl": result.get('simple_pnl', 0) if result else 0,
            "compound_pnl": result.get('compound_pnl', 0) if result else 0,
            "max_drawdown": result.get('max_drawdown', result.get('mdd', 0)) if result else 0,
            "profit_factor": result.get('profit_factor', 0) if result else 0,
            "grade": grade,
        },
        "params": params.copy(),
    }


# =============================================================================
# 프리셋 저장/로드 (config/presets/ 호환)
# =============================================================================
def _get_presets_dir() -> Path:
    """프리셋 저장 디렉토리 반환"""
    # 프로젝트 루트 기준 config/presets/
    base = Path(__file__).parent.parent.parent  # trading/core -> trading -> project
    presets_dir = base / "config" / "presets"
    presets_dir.mkdir(parents=True, exist_ok=True)
    return presets_dir


def save_preset_json(
    params: Dict,
    name: str,
    symbol: str = "BTCUSDT",
    exchange: str = "bybit",
    timeframe: str = "1h",
    strategy: str = "macd",
    result: Dict = None,
    custom_path: str = None,
) -> str:
    """
    프리셋을 JSON 파일로 저장
    
    Args:
        params: 전략 파라미터
        name: 프리셋 이름
        symbol, exchange, timeframe, strategy: 메타정보
        result: 백테스트 결과 (선택)
        custom_path: 커스텀 저장 경로 (선택)
    
    Returns:
        저장된 파일 경로
    """
    preset_data = create_preset_json(
        params, name, symbol, exchange, timeframe, strategy, result
    )
    
    if custom_path:
        path = Path(custom_path)
    else:
        path = _get_presets_dir() / f"{name}.json"
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(preset_data, f, indent=4, ensure_ascii=False)
    
    return str(path)


def load_preset_json(path_or_name: str) -> Dict:
    """
    프리셋 JSON 파일 로드
    
    Args:
        path_or_name: 파일 경로 또는 프리셋 이름
    
    Returns:
        프리셋 딕셔너리 (params, _meta, _result 포함)
    """
    # 경로인지 이름인지 판단
    if os.path.exists(path_or_name):
        path = Path(path_or_name)
    else:
        path = _get_presets_dir() / f"{path_or_name}.json"
    
    if not path.exists():
        raise FileNotFoundError(f"Preset not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def list_preset_files() -> List[str]:
    """저장된 프리셋 파일 목록"""
    presets_dir = _get_presets_dir()
    return [f.stem for f in presets_dir.glob("*.json")]


def delete_preset_file(name: str) -> bool:
    """프리셋 파일 삭제"""
    path = _get_presets_dir() / f"{name}.json"
    if path.exists():
        path.unlink()
        return True
    return False


# =============================================================================
# 프리셋 유틸리티
# =============================================================================
def get_preset(name: str) -> Dict:
    """
    프리셋 가져오기 (내장 우선, 없으면 파일)
    
    Args:
        name: 프리셋 이름
    
    Returns:
        파라미터 딕셔너리
    """
    # 내장 프리셋 확인
    if name in ALL_PRESETS:
        return ALL_PRESETS[name].copy()
    
    # 파일에서 로드 시도
    try:
        data = load_preset_json(name)
        return data.get('params', {})
    except FileNotFoundError:
        raise ValueError(f"Unknown preset: {name}. Available: {list_presets()}")


def list_presets() -> List[str]:
    """사용 가능한 모든 프리셋 목록 (내장 + 파일)"""
    builtin = list(ALL_PRESETS.keys())
    files = list_preset_files()
    return sorted(set(builtin + files))


def get_preset_description(name: str) -> str:
    """프리셋 설명 (내장) 또는 메타정보 (파일)"""
    descriptions = {
        'sandbox': "기본 프리셋 (안정형)",
        'filter_atr_optimal': "필터+ATR 최적화 (공격형)",
        'balanced_optimal': "균형 최적화 (중립형)",
        'stable_optimal': "안정 최적화 (보수형)",
        'hybrid_optimal': "하이브리드 최적화 (복합형)",
        'local_v23': "로컬 v2.3 파라미터",
        'max_profit': "최대 수익 파라미터",
    }
    
    if name in descriptions:
        return descriptions[name]
    
    # 파일에서 메타정보 로드
    try:
        data = load_preset_json(name)
        meta = data.get('_meta', {})
        result = data.get('_result', {})
        return f"{meta.get('strategy', 'unknown')} | {result.get('grade', 'C')} | WR {result.get('win_rate', 0):.1f}%"
    except:
        return "No description"


def get_preset_info(name: str) -> Dict:
    """프리셋 전체 정보 (메타 + 결과 + 파라미터)"""
    if name in ALL_PRESETS:
        return {
            '_meta': {
                'name': name,
                'strategy': 'builtin',
                'version': '2.0.0',
            },
            '_result': {},
            'params': ALL_PRESETS[name].copy(),
        }
    
    try:
        return load_preset_json(name)
    except FileNotFoundError:
        raise ValueError(f"Unknown preset: {name}")
