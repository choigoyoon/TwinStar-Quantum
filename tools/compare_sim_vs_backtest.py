# compare_sim_vs_backtest.py
"""시뮬레이터 vs 백테스트 비교 테스트"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime

def main():
    print("=" * 60)
    print("🔬 시뮬레이터 vs 백테스트 비교 테스트")
    print("=" * 60)
    
    # 1. 데이터 로드
    parquet_path = "data/cache/bybit_btcusdt_15m.parquet"
    
    try:
        df = pd.read_parquet(parquet_path)
        print(f"\n✅ 데이터 로드: {len(df):,}봉")
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return
    
    # timestamp 변환
    if df['timestamp'].dtype == 'int64':
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 지표 추가
    try:
        from indicator_generator import IndicatorGenerator
        df = IndicatorGenerator.add_all_indicators(df)
        if 'rsi' not in df.columns and 'rsi_14' in df.columns:
            df['rsi'] = df['rsi_14']
        if 'atr' not in df.columns and 'atr_14' in df.columns:
            df['atr'] = df['atr_14']
        print("✅ 지표 추가 완료")
    except Exception as e:
        print(f"⚠️ 지표 추가 실패: {e}")
    
    # 테스트 범위 설정 (최근 3000봉)
    test_start = max(200, len(df) - 3000)
    test_end = len(df)
    print(f"📊 테스트 범위: {test_start} ~ {test_end} ({test_end - test_start:,}봉)")
    
    # 2. 백테스트 실행
    print("\n" + "-" * 60)
    print("📈 백테스트 실행 중...")
    print("-" * 60)
    
    try:
        from core.strategy_core import AlphaX7Core
        
        strategy = AlphaX7Core()
        
        # 1H 리샘플링
        df_15m = df.iloc[test_start:test_end].copy()
        df_15m['datetime'] = df_15m['timestamp']
        df_temp = df_15m.set_index('datetime')
        
        df_1h = df_temp.resample('1H').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 
            'close': 'last', 'volume': 'sum'
        }).dropna().reset_index()
        df_1h['timestamp'] = df_1h['datetime']
        
        # 지표 추가
        df_1h = IndicatorGenerator.add_all_indicators(df_1h)
        if 'rsi' not in df_1h.columns and 'rsi_14' in df_1h.columns:
            df_1h['rsi'] = df_1h['rsi_14']
        
        print(f"   1H 데이터: {len(df_1h)}봉")
        
        # 백테스트 파라미터
        params = {
            'atr_mult': 1.5,
            'trail_start_r': 1.0,
            'trail_dist_r': 0.2,
            'pattern_tolerance': 0.03,
            'entry_validity_hours': 6,
            'pullback_rsi_long': 40,
            'pullback_rsi_short': 60,
            'filter_tf': '4h'
        }
        
        # 백테스트 실행
        bt_result = strategy.run_backtest(
            df_pattern=df_1h,
            df_entry=df_15m.reset_index(drop=True),
            slippage=0.001,  # 0.1%
            atr_mult=params['atr_mult'],
            trail_start_r=params['trail_start_r'],
            trail_dist_r=params['trail_dist_r'],
            pattern_tolerance=params['pattern_tolerance'],
            entry_validity_hours=params['entry_validity_hours'],
            pullback_rsi_long=params['pullback_rsi_long'],
            pullback_rsi_short=params['pullback_rsi_short'],
            filter_tf=params['filter_tf']
        )
        
        bt_trades = bt_result if bt_result else []
        print(f"\n✅ 백테스트 완료: {len(bt_trades)}건 거래")
        
        if bt_trades:
            bt_wins = len([t for t in bt_trades if t.get('pnl', 0) > 0])
            bt_pnl = sum(t.get('pnl', 0) for t in bt_trades)
            print(f"   승률: {bt_wins/len(bt_trades)*100:.1f}%")
            print(f"   총 PnL: {bt_pnl:+.2f}%")
        
    except Exception as e:
        import traceback
        print(f"❌ 백테스트 실패: {e}")
        traceback.print_exc()
        bt_trades = []
    
    # 3. 시뮬레이터 실행
    print("\n" + "-" * 60)
    print("🔬 시뮬레이터 실행 중...")
    print("-" * 60)
    
    try:
        from tools.realtime_simulator import RealtimeSimulator
        
        sim = RealtimeSimulator(parquet_path, "default")
        sim.df = df  # 이미 로드한 데이터 사용
        sim.load_preset()
        
        # 시뮬레이션 실행 (조용한 모드)
        sim_trades = sim.run(start_idx=test_start, end_idx=test_end, verbose=False)
        
        print(f"\n✅ 시뮬레이션 완료: {len(sim_trades)}건 거래")
        
        if sim_trades:
            sim_wins = len([t for t in sim_trades if t['pnl'] > 0])
            sim_pnl = sum(t['pnl'] for t in sim_trades)
            print(f"   승률: {sim_wins/len(sim_trades)*100:.1f}%")
            print(f"   총 PnL: {sim_pnl:+.2f}%")
        
    except Exception as e:
        import traceback
        print(f"❌ 시뮬레이션 실패: {e}")
        traceback.print_exc()
        sim_trades = []
    
    # 4. 비교 결과
    print("\n" + "=" * 60)
    print("📊 비교 결과")
    print("=" * 60)
    
    print(f"\n{'항목':<20} {'백테스트':>15} {'시뮬레이터':>15} {'차이':>15}")
    print("-" * 65)
    
    bt_count = len(bt_trades)
    sim_count = len(sim_trades)
    print(f"{'거래 수':<20} {bt_count:>15} {sim_count:>15} {abs(bt_count-sim_count):>15}")
    
    if bt_trades:
        bt_winrate = len([t for t in bt_trades if t.get('pnl', 0) > 0]) / len(bt_trades) * 100
    else:
        bt_winrate = 0
        
    if sim_trades:
        sim_winrate = len([t for t in sim_trades if t['pnl'] > 0]) / len(sim_trades) * 100
    else:
        sim_winrate = 0
        
    print(f"{'승률':<20} {bt_winrate:>14.1f}% {sim_winrate:>14.1f}% {abs(bt_winrate-sim_winrate):>14.1f}%")
    
    bt_pnl = sum(t.get('pnl', 0) for t in bt_trades)
    sim_pnl = sum(t['pnl'] for t in sim_trades) if sim_trades else 0
    print(f"{'총 PnL':<20} {bt_pnl:>14.2f}% {sim_pnl:>14.2f}% {abs(bt_pnl-sim_pnl):>14.2f}%")
    
    # 일치율 계산
    if bt_count > 0:
        match_rate = (1 - abs(bt_count - sim_count) / bt_count) * 100
        print(f"\n{'거래 수 일치율':<20} {match_rate:.1f}%")
    
    print("\n" + "=" * 60)
    
    # 결과 판정
    if bt_count > 0 and sim_count > 0:
        diff_pct = abs(bt_count - sim_count) / bt_count * 100
        if diff_pct < 10:
            print("✅ 결과: 로직 거의 일치 (차이 < 10%)")
        elif diff_pct < 25:
            print("🟡 결과: 약간의 차이 있음 (10% ~ 25%)")
        else:
            print("❌ 결과: 상당한 차이 존재 (> 25%)")
            print("   → 패턴 감지 로직 또는 진입/청산 조건 확인 필요")
    
    return bt_trades, sim_trades

if __name__ == "__main__":
    main()
