"""
프리셋 정의 및 로더
==================

모든 파라미터 프리셋 정의 및 JSON 로드/저장 기능
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


# =============================================================================
# 기본 프리셋 (검증됨)
# =============================================================================

# 샌드박스 ORIGINAL (83.8% 승률, 안정적)
SANDBOX_PARAMS: Dict[str, Any] = {
    'atr_mult': 1.5,
    'trail_start': 1.2,
    'trail_dist': 0.03,
    'tolerance': 0.10,
    'adx_min': 10,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}

# HYBRID 최적 (더 많은 거래)
HYBRID_OPTIMAL_PARAMS: Dict[str, Any] = {
    'atr_mult': 1.5,
    'trail_start': 1.2,
    'trail_dist': 0.03,
    'tolerance': 0.12,
    'adx_min': 5,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}

# 로컬 v2.3 (보수적)
LOCAL_V23_PARAMS: Dict[str, Any] = {
    'atr_mult': 1.5,
    'trail_start': 0.6,
    'trail_dist': 0.1,
    'tolerance': 0.11,
    'adx_min': 20,
    'min_vol_ratio': 0.8,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}

# 최대 수익 (공격적)
MAX_PROFIT_PARAMS: Dict[str, Any] = {
    'atr_mult': 1.5,
    'trail_start': 2.0,
    'trail_dist': 0.08,
    'tolerance': 0.12,
    'adx_min': 5,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}


# =============================================================================
# 2026-01-13 테스트 기반 최적화 프리셋
# =============================================================================

# ⭐ 필터 + ATR 최적 (수익 극대화)
# 전략: 필터로 신호 품질↑ + ATR로 손절 여유↑
# 성능: 거래 2,216 | 승률 75.0% | PnL +2,683% | MDD 13.4%
FILTER_ATR_OPTIMAL: Dict[str, Any] = {
    'atr_mult': 2.5,
    'trail_start': 1.2,
    'trail_dist': 0.03,
    'tolerance': 0.10,
    'adx_min': 10,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}

# 밸런스 최적 (승률/수익/MDD 균형)
# 성능: 거래 2,216 | 승률 72.6% | PnL +2,642% | MDD 11.0%
BALANCED_OPTIMAL: Dict[str, Any] = {
    'atr_mult': 2.0,
    'trail_start': 1.5,
    'trail_dist': 0.03,
    'tolerance': 0.10,
    'adx_min': 10,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}

# 안정형 최적 (높은 승률 + 낮은 MDD)
# 성능: 거래 2,216 | 승률 79.0% | PnL +2,521% | MDD 11.0%
STABLE_OPTIMAL: Dict[str, Any] = {
    'atr_mult': 2.0,
    'trail_start': 1.2,
    'trail_dist': 0.05,
    'tolerance': 0.10,
    'adx_min': 10,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}


# =============================================================================
# 프리셋 레지스트리
# =============================================================================

ALL_PRESETS: Dict[str, Dict[str, Any]] = {
    'sandbox': SANDBOX_PARAMS,
    'hybrid_optimal': HYBRID_OPTIMAL_PARAMS,
    'local_v23': LOCAL_V23_PARAMS,
    'max_profit': MAX_PROFIT_PARAMS,
    'filter_atr_optimal': FILTER_ATR_OPTIMAL,
    'balanced_optimal': BALANCED_OPTIMAL,
    'stable_optimal': STABLE_OPTIMAL,
}


# =============================================================================
# 프리셋 로더/저장 함수
# =============================================================================

def get_preset(name: str) -> Dict[str, Any]:
    """프리셋 이름으로 파라미터 가져오기"""
    if name not in ALL_PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(ALL_PRESETS.keys())}")
    return ALL_PRESETS[name].copy()


def list_presets() -> Dict[str, Dict[str, Any]]:
    """모든 프리셋 목록 반환"""
    return {name: params.copy() for name, params in ALL_PRESETS.items()}


def load_preset_json(filepath: str) -> Dict[str, Any]:
    """JSON 파일에서 프리셋 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('params', data)


def save_preset_json(
    filepath: str,
    params: Dict[str, Any],
    name: str = '',
    performance: Optional[Dict] = None,
    metadata: Optional[Dict] = None
) -> None:
    """프리셋을 JSON 파일로 저장"""
    data = {
        'name': name,
        'created': str(Path(filepath).stat().st_mtime) if os.path.exists(filepath) else '',
        'params': params,
    }
    if performance:
        data['performance'] = performance
    if metadata:
        data.update(metadata)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_preset_description(name: str) -> str:
    """프리셋 설명 반환"""
    descriptions = {
        'sandbox': '기본 안정형 (승률 83.8%, MDD 10.9%)',
        'hybrid_optimal': '하이브리드 최적 (거래 수 증가)',
        'local_v23': '보수적 (높은 ADX 필터)',
        'max_profit': '공격적 (높은 PnL 추구)',
        'filter_atr_optimal': '⭐ 수익 극대화 (ATR 2.5, PnL +2,683%)',
        'balanced_optimal': '밸런스형 (ATR 2.0, MDD 11%)',
        'stable_optimal': '안정형 (승률 79%, MDD 11%)',
    }
    return descriptions.get(name, 'Unknown preset')
