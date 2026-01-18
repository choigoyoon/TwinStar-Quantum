import json
import os
import sys
import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional


class _FallbackPaths:
    """EXE 환경에서 paths 모듈 import 실패 시 사용하는 fallback 클래스"""

    @staticmethod
    def _get_base() -> str:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def history(cls, exchange: str, symbol: str) -> str:
        base = cls._get_base()
        return os.path.join(base, 'user', 'exchanges',
                           exchange.lower(),
                           symbol.upper().replace('/', '_'),
                           'history.json')

    @classmethod
    def state(cls, exchange: str, symbol: str) -> str:
        base = cls._get_base()
        return os.path.join(base, 'user', 'exchanges',
                           exchange.lower(),
                           symbol.upper().replace('/', '_'),
                           'state.json')

    @classmethod
    def ensure_dirs(cls, exchange: Optional[str] = None, symbol: Optional[str] = None) -> None:
        base = cls._get_base()
        dirs = [os.path.join(base, 'user'), os.path.join(base, 'user', 'exchanges')]
        if exchange:
            dirs.append(os.path.join(base, 'user', 'exchanges', exchange.lower()))
        if exchange and symbol:
            dirs.append(os.path.join(base, 'user', 'exchanges',
                                    exchange.lower(), symbol.upper().replace('/', '_')))
        for d in dirs:
            os.makedirs(d, exist_ok=True)


# [FIX] EXE 호환 import
Paths: Any = _FallbackPaths

try:
    from paths import Paths  # type: ignore[no-redef]
except ImportError:
    pass


class StateStorage:
    """포지션 상태 저장 클래스 - 즉시 저장, 파일 락으로 동시 접근 보호"""
    
    def __init__(self, exchange: str, symbol: str):
        self.exchange = exchange.lower()
        self.symbol = symbol.upper().replace('/', '_')
        self.path = Paths.state(exchange, symbol)
        self._lock = threading.Lock()  # 동시 접근 보호
        
        # 폴더 생성
        Paths.ensure_dirs(exchange, symbol)
    
    def save(self, state: dict):
        """
        상태 즉시 저장 (스레드 안전)
        
        Args:
            state: 상태 딕셔너리
                - position: 'Long', 'Short', None
                - entry_price: 진입가
                - quantity: 수량
                - stop_loss: 현재 손절가 (트레일링 중 업데이트됨)
                - current_sl: 현재 적용 중인 SL 레벨 (재시작 시 복구용)
                - trail_active: 트레일링 활성화 여부
                - trail_start: 트레일 시작가
                - trail_dist: 트레일 거리
                - entry_time: 진입 시간
        """
        with self._lock:
            state['updated_at'] = datetime.now().isoformat()
            state['exchange'] = self.exchange
            state['symbol'] = self.symbol
            
            # 임시 파일에 먼저 저장 (손상 방지)
            temp_path = self.path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            
            # 원자적 교체
            if os.path.exists(self.path):
                os.remove(self.path)
            os.rename(temp_path, self.path)
    
    def load(self) -> Optional[Dict]:
        """
        저장된 상태 로드 (스레드 안전)
        
        Returns:
            상태 딕셔너리 또는 None
        """
        with self._lock:
            if os.path.exists(self.path):
                try:
                    with open(self.path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except (json.JSONDecodeError, Exception) as e:
                    # 손상된 파일 → 백업 후 None 반환
                    backup_path = self.path + f'.backup_{datetime.now():%Y%m%d_%H%M%S}'
                    os.rename(self.path, backup_path)
                    logging.warning(f"[StateStorage] 손상된 상태 파일 백업됨: {backup_path}")
                    return None
            return None
    
    def clear(self):
        """상태 파일 삭제 (포지션 청산 시)"""
        with self._lock:
            if os.path.exists(self.path):
                os.remove(self.path)
    
    def has_position(self) -> bool:
        """현재 포지션이 있는지 확인"""
        state = self.load()
        if state is None:
            return False
        return state.get('position') is not None


# 전역 인스턴스 캐시
_state_instances: Dict[str, StateStorage] = {}


def get_state_storage(exchange: str, symbol: str) -> StateStorage:
    """
    StateStorage 싱글톤 인스턴스 반환
    
    Args:
        exchange: 거래소 이름
        symbol: 심볼
    
    Returns:
        StateStorage 인스턴스
    """
    key = f"{exchange.lower()}_{symbol.upper()}"
    if key not in _state_instances:
        _state_instances[key] = StateStorage(exchange, symbol)
    return _state_instances[key]
