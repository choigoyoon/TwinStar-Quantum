"""
Multi Time-Series Backtester
- 여러 심볼의 신호를 통합하여 시계열 백테스트 실행
- 2-Track 시뮬레이션 (BTC 고정 + 알트 복리)
- 동시 포지션 제한 및 자본 관리
"""

import json
import logging
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple, cast
from pathlib import Path

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

try:
    from paths import Paths
    PRESETS_DIR = Paths.PRESETS
    CACHE_DIR = Paths.CACHE
except ImportError:
    PRESETS_DIR = 'config/presets'
    CACHE_DIR = 'data/cache'

from core.strategy_core import AlphaX7Core

class MultiBacktester:
    """통합 시계열 백테스터"""
    
    def __init__(self, 
                 initial_alt_capital: float = 1000.0,
                 btc_fixed_amount: float = 100.0,
                 exchange: str = 'bybit'):
        
        self.initial_alt_capital = initial_alt_capital
        self.btc_fixed_amount = btc_fixed_amount
        self.exchange = exchange.lower()
        
        self.presets_dir = Path(PRESETS_DIR)
        self.cache_dir = Path(CACHE_DIR)
        
        self.core = AlphaX7Core(use_mtf=True)
        
        logging.info(f"[MULTI-BT] Initialized: BTC=${btc_fixed_amount}, Alt_Start=${initial_alt_capital}")

    def load_all_presets(self) -> List[Dict]:
        """모든 유효한 프리셋 로드"""
        presets = []
        for f in self.presets_dir.glob(f"{self.exchange}_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as f_in:
                    data = json.load(f_in)
                    # _meta 정보 확인
                    meta = data.get('_meta', {})
                    if not meta: continue
                    
                    presets.append(data)
            except Exception as e:
                logging.warning(f"[MULTI-BT] Failed to load preset {f.name}: {e}")
        
        logging.info(f"[MULTI-BT] Loaded {len(presets)} presets")
        return presets

    def _get_data(self, symbol: str, timeframe: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """데이터 로드 및 리샘플링"""
        file_15m = self.cache_dir / f"{self.exchange}_{symbol.lower()}_15m.parquet"
        if not file_15m.exists():
            return None, None
            
        try:
            df_15m = pd.read_parquet(file_15m)
            if len(df_15m) < 500: return None, None
            
            # 타임스탬프 처리
            if 'timestamp' in df_15m.columns:
                if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
                    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
                else:
                    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
            
            # 1H 패턴용 리샘플링
            df_temp = df_15m.set_index('timestamp')
            df_pattern = df_temp.resample('1h').agg({
                'open': 'first', 'high': 'max', 'low': 'min',
                'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
            
            # 지표 추가
            from utils.indicators import IndicatorGenerator
            df_15m = IndicatorGenerator.add_all_indicators(df_15m)
            df_pattern = IndicatorGenerator.add_all_indicators(df_pattern)
            
            return df_pattern, df_15m
        except Exception as e:
            logging.error(f"[MULTI-BT] Data error {symbol}: {e}")
            return None, None

    def collect_all_signals(self, presets: List[Dict]) -> List[Dict]:
        """모든 프리셋의 개별 신호 수집 및 정렬"""
        all_signals = []
        
        for preset in presets:
            symbol = preset['_meta']['symbol']
            tf = preset['_meta']['timeframe']
            
            logging.info(f"[MULTI-BT] Processing signals for {symbol}...")
            
            df_pattern, df_entry = self._get_data(symbol, tf)
            if df_pattern is None: continue
            
            # 파라미터 추출 (평탄화 및 필터링)
            params = {}
            # 1. 최상위 키 중 '_'로 시작하지 않는 것들
            for k, v in preset.items():
                if not k.startswith('_') and k != 'params':
                    params[k] = v
            # 2. 'params' 키 내부에 있는 것들 (우선순위 높음)
            if 'params' in preset:
                params.update(preset['params'])
            
            # 3. run_backtest가 받는 필드만 남기기
            allowed_keys = [
                'slippage', 'atr_mult', 'trail_start_r', 'trail_dist_r',
                'pattern_tolerance', 'entry_validity_hours', 'pullback_rsi_long',
                'pullback_rsi_short', 'max_adds', 'filter_tf', 'rsi_period',
                'atr_period', 'enable_pullback'
            ]
            params = {k: v for k, v in params.items() if k in allowed_keys and k != 'filter_tf'}
            
            # 개별 백테스트 실행
            if df_entry is None: continue
            
            result = self.core.run_backtest(
                df_pattern=df_pattern,
                df_entry=df_entry,
                **params,
                filter_tf=tf
            )
            # run_backtest는 List[Dict] 또는 Tuple[List[Dict], Dict]를 반환할 수 있음
            trades: List[Dict[Any, Any]] = result[0] if isinstance(result, tuple) else result

            for t in trades:
                t['symbol'] = symbol
                # 간단 판별: BTCUSDT 이거나, BTC가 포함되고 USDT 페어인 경우 (ETHBTC 등 제외)
                # 정확하진 않지만 대부분의 경우 작동. 더 정확히는 is_btc 파라미터를 프리셋에 넣는게 좋음.
                sym_upper = symbol.upper()
                is_btc_pair = (sym_upper == 'BTCUSDT' or 
                              ('BTC' in sym_upper and 'USDT' in sym_upper and '/' not in sym_upper))
                
                t['is_btc'] = is_btc_pair
                
                all_signals.append(t)
        
        # 시간순 정렬 (entry_time 기준)
        all_signals.sort(key=lambda x: x['entry_time'])
        return all_signals

    def run_simulation(self, signals: List[Dict]) -> Dict:
        """통합 시계열 시뮬레이션 루프"""
        alt_capital = self.initial_alt_capital
        btc_capital = 0.0 # BTC 총 수익 추적
        
        active_positions: Dict[str, Optional[Dict[str, Any]]] = {
            'btc': None,
            'alt': None
        }
        
        history = []
        
        # Track B (Alt)의 시계열 자본 기록
        equity_curve = []
        
        for sig in signals:
            is_btc = sig['is_btc']
            entry_time = sig['entry_time']
            exit_time = sig['exit_time']
            pnl_pct = sig.get('pnl', 0.0) # AlphaX7Core uses 'pnl' for percentage profit
            
            track = 'btc' if is_btc else 'alt'
            
            # [LOGIC] 동일 트랙 내 포지션 중첩 제한 (단순화: 이전 포지션 종료 후 다음 진입 가능)
            last_pos = active_positions[track]
            if last_pos and last_pos['exit_time'] > entry_time:
                # 겹치는 포지션 스킵 (실제 거래소 제약 반영)
                continue
            
            # 진입 처리
            if is_btc:
                # Track A: $100 고정 진입
                trade_pnl = self.btc_fixed_amount * (pnl_pct / 100)
                btc_capital += trade_pnl
            else:
                # Track B: 전액 복리 진입
                trade_pnl = alt_capital * (pnl_pct / 100)
                alt_capital += trade_pnl
            
            active_positions[track] = sig
            
            history.append({
                'time': exit_time,
                'symbol': sig['symbol'],
                'track': track,
                'pnl_pct': pnl_pct,
                'pnl_usd': trade_pnl,
                'current_alt_cap': alt_capital,
                'total_btc_pnl': btc_capital
            })
            
            equity_curve.append({
                'time': exit_time,
                'equity': alt_capital + btc_capital
            })

        # 결과 분석
        if not history:
            return {'error': 'No trades executed'}
            
        total_pnl_usd = (alt_capital - self.initial_alt_capital) + btc_capital
        total_return_pct = (total_pnl_usd / self.initial_alt_capital) * 100
        
        wins = [h for h in history if h['pnl_pct'] > 0]
        win_rate = len(wins) / len(history)
        
        # MDD 계산
        max_equity = 0
        max_dd = 0
        curr_total = self.initial_alt_capital
        for h in history:
            curr_total = self.initial_alt_capital + (h['current_alt_cap'] - self.initial_alt_capital) + h['total_btc_pnl']
            max_equity = max(max_equity, curr_total)
            dd = (max_equity - curr_total) / max_equity if max_equity > 0 else 0
            max_dd = max(max_dd, dd)

        return {
            'summary': {
                'total_trades': len(history),
                'win_rate': win_rate,
                'final_alt_capital': alt_capital,
                'total_btc_pnl': btc_capital,
                'total_pnl_usd': total_pnl_usd,
                'total_return_pct': total_return_pct,
                'max_drawdown': max_dd * 100
            },
            'history': history,
            'equity_curve': equity_curve
        }

    def execute_all(self) -> Dict:
        """전체 프로세스 실행"""
        logging.info("[MULTI-BT] Starting full multi-backtest...")
        presets = self.load_all_presets()
        if not presets:
            return {'error': 'No presets found'}
            
        signals = self.collect_all_signals(presets)
        if not signals:
            return {'error': 'No signals collected'}
            
        return self.run_simulation(signals)

# 메인 실행부 (CLI 테스트용)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    bt = MultiBacktester(initial_alt_capital=1000, btc_fixed_amount=100)
    result = bt.execute_all()
    
    if result.get('error'):
        logger.error(f"Error: {result.get('error')}")
    else:
        s = result.get('summary', {})
        logger.info("\n" + "="*40)
        logger.info("통합 시계열 백테스트 결과")
        logger.info("="*40)
        logger.info(f"총 거래 수: {s['total_trades']}")
        logger.info(f"승률: {s['win_rate']*100:.1f}%")
        logger.info(f"최종 알트 자본: ${s['final_alt_capital']:.2f}")
        logger.info(f"총 BTC 수익: ${s['total_btc_pnl']:.2f}")
        logger.info(f"전체 수익: ${s['total_pnl_usd']:.2f} ({s['total_return_pct']:.1f}%)")
        logger.info(f"최대 낙폭 (MDD): {s['max_drawdown']:.1f}%")
        logger.info("="*40)

