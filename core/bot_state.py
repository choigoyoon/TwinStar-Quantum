"""
core/bot_state.py
봇 상태 관리 모듈 (Phase 2.1 리팩토링)

- 상태 저장/로드 (position, capital, trailing 등)
- 캐시 관리 (pending signals, bt_state)
- 거래 히스토리 저장
"""

import os
import tempfile

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path


class BotStateManager:
    """
    봇 상태 저장/로드 관리
    
    - 인스턴스별 상태 파일 분리 (exchange_symbol 조합)
    - 새 Storage 시스템과 레거시 파일 모두 지원
    - 캐시 관리 (1시간 유효)
    """
    
    def __init__(
        self, 
        exchange_name: str, 
        symbol: str, 
        storage_dir: str = None,
        use_new_storage: bool = False,
        state_storage = None,
        trade_storage = None
    ):
        """
        Args:
            exchange_name: 거래소 이름 (bybit, binance 등)
            symbol: 심볼 (BTCUSDT 등)
            storage_dir: 저장 디렉토리 (기본: storage/)
            use_new_storage: 새 Storage 시스템 사용 여부
            state_storage: StateStorage 인스턴스 (use_new_storage=True일 때)
            trade_storage: TradeStorage 인스턴스 (use_new_storage=True일 때)
        """
        self.exchange_name = exchange_name.lower()
        self.symbol = symbol.replace('/', '').replace('-', '').upper()
        
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            try:
                from paths import Paths
                self.storage_dir = Path(Paths.USER_DATA) / 'storage'
            except ImportError:
                # Fallback
                self.storage_dir = Path(__file__).parent.parent / 'storage'
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 인스턴스별 파일명
        instance_id = f"{self.exchange_name}_{self.symbol.lower()}"
        self.state_file = self.storage_dir / f"{instance_id}_state.json"
        self.cache_file = self.storage_dir / f"{instance_id}_cache.json"
        self.history_file = self.storage_dir / f"{instance_id}_history.json"
        
        # 레거시 호환 (기본 파일)
        self.default_state_file = self.storage_dir / "bot_state.json"
        
        # 새 Storage 시스템
        self.use_new_storage = use_new_storage
        self.state_storage = state_storage
        self.trade_storage = trade_storage
        
        logging.debug(f"[STATE] Initialized: {instance_id} → {self.state_file}")

        # Managed Positions (Phase 8.1.1)
        self.managed_positions: Dict[str, dict] = {}
        self._load_managed_positions()
    
    # ========== 상태 저장/로드 ==========
    
    def load_state(self) -> Optional[Dict]:
        """
        상태 로드
        
        Returns:
            상태 딕셔너리 또는 None
        """
        try:
            # 1. 새 Storage 우선
            if self.use_new_storage and self.state_storage:
                state = self.state_storage.load()
                if state:
                    logging.info(f"[STATE] Loaded from new storage")
                    return state
            
            # 2. 인스턴스 전용 파일
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                logging.info(f"[STATE] Loaded from {self.state_file.name}")
                return state
            
            # 3. 레거시 파일 (하위 호환)
            if self.default_state_file.exists():
                with open(self.default_state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                logging.info(f"[STATE] Loaded from legacy file")
                return state
                
            return None
            
        except Exception as e:
            logging.error(f"[STATE] Load error: {e}")
            return None
    
    def save_state(self, state: Dict) -> bool:
        """
        상태 저장 (Atomic Write 적용)
        
        Args:
            state: 저장할 상태 딕셔너리
            
        Returns:
            성공 여부
        """
        try:
            # timestamp 추가
            state['timestamp'] = datetime.now().isoformat()
            state['exchange'] = self.exchange_name
            state['symbol'] = self.symbol
            
            # 1. 새 Storage 저장
            if self.use_new_storage and self.state_storage:
                self.state_storage.save(state)
            
            # 2. 인스턴스 전용 파일 저장 (Atomic Write)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            # 임시 파일 사용하여 원자적 쓰기 보장
            dir_name = str(self.storage_dir)
            try:
                with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tmp_file:
                    json.dump(state, tmp_file, indent=2, ensure_ascii=False, default=str)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())
                    tmp_name = tmp_file.name
                
                os.replace(tmp_name, self.state_file)
            except Exception as e:
                logging.error(f"[STATE] Atomic write failed: {e}")
                # Fallback to direct write if temp file fails (e.g. permission)
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2, ensure_ascii=False, default=str)

            # 3. 레거시 파일도 저장 (UI 동기화용)
            try:
                legacy_dir = os.path.dirname(self.default_state_file)
                if not os.path.exists(legacy_dir):
                     os.makedirs(legacy_dir, exist_ok=True)

                with tempfile.NamedTemporaryFile('w', dir=legacy_dir, delete=False, encoding='utf-8') as tmp_file_legacy:
                    json.dump(state, tmp_file_legacy, indent=2, ensure_ascii=False, default=str)
                    tmp_file_legacy.flush()
                    os.fsync(tmp_file_legacy.fileno())
                    tmp_name_legacy = tmp_file_legacy.name
                
                os.replace(tmp_name_legacy, self.default_state_file)
            except Exception as e:
                logging.debug(f"[STATE] Legacy save failed: {e}")
                # Try simple write fallback
                try:
                    with open(self.default_state_file, 'w', encoding='utf-8') as f:
                         json.dump(state, f, indent=2, ensure_ascii=False, default=str)
                except Exception:

                    pass
            
            logging.debug(f"[STATE] Saved: {self.state_file.name}")
            return True
            
        except Exception as e:
            logging.error(f"[STATE] Save error: {e}")
            return False
    
    # ========== 캐시 관리 ==========
    
    def load_cache(self, max_age_hours: float = 1.0) -> Optional[Dict]:
        """
        캐시 로드 (지정 시간 이내만 유효)
        
        Args:
            max_age_hours: 최대 유효 시간 (기본 1시간)
            
        Returns:
            캐시 데이터 또는 None
        """
        if not self.cache_file.exists():
            return None
        
        try:
            # 파일 수정 시간 체크
            mtime = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
            if datetime.now() - mtime > timedelta(hours=max_age_hours):
                logging.info(f"[CACHE] Expired ({max_age_hours}h)")
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            logging.info(f"[CACHE] Loaded from {self.cache_file.name}")
            return cache
            
        except Exception as e:
            logging.error(f"[CACHE] Load error: {e}")
            return None
    
    def save_cache(self, data: Dict) -> bool:
        """
        캐시 저장
        
        Args:
            data: 캐시할 데이터
            
        Returns:
            성공 여부
        """
        try:
            data['last_update'] = datetime.utcnow().isoformat()
            
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            logging.debug(f"[CACHE] Saved: {self.cache_file.name}")
            return True
            
        except Exception as e:
            logging.error(f"[CACHE] Save error: {e}")
            return False
    
    # ========== 거래 히스토리 ==========
    
    def save_trade(self, trade: Dict, immediate_flush: bool = True) -> bool:
        """
        거래 히스토리에 거래 추가
        
        Args:
            trade: 거래 정보 딕셔너리
            immediate_flush: 즉시 파일 저장 여부
            
        Returns:
            성공 여부
        """
        try:
            # 1. 새 Storage 우선
            if self.use_new_storage and self.trade_storage:
                self.trade_storage.add_trade(trade, immediate_flush=immediate_flush)
                logging.info(f"[TRADE] Saved to new storage: {trade.get('pnl_pct', 0):.2f}%")
                return True
            
            # 2. 레거시 방식 (JSON 파일)
            history = []
            if self.history_file.exists():
                try:
                    with open(self.history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except json.JSONDecodeError:
                    history = []
            
            # 거래 추가
            trade['saved_at'] = datetime.now().isoformat()
            history.append(trade)
            
            # 최근 1000개만 유지
            if len(history) > 1000:
                history = history[-1000:]
            
            # 저장
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False, default=str)
            
            logging.info(f"[TRADE] Saved: {trade.get('pnl_pct', 0):.2f}%")
            return True
            
        except Exception as e:
            logging.error(f"[TRADE] Save error: {e}")
            return False
    
    def load_trade_history(self, limit: int = 50) -> List[Dict]:
        """
        거래 히스토리 로드
        
        Args:
            limit: 최대 개수
            
        Returns:
            거래 목록
        """
        try:
            # 1. 새 Storage
            if self.use_new_storage and self.trade_storage:
                return self.trade_storage.get_trades(limit=limit)
            
            # 2. 레거시 파일
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                return history[-limit:] if len(history) > limit else history
            
            return []
            
        except Exception as e:
            logging.error(f"[TRADE] Load error: {e}")
            return []
    
    # ========== 포지션 관리 (Phase 8.1.1) ==========

    def _load_managed_positions(self):
        """저장된 managed_positions 로드"""
        state = self.load_state()
        if state and 'managed_positions' in state:
            self.managed_positions = state['managed_positions']
            logging.debug(f"[POS] Loaded {len(self.managed_positions)} managed positions")

    def _save_managed_positions(self):
        """managed_positions를 상태에 저장"""
        state = self.load_state() or {}
        state['managed_positions'] = self.managed_positions
        self.save_state(state)

    def add_managed_position(
        self, 
        symbol: str, 
        order_id: str, 
        client_order_id: str, 
        entry_price: float,
        side: str,
        size: float
    ):
        """봇이 생성한 포지션 등록"""
        from datetime import datetime
        
        self.managed_positions[symbol] = {
            'order_id': order_id,
            'client_order_id': client_order_id,
            'entry_price': entry_price,
            'side': side,
            'size': size,
            'created_at': datetime.now().isoformat()
        }
        self._save_managed_positions()
        logging.info(f"[POS-ADD] Registered: {symbol} {side} @ {entry_price} (ID: {client_order_id})")

    def remove_managed_position(self, symbol: str):
        """포지션 청산 시 제거"""
        if symbol in self.managed_positions:
            del self.managed_positions[symbol]
            self._save_managed_positions()
            logging.info(f"[POS-REM] Removed: {symbol}")

    def is_managed_position(self, symbol: str) -> bool:
        """봇이 관리하는 포지션인지 확인"""
        return symbol in self.managed_positions

    def get_managed_position(self, symbol: str) -> Optional[dict]:
        """관리 중인 포지션 정보 반환"""
        return self.managed_positions.get(symbol)

    # ========== 유틸리티 ==========
    
    def get_state_file_path(self) -> str:
        """상태 파일 경로 반환"""
        return str(self.state_file)
    
    def get_cache_file_path(self) -> str:
        """캐시 파일 경로 반환"""
        return str(self.cache_file)
    
    def clear_cache(self) -> bool:
        """캐시 파일 삭제"""
        try:
            if self.cache_file.exists():
                os.remove(self.cache_file)
                logging.info(f"[CACHE] Cleared: {self.cache_file.name}")
            return True
        except Exception as e:
            logging.error(f"[CACHE] Clear error: {e}")
            return False


