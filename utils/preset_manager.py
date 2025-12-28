# preset_manager.py - 통합 프리셋 관리자 V2
"""
전략 파라미터 프리셋 관리
- 새 형식: 그룹화된 스키마 (timeframes, trading, indicators, risk)
- 레거시: flat 구조 호환
- config/presets/ 폴더에 JSON 저장/로드
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# 경로 설정 (Paths 클래스 활용)
from paths import Paths

# 외부 저장용 (사용자 데이터)
BASE_DIR = Path(Paths.BASE)
CONFIG_DIR = Path(Paths.USER_CONFIG)
PRESETS_DIR = CONFIG_DIR / 'presets'
LEGACY_PARAMS_FILE = CONFIG_DIR / 'strategy_params.json'

# 내부 번들용 (읽기 전용 자원)
INTERNAL_CONFIG = Path(Paths.CONFIG)
INTERNAL_PRESETS = INTERNAL_CONFIG / 'presets'

# ==================== 새 스키마 V2 ====================
DEFAULT_PARAMS_V2 = {
    "_meta": {
        "name": "Default",
        "type": "preset",
        "version": "2.0",
        "created": None,
        "updated": None
    },
    "timeframes": {
        "filter_tf": "4h",
        "trend_interval": "1h",
        "entry_tf": "15min"
    },
    "trading": {
        "leverage": 3,
        "direction": "Both"
    },
    "indicators": {
        "rsi_period": 21,
        "atr_mult": 1.25,
        "pullback_rsi_long": 40,
        "pullback_rsi_short": 60,
        "pattern_tolerance": 0.05
    },
    "risk": {
        "trail_start_r": 1.0,
        "trail_dist_r": 0.2,
        "max_adds": 1,
        "entry_validity_hours": 4.0
    },
    "fixed": {
        "slippage_pct": 0.05,
        "fee_pct": 0.055
    },
    "results": {}
}

# ==================== 레거시 Flat 구조 ====================
DEFAULT_PARAMS_FLAT = {
    "_description": "Default Strategy Parameters",
    "_updated": None,
    "atr_mult": 1.25,
    "trail_start_r": 1.0,
    "trail_dist_r": 0.2,
    "pattern_tolerance": 0.05,
    "entry_validity_hours": 4.0,
    "pullback_rsi_long": 40,
    "pullback_rsi_short": 60,
    "rsi_period": 21,
    "max_adds": 1,
    "trend_interval": "1h",
    "entry_tf": "15min",
    "filter_tf": "4h",
    "leverage": 3,
    "direction": "Both"
}


class PresetManager:
    """전략 파라미터 프리셋 관리자 V2"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._ensure_dirs()
        self._ensure_default()
        self._cache = {}
    
    def _ensure_dirs(self):
        """디렉토리 생성"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _ensure_default(self):
        """기본 프리셋 생성 (V2 형식)"""
        default_path = PRESETS_DIR / '_default.json'
        if not default_path.exists():
            data = DEFAULT_PARAMS_V2.copy()
            data['_meta']['created'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_json(default_path, data)
            print(f"[PresetManager] 기본 프리셋 생성: {default_path}")
    
    def _save_json(self, path: Path, data: Dict) -> bool:
        """JSON 저장"""
        try:
            if '_meta' in data:
                data['_meta']['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elif '_updated' in data or isinstance(data, dict):
                data['_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[PresetManager] 저장 실패: {e}")
            return False
    
    def _load_json(self, path: Path) -> Dict:
        """JSON 로드"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            print(f"[PresetManager] JSON 파싱 오류: {e}")
            return {}
    
    # ==================== 형식 변환 ====================
    
    def _is_v2_format(self, data: Dict) -> bool:
        """V2 형식인지 확인"""
        return 'timeframes' in data or '_meta' in data
    
    def _convert_legacy_to_v2(self, legacy: Dict) -> Dict:
        """레거시 flat → V2 형식 변환"""
        return {
            "_meta": {
                "name": legacy.get('_description', 'Converted'),
                "type": "preset",
                "version": "2.0",
                "created": legacy.get('_updated'),
                "updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            "timeframes": {
                "filter_tf": legacy.get('filter_tf', '4h'),
                "trend_interval": legacy.get('trend_interval', '1h'),
                "entry_tf": legacy.get('entry_tf', '15min')
            },
            "trading": {
                "leverage": int(legacy.get('leverage', 3)),
                "direction": legacy.get('direction', 'Both')
            },
            "indicators": {
                "rsi_period": int(legacy.get('rsi_period', 21)),
                "atr_mult": float(legacy.get('atr_mult', 1.25)),
                "pullback_rsi_long": int(legacy.get('pullback_rsi_long', 40)),
                "pullback_rsi_short": int(legacy.get('pullback_rsi_short', 60)),
                "pattern_tolerance": float(legacy.get('pattern_tolerance', 0.05))
            },
            "risk": {
                "trail_start_r": float(legacy.get('trail_start_r', 1.0)),
                "trail_dist_r": float(legacy.get('trail_dist_r', 0.2)),
                "max_adds": int(legacy.get('max_adds', 1)),
                "entry_validity_hours": float(legacy.get('entry_validity_hours', 4.0))
            },
            "fixed": {
                "slippage_pct": float(legacy.get('slippage_pct', 0.05)),
                "fee_pct": float(legacy.get('fee_pct', 0.055))
            },
            "results": legacy.get('results', {})
        }
    
    def _flatten(self, data: Dict) -> Dict:
        """V2 형식 → flat 형식 변환 (봇 호환)"""
        
        # 최적화 저장 형식 처리 (params 키)
        if 'params' in data:
            result = data['params'].copy()
            # _meta 정보도 추가
            if '_meta' in data:
                result['_description'] = data['_meta'].get('symbol', '')
                result['_updated'] = data['_meta'].get('created', '')
            return result
        
        if not self._is_v2_format(data):
            return data  # 이미 flat
        
        flat = {}
        for section in ['timeframes', 'trading', 'indicators', 'risk', 'fixed']:
            if section in data:
                flat.update(data[section])
        
        # _meta 정보 일부 추가
        if '_meta' in data:
            flat['_description'] = data['_meta'].get('name', '')
            flat['_updated'] = data['_meta'].get('updated', '')
        
        return flat
    
    # ==================== 메인 API ====================
    
    def load_preset(self, name: str = '_default') -> Dict:
        """
        프리셋 로드 (V2 형식 반환)
        
        Args:
            name: 프리셋 이름 (예: '_default', 'btc_1h', 'eth_4h')
        
        Returns:
            V2 형식 파라미터 dict
        """
        # [REMOVED] 실시간 반영을 위해 캐시 체크 제거
        # if name in self._cache:
        #     return self._cache[name].copy()
        
        preset_path = PRESETS_DIR / f'{name}.json'
        internal_path = INTERNAL_PRESETS / f'{name}.json'
        
        target_path = None
        if preset_path.exists():
            target_path = preset_path
        elif internal_path.exists():
            target_path = internal_path
            print(f"[PresetManager] Using bundled preset: {name}")
        
        if target_path:
            data = self._load_json(target_path)
            if self._is_v2_format(data):
                result = data
            else:
                result = self._convert_legacy_to_v2(data)
        else:
            # 레거시 strategy_params.json 시도
            if LEGACY_PARAMS_FILE.exists():
                data = self._load_json(LEGACY_PARAMS_FILE)
                result = self._convert_legacy_to_v2(data)
            else:
                result = DEFAULT_PARAMS_V2.copy()
        
        self._cache[name] = result
        return result.copy()
    
    def load_preset_flat(self, name: str = '_default') -> Dict:
        """
        프리셋 로드 (flat 형식 - 봇/백테스트 호환)
        
        Returns:
            flat 형식 파라미터 dict
        """
        data = self.load_preset(name)
        return self._flatten(data)
    
    def save_preset(self, name: str, params: Dict) -> bool:
        """
        프리셋 저장 (V2 형식)
        
        Args:
            name: 프리셋 이름
            params: 파라미터 dict (V2 또는 flat)
        
        Returns:
            성공 여부
        """
        preset_path = PRESETS_DIR / f'{name}.json'
        
        # flat 형식이면 V2로 변환
        if not self._is_v2_format(params):
            params = self._convert_legacy_to_v2(params)
        
        # 이름 설정
        if '_meta' in params:
            params['_meta']['name'] = name
        
        if self._save_json(preset_path, params):
            self._cache[name] = params
            print(f"[PresetManager] 프리셋 저장: {name}")
            return True
        return False
    
    def save_strategy_params(self, params: Dict) -> bool:
        """
        기존 strategy_params.json에 저장 (레거시 호환)
        """
        # V2 형식이면 flat으로 변환
        if self._is_v2_format(params):
            flat_params = self._flatten(params)
        else:
            flat_params = params.copy()
        
        existing = self._load_json(LEGACY_PARAMS_FILE) if LEGACY_PARAMS_FILE.exists() else {}
        existing.update(flat_params)
        return self._save_json(LEGACY_PARAMS_FILE, existing)
    
    def load_strategy_params(self) -> Dict:
        """
        기존 strategy_params.json 로드 (레거시 호환, flat 형식)
        """
        if LEGACY_PARAMS_FILE.exists():
            params = self._load_json(LEGACY_PARAMS_FILE)
            return {**DEFAULT_PARAMS_FLAT, **params}
        return DEFAULT_PARAMS_FLAT.copy()
    
    def list_presets(self) -> list:
        """사용 가능한 프리셋 목록 (사용자 + 내부 번들)"""
        presets = set()
        
        # 1. 사용자 프리셋 (수정 가능)
        if PRESETS_DIR.exists():
            for f in PRESETS_DIR.glob('*.json'):
                presets.add(f.stem)
        
        # 2. 내부 번들 프리셋 (읽기 전용)
        if INTERNAL_PRESETS.exists():
            for f in INTERNAL_PRESETS.glob('*.json'):
                presets.add(f.stem)
                
        return sorted(list(presets))
    
    def delete_preset(self, name: str) -> bool:
        """프리셋 삭제 (기본 프리셋 제외)"""
        if name == '_default':
            print("[PresetManager] 기본 프리셋은 삭제 불가")
            return False
        
        preset_path = PRESETS_DIR / f'{name}.json'
        try:
            if preset_path.exists():
                preset_path.unlink()
                if name in self._cache:
                    del self._cache[name]
                return True
        except Exception as e:
            print(f"[PresetManager] 삭제 실패: {e}")
        return False
    
    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()


