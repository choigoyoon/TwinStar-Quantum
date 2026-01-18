"""
utils/state_manager.py - 봇 상태 관리
크래시 복구를 위한 상태 저장/로드
"""
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class StateManager:
    """
    봇 상태 관리 클래스
    주기적 상태 저장 및 크래시 복구 지원
    """
    
    def __init__(self, state_dir: str | None = None, bot_id: str = "default"):
        """
        Args:
            state_dir: 상태 파일 저장 디렉토리
            bot_id: 봇 식별자 (파일명에 사용)
        """
        if state_dir is None:
            try:
                from paths import Paths
                state_dir = str(Paths.DATA)
            except ImportError:
                state_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.state_dir = Path(state_dir) if state_dir else Path.cwd()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.bot_id = bot_id
        self.state_file = self.state_dir / f"bot_state_{bot_id}.json"
        self.backup_file = self.state_dir / f"bot_state_{bot_id}.backup.json"
        
        self._state: Dict[str, Any] = {}
        self._last_save = None
    
    def save(self, state: Dict[str, Any] | None = None) -> bool:
        """
        상태 저장
        
        Args:
            state: 저장할 상태 (None이면 내부 상태 사용)
            
        Returns:
            저장 성공 여부
        """
        try:
            if state:
                self._state = state
            
            # 메타데이터 추가
            save_data = {
                '_meta': {
                    'bot_id': self.bot_id,
                    'saved_at': datetime.now().isoformat(),
                    'version': '1.0'
                },
                'state': self._state
            }
            
            # 기존 파일 백업
            if self.state_file.exists():
                try:
                    self.state_file.rename(self.backup_file)
                except Exception:
                    pass
            
            # 새 상태 저장
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
            
            self._last_save = datetime.now()
            logger.debug(f"[STATE] 상태 저장 완료: {self.state_file}")
            return True
            
        except Exception as e:
            logger.error(f"[STATE] 상태 저장 실패: {e}")
            return False
    
    def load(self) -> Optional[Dict[str, Any]]:
        """
        상태 로드 (메인 → 백업 순서)
        
        Returns:
            로드된 상태 또는 None
        """
        for file_path in [self.state_file, self.backup_file]:
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    self._state = data.get('state', {})
                    meta = data.get('_meta', {})
                    
                    logger.info(
                        f"[STATE] 상태 로드 완료: {file_path.name} "
                        f"(저장: {meta.get('saved_at', 'unknown')})"
                    )
                    return self._state
                    
                except json.JSONDecodeError:
                    logger.warning(f"[STATE] 상태 파일 손상: {file_path}")
                    continue
                except Exception as e:
                    logger.error(f"[STATE] 상태 로드 실패: {e}")
                    continue
        
        logger.info("[STATE] 저장된 상태 없음, 새로 시작")
        return None
    
    def update(self, key: str, value: Any, auto_save: bool = False):
        """
        상태 업데이트
        
        Args:
            key: 상태 키
            value: 값
            auto_save: 자동 저장 여부
        """
        self._state[key] = value
        
        if auto_save:
            self.save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """상태 값 조회"""
        return self._state.get(key, default)
    
    def clear(self):
        """상태 초기화"""
        self._state = {}
        
        for file_path in [self.state_file, self.backup_file]:
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass
        
        logger.info("[STATE] 상태 초기화 완료")
    
    @property
    def has_saved_state(self) -> bool:
        """저장된 상태 존재 여부"""
        return self.state_file.exists() or self.backup_file.exists()
    
    def get_position_state(self) -> Optional[Dict]:
        """포지션 상태 조회"""
        return self._state.get('position')
    
    def save_position(self, position: Dict):
        """포지션 상태 저장"""
        self.update('position', position, auto_save=True)
    
    def clear_position(self):
        """포지션 상태 클리어"""
        if 'position' in self._state:
            del self._state['position']
            self.save()


def get_state_manager(bot_id: str = "default") -> StateManager:
    """싱글톤 StateManager 반환"""
    if not hasattr(get_state_manager, '_instances'):
        get_state_manager._instances = {}
    
    if bot_id not in get_state_manager._instances:
        get_state_manager._instances[bot_id] = StateManager(bot_id=bot_id)
    
    return get_state_manager._instances[bot_id]


if __name__ == '__main__':
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    sm = StateManager(bot_id='test')
    
    # 저장
    sm.update('position', {'symbol': 'BTCUSDT', 'side': 'Long', 'entry': 95000})
    sm.update('last_signal', '2026-01-05T12:00:00')
    sm.save()
    
    # 로드
    sm2 = StateManager(bot_id='test')
    state = sm2.load()
    logger.info(f"Loaded state: {state}")
    
    # 정리
    sm2.clear()
