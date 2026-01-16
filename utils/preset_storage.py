# utils/preset_storage.py
"""
멀티체인 프리셋 저장/로드/상태관리 모듈
- 자동 생성 프리셋 관리
- 승률 추적
- 상태 관리 (active/warning/suspended)
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Logging
import logging
logger = logging.getLogger(__name__)


class PresetStorage:
    """멀티체인 프리셋 저장소"""
    
    # 프리셋 상태
    STATUS_ACTIVE = 'active'
    STATUS_WARNING = 'warning'
    STATUS_SUSPENDED = 'suspended'
    STATUS_NEEDS_REOPTIMIZE = 'needs_reoptimize'
    
    def __init__(self, base_path: str | None = None):
        """
        Args:
            base_path: 프리셋 저장 기본 경로
        """
        if base_path is None:
            # 기본 경로: config/presets/auto
            base_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'presets', 'auto')
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 인덱스 파일 (전체 프리셋 메타데이터)
        self.index_file = self.base_path / '_index.json'
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """인덱스 파일 로드"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'presets': {}, 'last_updated': None}
    
    def _save_index(self):
        """인덱스 파일 저장"""
        self.index['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def _get_preset_key(self, symbol: str, tf: str) -> str:
        """프리셋 키 생성 (레거시 호환용)"""
        return f"{symbol.upper()}_{tf.lower()}"

    def _get_preset_path(
        self,
        symbol: str,
        tf: str,
        mode: str | None = None,
        strategy_type: str | None = None,
        use_timestamp: bool = True,
        exchange: str | None = None
    ) -> Path:
        """
        프리셋 파일 경로 (v3.0 - 전략 유형 추가)

        Args:
            symbol: 심볼
            tf: 타임프레임
            mode: 최적화 모드 (quick/standard/deep)
            strategy_type: 전략 유형 (macd/adx)
            use_timestamp: 타임스탬프 포함 여부 (기본 True)
            exchange: 거래소 (None이면 self.exchange 사용)
        """
        from config.constants import generate_preset_filename

        # 거래소 정보 (None 방지)
        exchange_name: str = exchange if exchange is not None else getattr(self, 'exchange', 'bybit')

        filename = generate_preset_filename(
            exchange=exchange_name,
            symbol=symbol,
            timeframe=tf,
            mode=mode,
            strategy_type=strategy_type,
            use_timestamp=use_timestamp
        )
        return self.base_path / filename
    
    def save_preset(
        self,
        symbol: str,
        tf: str,
        params: Dict,
        optimization_result: Dict | None = None,
        chart_profile: Dict | None = None,
        mode: str | None = None,
        strategy_type: str | None = None,
        exchange: str | None = None
    ) -> bool:
        """
        프리셋 저장 (v3.0 - 전략 유형 추가)

        Args:
            symbol: 심볼 (예: BTCUSDT)
            tf: 타임프레임 (예: 4h)
            params: 최적화 파라미터
            optimization_result: 최적화 결과 (승률, MDD 등)
            chart_profile: 차트 프로파일
            mode: 최적화 모드 (quick/standard/deep)
            strategy_type: 전략 유형 (macd/adx)
            exchange: 거래소 (None이면 self.exchange 사용)

        Returns:
            성공 여부
        """
        try:
            key = self._get_preset_key(symbol, tf)
            path = self._get_preset_path(
                symbol, tf, mode=mode, strategy_type=strategy_type,
                use_timestamp=True, exchange=exchange
            )
            
            preset_data = {
                'symbol': symbol.upper(),
                'timeframe': tf.lower(),
                'strategy_type': strategy_type or 'macd',  # v3.0: 전략 유형 추가
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

                # 파라미터
                'params': params,

                # 최적화 결과
                'optimization': optimization_result or {},

                # 차트 프로파일 (유사도 매칭용)
                'chart_profile': chart_profile or {},
                
                # 실시간 추적
                'live_stats': {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0.0,
                    'win_rate': 0.0,
                    'last_trade': None
                },
                
                # 상태
                'status': self.STATUS_ACTIVE,
                
                # 매칭된 코인 (신규 코인이 이 프리셋 사용 시)
                'matched_coins': []
            }
            
            # 파일 저장
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=2, ensure_ascii=False)
            
            # 인덱스 업데이트
            self.index['presets'][key] = {
                'symbol': symbol.upper(),
                'timeframe': tf.lower(),
                'win_rate': optimization_result.get('win_rate', 0) if optimization_result else 0,
                'status': self.STATUS_ACTIVE,
                'created_at': preset_data['created_at']
            }
            self._save_index()
            
            logger.info(f"[PresetStorage] ✅ 저장: {key}")
            return True
            
        except Exception as e:
            logger.info(f"[PresetStorage] ❌ 저장 실패 ({symbol}_{tf}): {e}")
            return False
    
    def load_preset(self, symbol: str, tf: str) -> Optional[Dict]:
        """프리셋 로드 (최신 파일 자동 선택)

        타임스탬프 포함 파일명을 glob 패턴으로 검색하여 가장 최신 파일 로드.

        Args:
            symbol: 심볼 (예: BTCUSDT)
            tf: 타임프레임 (예: 4h)

        Returns:
            프리셋 데이터 dict 또는 None
        """
        exchange_name = getattr(self, 'exchange', 'bybit')

        # 1. 타임스탬프 포함 패턴으로 검색
        pattern = f"{exchange_name}_{symbol}_{tf}_*.json"
        matches = list(self.base_path.glob(pattern))

        # 2. 타임스탬프 없는 파일도 시도
        if not matches:
            fallback = self.base_path / f"{exchange_name}_{symbol}_{tf}.json"
            if fallback.exists():
                matches = [fallback]

        if not matches:
            return None

        # 3. 가장 최신 파일 선택 (수정 시간 기준)
        latest = max(matches, key=lambda p: p.stat().st_mtime)

        try:
            with open(latest, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.info(f"[PresetStorage] ❌ 로드 실패 ({symbol}_{tf}): {e}")
            return None

    def load_all_presets(self, symbol: str, tf: str) -> List[Dict]:
        """같은 symbol/tf의 모든 프리셋 로드 (타입별 정렬)

        동일한 심볼/타임프레임의 모든 프리셋 파일을 로드하고,
        preset_type(aggressive/balanced/conservative) 순서로 정렬.

        Args:
            symbol: 심볼 (예: BTCUSDT)
            tf: 타임프레임 (예: 4h)

        Returns:
            프리셋 데이터 리스트 (preset_type 순 정렬)
        """
        exchange_name = getattr(self, 'exchange', 'bybit')
        pattern = f"{exchange_name}_{symbol}_{tf}_*.json"
        matches = list(self.base_path.glob(pattern))

        # 타임스탬프 없는 파일도 포함
        fallback = self.base_path / f"{exchange_name}_{symbol}_{tf}.json"
        if fallback.exists() and fallback not in matches:
            matches.append(fallback)

        presets = []
        for file_path in matches:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['_file_path'] = str(file_path)
                    presets.append(data)
            except Exception as e:
                logger.warning(f"[PresetStorage] 파일 로드 실패 ({file_path.name}): {e}")
                continue

        # preset_type 기준 정렬 (aggressive → balanced → conservative)
        type_order = {'aggressive': 0, 'balanced': 1, 'conservative': 2}
        presets.sort(key=lambda p: type_order.get(
            p.get('optimization', {}).get('preset_type', ''), 999
        ))

        return presets

    def update_live_stats(self, symbol: str, tf: str, 
                         is_win: bool, pnl: float) -> bool:
        """
        실시간 거래 결과 업데이트
        
        Args:
            symbol: 심볼
            tf: 타임프레임
            is_win: 승리 여부
            pnl: 손익
        """
        preset = self.load_preset(symbol, tf)
        if preset is None:
            return False
        
        try:
            stats = preset.get('live_stats', {})
            stats['trades'] = stats.get('trades', 0) + 1
            
            if is_win:
                stats['wins'] = stats.get('wins', 0) + 1
            else:
                stats['losses'] = stats.get('losses', 0) + 1
            
            stats['total_pnl'] = stats.get('total_pnl', 0) + pnl
            stats['win_rate'] = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            stats['last_trade'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            preset['live_stats'] = stats
            preset['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 상태 체크
            preset['status'] = self._check_health(preset)
            
            # 저장
            path = self._get_preset_path(symbol, tf)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(preset, f, indent=2, ensure_ascii=False)
            
            # 인덱스 업데이트
            key = self._get_preset_key(symbol, tf)
            if key in self.index['presets']:
                self.index['presets'][key]['win_rate'] = stats['win_rate']
                self.index['presets'][key]['status'] = preset['status']
                self._save_index()
            
            return True
            
        except Exception as e:
            logger.info(f"[PresetStorage] ❌ 업데이트 실패: {e}")
            return False
    
    def _check_health(self, preset: Dict) -> str:
        """프리셋 건강 상태 체크"""
        live_stats = preset.get('live_stats', {})
        opt_result = preset.get('optimization', {})
        
        # 최소 거래 수 체크
        if live_stats.get('trades', 0) < 10:
            return self.STATUS_ACTIVE
        
        opt_win_rate = opt_result.get('win_rate', 0)
        live_win_rate = live_stats.get('win_rate', 0)
        
        diff = opt_win_rate - live_win_rate
        
        if diff > 15:  # 15% 이상 하락
            return self.STATUS_NEEDS_REOPTIMIZE
        elif diff > 10:  # 10~15% 하락
            return self.STATUS_SUSPENDED
        elif diff > 5:  # 5~10% 하락
            return self.STATUS_WARNING
        else:
            return self.STATUS_ACTIVE
    
    def get_active_presets(self) -> List[Dict]:
        """활성 상태 프리셋 목록"""
        active = []
        for key, meta in self.index.get('presets', {}).items():
            if meta.get('status') in [self.STATUS_ACTIVE, self.STATUS_WARNING]:
                preset = self.load_preset(meta['symbol'], meta['timeframe'])
                if preset:
                    active.append(preset)
        return active
    
    def get_tradeable_presets(self) -> List[Dict]:
        """거래 가능 프리셋 (active만)"""
        return [p for p in self.get_active_presets() 
                if p.get('status') == self.STATUS_ACTIVE]
    
    def get_all_presets(self) -> List[Dict]:
        """전체 프리셋 목록"""
        presets = []
        for key, meta in self.index.get('presets', {}).items():
            preset = self.load_preset(meta['symbol'], meta['timeframe'])
            if preset:
                presets.append(preset)
        return presets
    
    def set_status(self, symbol: str, tf: str, status: str) -> bool:
        """상태 수동 설정"""
        preset = self.load_preset(symbol, tf)
        if preset is None:
            return False
        
        preset['status'] = status
        preset['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        path = self._get_preset_path(symbol, tf)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(preset, f, indent=2, ensure_ascii=False)
        
        key = self._get_preset_key(symbol, tf)
        if key in self.index['presets']:
            self.index['presets'][key]['status'] = status
            self._save_index()
        
        return True
    
    def delete_preset(self, symbol: str, tf: str) -> bool:
        """프리셋 삭제"""
        path = self._get_preset_path(symbol, tf)
        key = self._get_preset_key(symbol, tf)
        
        try:
            if path.exists():
                os.remove(path)
            
            if key in self.index['presets']:
                del self.index['presets'][key]
                self._save_index()
            
            return True
        except Exception as e:
            logger.info(f"[PresetStorage] ❌ 삭제 실패: {e}")
            return False
    
    def get_presets_by_status(self, status: str) -> List[Dict]:
        """상태별 프리셋 조회"""
        return [p for p in self.get_all_presets() if p.get('status') == status]
    
    def get_stats_summary(self) -> Dict:
        """전체 통계 요약"""
        presets = self.get_all_presets()
        
        return {
            'total': len(presets),
            'active': len([p for p in presets if p.get('status') == self.STATUS_ACTIVE]),
            'warning': len([p for p in presets if p.get('status') == self.STATUS_WARNING]),
            'suspended': len([p for p in presets if p.get('status') == self.STATUS_SUSPENDED]),
            'needs_reoptimize': len([p for p in presets if p.get('status') == self.STATUS_NEEDS_REOPTIMIZE]),
            'avg_win_rate': sum(p.get('live_stats', {}).get('win_rate', 0) for p in presets) / len(presets) if presets else 0
        }


# 테스트용
if __name__ == "__main__":
    storage = PresetStorage()
    
    # 테스트 저장
    storage.save_preset(
        symbol='BTCUSDT',
        tf='4h',
        params={'atr_mult': 1.25, 'leverage': 3},
        optimization_result={'win_rate': 85.5, 'mdd': 12.3, 'trades': 120}
    )
    
    # 테스트 로드
    preset = storage.load_preset('BTCUSDT', '4h')
    logger.info(f"로드된 프리셋: {preset}")
    
    # 통계
    logger.info(f"통계: {storage.get_stats_summary()}")