# ==================== 싱글톤 인스턴스 ====================
_manager_instance = None

def get_preset_manager() -> PresetManager:
    """PresetManager 싱글톤 반환"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PresetManager()
    return _manager_instance


# ==================== 편의 함수 (레거시 호환) ====================
def load_strategy_params() -> Dict:
    """기존 코드 호환용 - strategy_params.json 로드 (flat)"""
    return get_preset_manager().load_strategy_params()


def save_strategy_params(params: Dict) -> bool:
    """기존 코드 호환용 - strategy_params.json 저장"""
    return get_preset_manager().save_strategy_params(params)


# ==================== 테스트 ====================
if __name__ == "__main__":
    print("=== PresetManager V2 Test ===")
    
    pm = get_preset_manager()
    
    # 1. 프리셋 목록
    print(f"\n1. 프리셋 목록: {pm.list_presets()}")
    
    # 2. V2 형식 로드
    default_v2 = pm.load_preset()
    print(f"\n2. V2 형식: timeframes={default_v2.get('timeframes')}")
    
    # 3. Flat 형식 로드
    default_flat = pm.load_preset_flat()
    print(f"\n3. Flat 형식: atr_mult={default_flat.get('atr_mult')}, leverage={default_flat.get('leverage')}")
    
    # 4. 커스텀 프리셋 저장 (V2)
    test_preset = {
        "timeframes": {"filter_tf": "1d", "trend_interval": "4h", "entry_tf": "1h"},
        "trading": {"leverage": 5, "direction": "Long"},
        "indicators": {"atr_mult": 2.0, "rsi_period": 14},
        "risk": {"trail_start_r": 1.5, "trail_dist_r": 0.3},
    }
    pm.save_preset('test_v2', test_preset)
    print("\n4. V2 프리셋 저장: test_v2")
    
    # 5. 재로드 확인
    loaded = pm.load_preset('test_v2')
    print(f"\n5. 재로드: leverage={loaded['trading']['leverage']}, atr_mult={loaded['indicators']['atr_mult']}")
    
    # 6. Flat 변환
    flat = pm.load_preset_flat('test_v2')
    print(f"\n6. Flat 변환: leverage={flat.get('leverage')}, atr_mult={flat.get('atr_mult')}")
    
    # 7. 레거시 호환
    legacy = load_strategy_params()
    print(f"\n7. 레거시 로드: {len(legacy)}개 키")
    
    # 8. 정리
    pm.delete_preset('test_v2')
    print("\n8. 테스트 프리셋 삭제: test_v2")
    
    print("\n✅ Test PASSED!")


def get_backtest_params(preset_name: str = None) -> Dict:
    """백테스트/실매매용 통합 파라미터 로드
    
    우선순위:
    1. DEFAULT_PARAMS (기본값)
    2. strategy_params.json (저장된 설정)
    3. 프리셋 파일 (지정된 경우)
    """
    # 1. 기본값 로드 (GUI.constants가 Source of Truth)
    try:
        from GUI.constants import DEFAULT_PARAMS
        params = DEFAULT_PARAMS.copy()
    except ImportError:
        # Fallback if GUI module not accessible
        params = {
            'atr_mult': 1.25, 'trail_start_r': 0.8, 'trail_dist_r': 0.1,
            'pattern_tolerance': 0.03, 'entry_validity_hours': 6.0,
            'filter_tf': '4h', 'rsi_period': 14, 'atr_period': 14,
            'pullback_rsi_long': 40, 'pullback_rsi_short': 60
        }
    
    # 2. strategy_params.json 로드 (사용자 저장값)
    base_params = load_strategy_params()
    if base_params:
        params.update(base_params)
    
    # 3. 프리셋 로드 (지정된 경우 최우선)
    if preset_name and preset_name not in ('기본값', '기본 설정', ''):
        try:
            # 싱글톤 인스턴스 사용
            mgr = get_preset_manager()
            preset_params = mgr.load_preset_flat(preset_name)
            if preset_params:
                params.update(preset_params)
                print(f"[PARAMS] Preset applied: {preset_name}")
        except Exception as e:
            print(f"[PARAMS] Preset load failed: {e}")
    
    return params
