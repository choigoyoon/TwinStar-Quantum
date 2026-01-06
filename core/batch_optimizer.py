"""
배치 최적화 관리자 (v2.1)
- 거래소 전체 심볼 순차 최적화
- 엄격한 필터링: WinRate >= 70%, MDD <= 20%, Trades >= 30
- 진행 상태 저장/복구 (중단 후 이어하기)
- 프리셋 자동 생성
"""
import logging
logger = logging.getLogger(__name__)


import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Callable
from dataclasses import dataclass, asdict

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

try:
    from core.optimizer import optimize_strategy
except ImportError:
    optimize_strategy = None

try:
    from utils.preset_manager import get_preset_manager
except ImportError:
    get_preset_manager = None

try:
    from exchanges.exchange_manager import get_exchange_manager
except ImportError:
    get_exchange_manager = None


@dataclass
class OptimizationState:
    """최적화 진행 상태 (저장/복구용)"""
    exchange: str
    timeframes: List[str]
    total_symbols: int
    completed: int
    current_symbol: str
    started_at: str
    last_update: str
    failed_symbols: List[str]
    success_count: int
    min_win_rate: float
    min_trades: int
    max_mdd: float = 20.0


class BatchOptimizer:
    """배치 최적화 관리자 (Strict Filtering v2.1)"""
    
    STATE_FILE = Path('data/batch_state.json')
    
    def __init__(
        self,
        exchange: str = 'bybit',
        timeframes: List[str] = None,
        min_win_rate: float = 70.0,
        min_trades: int = 30,
        max_mdd: float = 20.0
    ):
        self.exchange = exchange
        self.timeframes = timeframes or ['4h', '1d']
        self.min_win_rate = min_win_rate
        self.min_trades = min_trades
        self.max_mdd = max_mdd
        
        self.symbols: List[str] = []
        self.state: Optional[OptimizationState] = None
        self.is_running = False
        self.is_paused = False
        
        self.status_callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None
        self.task_callback: Optional[Callable] = None

    def set_callbacks(self, status_cb=None, progress_cb=None, task_cb=None):
        """Set UI callback functions"""
        self.status_callback = status_cb
        self.progress_callback = progress_cb
        self.task_callback = task_cb

    def _update_status(self, msg: str):
        if self.status_callback:
            self.status_callback(msg)
        logger.info(f"[BatchOptimizer] {msg}")

    def _update_progress(self, current: int, total: int, symbol: str):
        if self.progress_callback:
            self.progress_callback(current, total, symbol)

    def fetch_symbols(self):
        """거래소에서 심볼 목록 조회"""
        try:
            if get_exchange_manager:
                em = get_exchange_manager()
                exchange = em.get_exchange(self.exchange)
                if exchange and hasattr(exchange, 'exchange'):
                    tickers = exchange.exchange.fetch_tickers()
                    self.symbols = [
                        s.replace('/', '').replace(':USDT', '')
                        for s in tickers.keys() 
                        if 'USDT' in s
                    ][:100]  # Limit to top 100
                    return
        except Exception as e:
            logger.error(f"Symbol fetch error: {e}")
        
        # Fallback
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT',
            'ADAUSDT', 'BNBUSDT', 'TRXUSDT', 'LINKUSDT', 'AVAXUSDT'
        ]

    def optimize_symbol(self, symbol: str, timeframe: str) -> Optional[dict]:
        """단일 심볼 최적화"""
        try:
            if optimize_strategy:
                result = optimize_strategy(
                    symbol=symbol,
                    timeframe=timeframe,
                    exchange=self.exchange
                )
                return result
        except Exception as e:
            self._update_status(f"최적화 실패 ({symbol}): {e}")
        return None

    def save_preset(self, symbol: str, timeframe: str, result: dict) -> str:
        """프리셋 저장"""
        if get_preset_manager:
            pm = get_preset_manager()
            name = f"{self.exchange}_{symbol}_{timeframe}"
            
            preset_data = {
                '_meta': {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'exchange': self.exchange,
                    'created_at': datetime.now().isoformat()
                },
                '_result': {
                    'win_rate': result.get('win_rate', 0),
                    'profit_factor': result.get('profit_factor', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'total_trades': result.get('total_trades', 0)
                },
                'params': result.get('best_params', result.get('params', {}))
            }
            
            pm.save_preset(name, preset_data)
            return name
        return ""

    def save_state(self):
        """상태 저장"""
        if self.state:
            self.state.last_update = datetime.now().isoformat()
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.state), f, indent=2, ensure_ascii=False)

    def load_state(self) -> bool:
        """상태 복구"""
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.state = OptimizationState(**data)
                    return True
            except Exception:
                pass
        return False

    def run(self, resume: bool = False) -> dict:
        """배치 최적화 실행"""
        self.is_running = True
        self.is_paused = False
        
        # 심볼 조회
        if not self.symbols:
            self._update_status("🔍 심볼 조회 중...")
            self.fetch_symbols()
        
        # 상태 복구 또는 신규 시작
        start_idx = 0
        if resume and self.load_state():
            try:
                start_idx = self.symbols.index(self.state.current_symbol)
                self._update_status(f"♻️ {self.state.current_symbol}부터 재개 ({start_idx}/{len(self.symbols)})")
            except ValueError:
                start_idx = self.state.completed
        else:
            self.state = OptimizationState(
                exchange=self.exchange,
                timeframes=self.timeframes,
                total_symbols=len(self.symbols),
                completed=0,
                current_symbol='',
                started_at=datetime.now().isoformat(),
                last_update=datetime.now().isoformat(),
                failed_symbols=[],
                success_count=0,
                min_win_rate=self.min_win_rate,
                min_trades=self.min_trades,
                max_mdd=self.max_mdd
            )
        
        self._update_status(
            f"🚀 배치 최적화 시작: {len(self.symbols)}개 심볼 "
            f"(WR>={self.min_win_rate}%, MDD<={self.max_mdd}%, TR>={self.min_trades})"
        )
        
        # 최적화 루프
        for idx in range(start_idx, len(self.symbols)):
            if not self.is_running:
                self._update_status("⏹ 사용자에 의해 중지됨")
                break
            
            while self.is_paused:
                time.sleep(1)
                if not self.is_running:
                    break
            
            symbol = self.symbols[idx]
            self.state.current_symbol = symbol
            self.state.completed = idx
            
            self._update_progress(idx + 1, len(self.symbols), symbol)
            
            for tf in self.timeframes:
                if not self.is_running:
                    break
                
                self._update_status(f"🔧 [{idx+1}/{len(self.symbols)}] {symbol} {tf} 최적화 중...")
                
                result = self.optimize_symbol(symbol, tf)
                
                if result:
                    # Strict Filter Check
                    wr = result.get('win_rate', 0)
                    mdd = result.get('max_drawdown', 100)
                    tr = result.get('total_trades', 0)
                    
                    failed_reasons = []
                    if wr < self.min_win_rate:
                        failed_reasons.append(f"WinRate({wr:.1f}%)<{self.min_win_rate}%")
                    if mdd > self.max_mdd:
                        failed_reasons.append(f"MDD({mdd:.1f}%)>{self.max_mdd}%")
                    if tr < self.min_trades:
                        failed_reasons.append(f"Trades({tr})<{self.min_trades}")
                    
                    if not failed_reasons:
                        self.save_preset(symbol, tf, result)
                        self.state.success_count += 1
                        self._update_status(f"✅ {symbol} 통과: WR {wr:.1f}%, MDD {mdd:.1f}%")
                    else:
                        reason = ", ".join(failed_reasons)
                        if symbol not in [s.split(' ')[0] for s in self.state.failed_symbols]:
                            self.state.failed_symbols.append(f"{symbol} ({reason})")
                        self._update_status(f"❌ {symbol} 탈락: {reason}")
                else:
                    if symbol not in [s.split(' ')[0] for s in self.state.failed_symbols]:
                        self.state.failed_symbols.append(f"{symbol} (No Result)")
                
                self.save_state()
                time.sleep(0.5)
        
        self.is_running = False
        
        summary = self.get_summary()
        self._update_status(
            f"🎉 완료! 성공: {summary['success']}, 실패: {summary['failed']}, "
            f"총 프리셋: {summary['success']}개"
        )
        
        return summary
    
    def pause(self):
        """일시정지"""
        self.is_paused = True
        self._update_status("⏸ 일시정지됨 - 현재 작업 완료 후 대기")
    
    def resume(self):
        """재개"""
        self.is_paused = False
        self._update_status("▶️ 재개됨")
    
    def stop(self):
        """중지 (상태 저장)"""
        self.is_running = False
        self.is_paused = False
        self.save_state()
        self._update_status("⏹ 중지됨 (진행 상태 저장됨 - 이어하기 가능)")
    
    def get_summary(self) -> dict:
        """요약 정보 반환"""
        return {
            'exchange': self.exchange,
            'timeframes': self.timeframes,
            'total_symbols': len(self.symbols),
            'completed': self.state.completed if self.state else 0,
            'success': self.state.success_count if self.state else 0,
            'failed': len(self.state.failed_symbols) if self.state else 0,
            'failed_symbols': self.state.failed_symbols[:20] if self.state else [],
            'min_win_rate': self.min_win_rate,
            'max_mdd': self.max_mdd,
            'min_trades': self.min_trades
        }
