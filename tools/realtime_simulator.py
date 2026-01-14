# realtime_simulator.py - 백테스트 로직 100% 동일 검증
"""
strategy_core.py의 run_backtest를 직접 사용하여
봉 1개씩 추가하면서 매매 결과 확인
"""
import sys
sys.path.insert(0, 'c:/매매전략')
import os
os.chdir('c:/매매전략')

import pandas as pd
import argparse
from datetime import datetime

from core.strategy_core import AlphaX7Core

try:
    from utils.indicators import IndicatorGenerator
except ImportError:
    IndicatorGenerator = None

try:
    from utils.preset_manager import get_preset_manager
except ImportError:
    def get_preset_manager(): return None


class RealtimeSimulator:
    """strategy_core.run_backtest 직접 호출 시뮬레이터"""
    
    def __init__(self, parquet_path: str, preset_name: str = None):
        self.parquet_path = parquet_path
        self.preset_name = preset_name
        self.df_15m = None
        self.params = {}
        self.trades = []
    
    def load_data(self):
        """데이터 로드"""
        print("\n" + "=" * 50)
        print("🔬 실매매 로직 검증 시뮬레이터")
        print("   (strategy_core.run_backtest 직접 호출)")
        print("=" * 50)
        
        self.df_15m = pd.read_parquet(self.parquet_path)
        
        if 'timestamp' in self.df_15m.columns:
            if self.df_15m['timestamp'].dtype == 'int64':
                self.df_15m['timestamp'] = pd.to_datetime(self.df_15m['timestamp'], unit='ms')
        
        self.df_15m = self.df_15m.sort_values('timestamp').reset_index(drop=True)
        
        print(f"📁 파일: {os.path.basename(self.parquet_path)}")
        print(f"📊 봉 수: {len(self.df_15m):,}개")
        
        return self
    
    def load_preset(self):
        """프리셋 로드"""
        pm = get_preset_manager()
        if pm and self.preset_name:
            try:
                self.params = pm.load_preset_flat(self.preset_name)
                print(f"⚙️ 프리셋: {self.preset_name}")
                print(f"   ATR: {self.params.get('atr_mult', 1.25)} | "
                      f"Trail: {self.params.get('trail_start_r', 0.8)}/{self.params.get('trail_dist_r', 0.1)} | "
                      f"RSI: {self.params.get('pullback_rsi_long', 40)}/{self.params.get('pullback_rsi_short', 60)}")
            except Exception as e:
                print(f"⚠️ 프리셋 로드 실패: {e}")
                self.params = {}
        else:
            self.params = {}
            print(f"⚙️ 프리셋: Default")
        
        return self
    
    def _resample_to_1h(self, df: pd.DataFrame) -> pd.DataFrame:
        """15분봉 → 1시간봉 리샘플링"""
        df = df.copy()
        df['datetime'] = df['timestamp']
        df = df.set_index('datetime')
        
        resampled = df.resample('1h').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna().reset_index()
        
        resampled['timestamp'] = resampled['datetime']
        
        if IndicatorGenerator:
            resampled = IndicatorGenerator.add_all_indicators(resampled)
        
        return resampled
    
    def run(self, start_idx=200, end_idx=None, verbose=True):
        """시뮬레이션 실행 - 봉 1개씩 추가하며 run_backtest 호출"""
        df = self.df_15m
        end_idx = end_idx or len(df)
        total = end_idx - start_idx
        
        print(f"\n{'─' * 50}")
        print(f"🚀 시뮬레이션: 봉 {start_idx} ~ {end_idx} ({total:,}봉)")
        print(f"{'─' * 50}")
        
        # 전략 초기화
        strategy = AlphaX7Core(use_mtf=True)
        
        # 파라미터 설정
        params = {
            'slippage': self.params.get('slippage', 0.0005),
            'atr_mult': self.params.get('atr_mult', 1.25),
            'trail_start_r': self.params.get('trail_start_r', 0.8),
            'trail_dist_r': self.params.get('trail_dist_r', 0.1),
            'pattern_tolerance': self.params.get('pattern_tolerance', 0.03),
            'entry_validity_hours': self.params.get('entry_validity_hours', 6.0),
            'pullback_rsi_long': self.params.get('pullback_rsi_long', 40),
            'pullback_rsi_short': self.params.get('pullback_rsi_short', 60),
            'filter_tf': self.params.get('filter_tf', '4h'),
            'rsi_period': self.params.get('rsi_period', 14),
            'atr_period': self.params.get('atr_period', 14),
        }
        
        # 1. 먼저 전체 백테스트 결과 (기준)
        print("\n⏳ 전체 백테스트 실행 중...")
        df_full = df.iloc[:end_idx].copy()
        
        if IndicatorGenerator:
            df_full = IndicatorGenerator.add_all_indicators(df_full)
        
        df_1h_full = self._resample_to_1h(df_full)
        
        full_trades = strategy.run_backtest(
            df_pattern=df_1h_full,
            df_entry=df_full,
            return_state=False,
            **params
        )
        
        print(f"   백테스트 결과: {len(full_trades)}건")
        
        # 2. 봉 1개씩 추가하면서 증분 시뮬레이션
        print("\n⏳ 증분 시뮬레이션 시작...")
        
        prev_trade_count = 0
        progress_interval = max(1, total // 20)
        
        entry_times = []  # 진입 시점 기록
        
        for i in range(start_idx, end_idx):
            # 현재까지의 데이터
            df_so_far = df.iloc[:i+1].copy()
            
            if IndicatorGenerator:
                df_so_far = IndicatorGenerator.add_all_indicators(df_so_far)
            
            df_1h = self._resample_to_1h(df_so_far)
            
            # 백테스트 실행 (현재까지 데이터로)
            trades, state = strategy.run_backtest(
                df_pattern=df_1h,
                df_entry=df_so_far,
                return_state=True,
                **params
            )
            
            # 새 거래 발생 확인
            if len(trades) > prev_trade_count:
                new_trades = trades[prev_trade_count:]
                for t in new_trades:
                    entry_time = t.get('entry_time', df_so_far['timestamp'].iloc[-1])
                    entry_times.append(entry_time)
                    
                    if verbose:
                        direction = t.get('type', '?')
                        entry_price = t.get('entry', 0)
                        pnl = t.get('pnl_pct', t.get('pnl', 0))
                        emoji = "🟢" if direction == 'Long' else "🔴"
                        result = "✅" if pnl > 0 else "❌"
                        print(f"[{entry_time}] {emoji} {direction} @ ${entry_price:,.0f} → {result} {pnl:+.2f}%")
                
                prev_trade_count = len(trades)
            
            # 진행률
            if (i - start_idx) % progress_interval == 0:
                pct = (i - start_idx) / total * 100
                ts = df_so_far['timestamp'].iloc[-1]
                price = df_so_far['close'].iloc[-1]
                pending = len(state.get('pending', []))
                print(f"[{pct:5.1f}%] {ts} | ${price:,.0f} | 거래: {len(trades)}건 | 대기: {pending}개")
        
        # 결과 저장
        self.trades = trades if trades else []
        
        # 결과 출력
        self._print_results(full_trades, trades)
        
        return trades
    
    def _print_results(self, full_trades, sim_trades):
        """결과 비교"""
        print(f"\n{'=' * 50}")
        print(f"📈 시뮬레이션 결과")
        print(f"{'=' * 50}")
        
        print(f"\n[비교]")
        print(f"   전체 백테스트: {len(full_trades)}건")
        print(f"   증분 시뮬레이션: {len(sim_trades)}건")
        
        if len(full_trades) == len(sim_trades):
            print(f"   ✅ 일치!")
        else:
            print(f"   ❌ 불일치 (차이: {len(full_trades) - len(sim_trades)}건)")
        
        if sim_trades:
            wins = [t for t in sim_trades if t.get('pnl_pct', t.get('pnl', 0)) > 0]
            total_pnl = sum(t.get('pnl_pct', t.get('pnl', 0)) for t in sim_trades)
            win_rate = len(wins) / len(sim_trades) * 100
            
            print(f"\n[통계]")
            print(f"   승률: {win_rate:.1f}% ({len(wins)}/{len(sim_trades)})")
            print(f"   총 수익: {total_pnl:.2f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='실매매 로직 검증 시뮬레이터')
    parser.add_argument('-d', '--data', required=True, help='parquet 파일')
    parser.add_argument('-p', '--preset', default=None, help='프리셋 이름')
    parser.add_argument('-s', '--start', type=int, default=200)
    parser.add_argument('-e', '--end', type=int, default=None)
    parser.add_argument('-q', '--quiet', action='store_true')
    args = parser.parse_args()
    
    sim = RealtimeSimulator(args.data, args.preset)
    sim.load_data().load_preset()
    sim.run(args.start, args.end, verbose=not args.quiet)