# 싱글톤 인스턴스 (필요시)
_instances: Dict[str, BotStateManager] = {}

def get_state_manager(exchange_name: str, symbol: str, **kwargs) -> BotStateManager:
    """
    싱글톤 패턴으로 BotStateManager 인스턴스 반환
    
    Args:
        exchange_name: 거래소 이름
        symbol: 심볼
        **kwargs: BotStateManager 추가 인자
        
    Returns:
        BotStateManager 인스턴스
    """
    key = f"{exchange_name.lower()}_{symbol.upper()}"
    if key not in _instances:
        _instances[key] = BotStateManager(exchange_name, symbol, **kwargs)
    return _instances[key]


if __name__ == '__main__':
    # 테스트 코드
    logger.info("=== BotStateManager Test ===\n")
    
    manager = BotStateManager('bybit', 'BTCUSDT')
    
    # 상태 저장 테스트
    test_state = {
        'position': {'side': 'Long', 'entry_price': 95000, 'size': 0.1},
        'capital': 1000,
        'current_sl': 94000,
        'extreme_price': 96000
    }
    success = manager.save_state(test_state)
    logger.error(f"1. Save state: {'✅' if success else '❌'}")
    
    # 상태 로드 테스트
    loaded = manager.load_state()
    logger.info(f"2. Load state: {loaded is not None}")
    if loaded:
        logger.info(f"   Position: {loaded.get('position')}")
    
    # 캐시 테스트
    cache_data = {'pending': [{'type': 'Long', 'time': '2025-01-01T00:00:00'}]}
    manager.save_cache(cache_data)
    loaded_cache = manager.load_cache()
    logger.error(f"3. Cache round-trip: {'✅' if loaded_cache else '❌'}")
    
    # 거래 저장 테스트
    trade = {'pnl_pct': 5.5, 'direction': 'Long', 'entry': 95000, 'exit': 96000}
    manager.save_trade(trade)
    history = manager.load_trade_history()
    logger.info(f"4. Trade history: {len(history)} trades")
    
    logger.info("\n✅ All tests passed!")
