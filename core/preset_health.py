"""
Preset Health Monitor
- 실시간 승률 vs 최적화 승률 비교
- 성능 저하 시 경고/중지/재최적화 표시
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from pathlib import Path

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

try:
    from paths import Paths
    PRESETS_DIR = Paths.PRESETS
except ImportError:
    PRESETS_DIR = 'config/presets'


class PresetHealthMonitor:
    """프리셋 건강 상태 모니터링"""
    
    # 임계값 설정
    WARNING_THRESHOLD = 0.05      # 5% 차이 → 경고
    PAUSE_THRESHOLD = 0.10        # 10% 차이 → 거래 중지
    REOPTIMIZE_THRESHOLD = 0.15   # 15% 차이 → 재최적화 필요
    
    # 최소 거래 수 (신뢰도)
    MIN_TRADES_FOR_CHECK = 10
    
    # 상태 코드
    STATUS_ACTIVE = 'active'
    STATUS_WARNING = 'warning'
    STATUS_PAUSED = 'paused'
    STATUS_REOPTIMIZE = 'needs_reoptimize'
    
    def __init__(self, presets_dir: str = None):
        self.presets_dir = Path(presets_dir or PRESETS_DIR)
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        
        # 실시간 성능 추적
        self._realtime_stats: Dict[str, Dict] = {}
        
        # 헬스 상태 캐시
        self._health_cache: Dict[str, Dict] = {}
        
        logging.info(f"[HEALTH] PresetHealthMonitor initialized: {self.presets_dir}")
    
    def record_trade(self, preset_name: str, is_win: bool, pnl_pct: float):
        """
        거래 결과 기록
        
        Args:
            preset_name: 프리셋 이름 (예: bybit_BTCUSDT_15m)
            is_win: 승리 여부
            pnl_pct: 손익률 (%)
        """
        if preset_name not in self._realtime_stats:
            self._realtime_stats[preset_name] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'history': []
            }
        
        stats = self._realtime_stats[preset_name]
        stats['trades'] += 1
        stats['total_pnl'] += pnl_pct
        
        if is_win:
            stats['wins'] += 1
        else:
            stats['losses'] += 1
        
        # 최근 100개 기록 유지
        stats['history'].append({
            'time': datetime.now().isoformat(),
            'win': is_win,
            'pnl': pnl_pct
        })
        stats['history'] = stats['history'][-100:]
        
        logging.debug(f"[HEALTH] Trade recorded: {preset_name} ({'W' if is_win else 'L'}) {pnl_pct:+.2f}%")
        
        # 자동 헬스 체크
        self.check_health(preset_name)
    
    def get_realtime_winrate(self, preset_name: str) -> Optional[float]:
        """실시간 승률 계산"""
        stats = self._realtime_stats.get(preset_name)
        if not stats or stats['trades'] == 0:
            return None
        return stats['wins'] / stats['trades']
    
    def get_optimized_winrate(self, preset_name: str) -> Optional[float]:
        """최적화 시점 승률 조회"""
        preset_path = self.presets_dir / f"{preset_name}.json"
        
        if not preset_path.exists():
            return None
        
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # _result 또는 최상위에서 win_rate 찾기
            if '_result' in data:
                return data['_result'].get('win_rate')
            return data.get('win_rate') or data.get('optimized_win_rate')
        except Exception as e:
            logging.error(f"[HEALTH] Failed to load preset: {e}")
            return None
    
    def check_health(self, preset_name: str) -> Dict:
        """
        프리셋 건강 상태 체크
        
        Returns:
            {
                'status': 'active' | 'warning' | 'paused' | 'needs_reoptimize',
                'realtime_wr': float,
                'optimized_wr': float,
                'diff': float,
                'trades': int,
                'message': str
            }
        """
        result = {
            'status': self.STATUS_ACTIVE,
            'realtime_wr': None,
            'optimized_wr': None,
            'diff': 0,
            'trades': 0,
            'message': ''
        }
        
        # 실시간 승률
        realtime_wr = self.get_realtime_winrate(preset_name)
        optimized_wr = self.get_optimized_winrate(preset_name)
        
        stats = self._realtime_stats.get(preset_name, {})
        trades = stats.get('trades', 0)
        
        result.update({
            'realtime_wr': realtime_wr,
            'optimized_wr': optimized_wr,
            'trades': trades
        })
        
        # 데이터 부족
        if realtime_wr is None or optimized_wr is None:
            result.update({'message': '데이터 부족'})
            return result
        
        # 최소 거래 수 미달
        if trades < self.MIN_TRADES_FOR_CHECK:
            result.update({'message': f'거래 수 부족 ({trades}/{self.MIN_TRADES_FOR_CHECK})'})
            return result
        
        # 차이 계산
        diff = optimized_wr - realtime_wr
        result.update({'diff': diff})
        
        # 상태 판정
        if diff >= self.REOPTIMIZE_THRESHOLD:
            result.update({'status': self.STATUS_REOPTIMIZE})
            result.update({'message': f'재최적화 필요! (차이: {diff*100:.1f}%)'})
            logging.warning(f"[HEALTH] 🔴 {preset_name}: {result.get('message')}")
            
        elif diff >= self.PAUSE_THRESHOLD:
            result.update({'status': self.STATUS_PAUSED})
            result.update({'message': f'거래 일시 중지 (차이: {diff*100:.1f}%)'})
            logging.warning(f"[HEALTH] 🟠 {preset_name}: {result.get('message')}")
            
        elif diff >= self.WARNING_THRESHOLD:
            result.update({'status': self.STATUS_WARNING})
            result.update({'message': f'성능 저하 경고 (차이: {diff*100:.1f}%)'})
            logging.info(f"[HEALTH] 🟡 {preset_name}: {result.get('message')}")
            
        else:
            result.update({'status': self.STATUS_ACTIVE})
            result.update({'message': '정상'})
        
        # 캐시 업데이트
        self._health_cache[preset_name] = result
        
        # 프리셋 파일에 상태 저장
        self._update_preset_status(preset_name, result)
        
        return result
    
    def _update_preset_status(self, preset_name: str, health: Dict):
        """프리셋 파일에 헬스 상태 업데이트"""
        preset_path = self.presets_dir / f"{preset_name}.json"
        
        if not preset_path.exists():
            return
        
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['_health'] = {
                'status': health['status'],
                'realtime_wr': health['realtime_wr'],
                'diff': health['diff'],
                'trades': health['trades'],
                'last_check': datetime.now().isoformat()
            }
            
            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"[HEALTH] Failed to update preset status: {e}")
    
    def can_trade(self, preset_name: str) -> Tuple[bool, str]:
        """
        거래 가능 여부 확인
        
        Returns:
            (can_trade: bool, reason: str)
        """
        health = self._health_cache.get(preset_name)
        
        if not health:
            health = self.check_health(preset_name)
        
        if health['status'] in [self.STATUS_PAUSED, self.STATUS_REOPTIMIZE]:
            return False, health['message']
        
        return True, 'OK'
    
    def get_all_health(self) -> Dict[str, Dict]:
        """모든 프리셋 헬스 상태 조회"""
        results = {}
        
        for preset_file in self.presets_dir.glob('*.json'):
            preset_name = preset_file.stem
            results[preset_name] = self.check_health(preset_name)
        
        return results
    
    def get_summary(self) -> Dict:
        """전체 요약"""
        all_health = self.get_all_health()
        
        summary = {
            'total': len(all_health),
            'active': 0,
            'warning': 0,
            'paused': 0,
            'reoptimize': 0,
            'problem_presets': []
        }
        
        for name, health in all_health.items():
            status = health['status']
            if status == self.STATUS_ACTIVE:
                summary['active'] += 1
            elif status == self.STATUS_WARNING:
                summary['warning'] += 1
            elif status == self.STATUS_PAUSED:
                summary['paused'] += 1
                summary['problem_presets'].append(name)
            elif status == self.STATUS_REOPTIMIZE:
                summary['reoptimize'] += 1
                summary['problem_presets'].append(name)
        
        return summary
    
    def reset_stats(self, preset_name: str = None):
        """통계 초기화"""
        if preset_name:
            self._realtime_stats.pop(preset_name, None)
            self._health_cache.pop(preset_name, None)
        else:
            self._realtime_stats.clear()
            self._health_cache.clear()
        
        logging.info(f"[HEALTH] Stats reset: {preset_name or 'ALL'}")


# 싱글톤 인스턴스
_health_monitor = None

def get_health_monitor() -> PresetHealthMonitor:
    """헬스 모니터 싱글톤"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = PresetHealthMonitor()
    return _health_monitor


# 테스트
if __name__ == '__main__':
    monitor = PresetHealthMonitor()
    
    # 테스트 거래 기록
    test_preset = 'bybit_BTCUSDT_15m'
    
    # 10번 거래 시뮬레이션 (7승 3패 = 70%)
    for i in range(10):
        is_win = i < 7
        pnl = 2.5 if is_win else -1.5
        monitor.record_trade(test_preset, is_win, pnl)
    
    # 헬스 체크
    health = monitor.check_health(test_preset)
    logger.info(f"Health: {health}")
    
    # 거래 가능 여부
    can, reason = monitor.can_trade(test_preset)
    logger.info(f"Can trade: {can}, Reason: {reason}")
