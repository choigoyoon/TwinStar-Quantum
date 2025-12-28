import json
import os
import sys
import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional

# [FIX] EXE 호환 import
try:
    from paths import Paths
except ImportError:
    try:
        from .paths import Paths
    except ImportError:
        class Paths:
            @staticmethod
            def _get_base():
                if getattr(sys, 'frozen', False):
                    return os.path.dirname(sys.executable)
                return os.path.dirname(os.path.abspath(__file__))
            
            @classmethod
            def history(cls, exchange, symbol):
                base = cls._get_base()
                return os.path.join(base, 'user', 'exchanges', 
                                   exchange.lower(), 
                                   symbol.upper().replace('/', '_'), 
                                   'history.json')
            
            @classmethod
            def state(cls, exchange, symbol):
                base = cls._get_base()
                return os.path.join(base, 'user', 'exchanges',
                                   exchange.lower(),
                                   symbol.upper().replace('/', '_'),
                                   'state.json')
            
            @classmethod
            def ensure_dirs(cls, exchange=None, symbol=None):
                base = cls._get_base()
                dirs = [os.path.join(base, 'user'), os.path.join(base, 'user', 'exchanges')]
                if exchange:
                    dirs.append(os.path.join(base, 'user', 'exchanges', exchange.lower()))
                if exchange and symbol:
                    dirs.append(os.path.join(base, 'user', 'exchanges', 
                                            exchange.lower(), symbol.upper().replace('/', '_')))
                for d in dirs:
                    os.makedirs(d, exist_ok=True)


class TradeStorage:
    """스레드 안전한 거래 기록 저장 클래스"""
    
    BUFFER_SIZE = 5      # 버퍼에 이만큼 쌓이면 저장
    FLUSH_INTERVAL = 60  # 초 단위로 이 시간 지나면 저장
    
    def __init__(self, exchange: str, symbol: str):
        self.exchange = exchange.lower()
        self.symbol = symbol.upper().replace('/', '_')
        self.path = Paths.history(exchange, symbol)
        
        self._lock = threading.Lock()
        self._buffer: List[Dict] = []
        self._last_save = datetime.now()
        
        # 폴더 생성
        Paths.ensure_dirs(exchange, symbol)
    
    def add_trade(self, trade: dict, immediate_flush: bool = False):
        """
        거래 추가
        
        Args:
            trade: 거래 정보 딕셔너리
                - entry_time: 진입 시간
                - exit_time: 청산 시간
                - direction: 'Long' or 'Short'
                - entry_price: 진입가
                - exit_price: 청산가
                - pnl_pct: 수익률 (%)
                - pnl_usd: 수익금 ($)
            immediate_flush: True면 버퍼 무시하고 즉시 저장 (포지션 청산 시 권장)
        """
        with self._lock:
            trade['saved_at'] = datetime.now().isoformat()
            trade['exchange'] = self.exchange
            trade['symbol'] = self.symbol
            self._buffer.append(trade)
            
            # 즉시 저장 또는 조건 충족 시 저장
            if immediate_flush or self._should_flush():
                self._flush()
    
    def _should_flush(self) -> bool:
        """저장 조건 확인"""
        # 버퍼가 일정 크기 이상
        if len(self._buffer) >= self.BUFFER_SIZE:
            return True
        # 마지막 저장 후 일정 시간 경과
        if (datetime.now() - self._last_save).seconds >= self.FLUSH_INTERVAL:
            return True
        return False
    
    def _flush(self):
        """버퍼를 디스크에 저장"""
        if not self._buffer:
            return
        
        # 기존 데이터 로드
        history = self._load_existing()
        history.extend(self._buffer)
        
        # 임시 파일에 먼저 저장 (손상 방지)
        temp_path = self.path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        # 원자적 교체
        if os.path.exists(self.path):
            os.remove(self.path)
        os.rename(temp_path, self.path)
        
        # 버퍼 초기화
        self._buffer = []
        self._last_save = datetime.now()
    
    def _load_existing(self) -> List[Dict]:
        """기존 거래 기록 로드"""
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                # 손상된 파일 → 백업 후 새로 시작
                backup_path = self.path + f'.backup_{datetime.now():%Y%m%d_%H%M%S}'
                os.rename(self.path, backup_path)
                return []
        return []
    
    def force_save(self):
        """강제 저장 (종료 시 호출)"""
        with self._lock:
            self._flush()
    
    def get_all_trades(self) -> List[Dict]:
        """모든 거래 기록 반환 (버퍼 포함)"""
        with self._lock:
            existing = self._load_existing()
            # 최신순 정렬 (버퍼가 더 최신일 수 있음, 하지만 보통 append임)
            # 버퍼 + 기존 데이터 합치기
            all_trades = existing + self._buffer
            return sorted(all_trades, key=lambda x: x.get('exit_time', ''), reverse=True)

    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """최근 거래 기록 반환"""
        with self._lock:
            # 효율성을 위해 전체 로드 후 슬라이싱 (파일이 아주 크지 않다면 OK)
            # 개선점: 파일 끝부분만 읽는 방식이 좋으나 JSON 구조상 전체 파싱 필요
            all_trades = self.get_all_trades()
            return all_trades[:limit]
            
    def get_stats(self) -> Dict:
            all_trades = existing + self._buffer.copy()
            # 날짜순 정렬 (내림차순)
            try:
                all_trades.sort(key=lambda x: x.get('time', ''), reverse=True)
            except:
                pass
            return all_trades

    def get_recent_trades(self, limit: int = 5) -> List[Dict]:
        """최근 거래 기록 반환"""
        trades = self.get_all_trades()
        return trades[:limit]
    
    def get_stats(self) -> Dict:
        """거래 통계 계산"""
        trades = self.get_all_trades()
        
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl_pct': 0.0,
                'total_pnl_usd': 0.0,
                'avg_pnl_pct': 0.0,
                'max_win_pct': 0.0,
                'max_loss_pct': 0.0,
            }
        
        pnl_list = [t.get('pnl_pct', 0) for t in trades]
        pnl_usd_list = [t.get('pnl_usd', 0) for t in trades]
        wins = [p for p in pnl_list if p > 0]
        
        return {
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'total_pnl_pct': sum(pnl_list),
            'total_pnl_usd': sum(pnl_usd_list),
            'avg_pnl_pct': sum(pnl_list) / len(pnl_list) if pnl_list else 0,
            'max_win_pct': max(pnl_list) if pnl_list else 0,
            'max_loss_pct': min(pnl_list) if pnl_list else 0,
        }


# 전역 인스턴스 캐시
_storage_instances: Dict[str, TradeStorage] = {}


def get_trade_storage(exchange: str, symbol: str) -> TradeStorage:
    """
    TradeStorage 싱글톤 인스턴스 반환
    
    Args:
        exchange: 거래소 이름 (bybit, binance, lighter)
        symbol: 심볼 (BTCUSDT, ETHUSDT)
    
    Returns:
        TradeStorage 인스턴스
    """
    key = f"{exchange.lower()}_{symbol.upper()}"
    if key not in _storage_instances:
        _storage_instances[key] = TradeStorage(exchange, symbol)
    return _storage_instances[key]
