import os
import pandas as pd
import numpy as np
from core.strategy_core import AlphaX7Core
from core.multi_symbol_backtest import MultiSymbolBacktest

def diagnose():
    print("🔍 [DIAGNOSE] Starting Backtest Diagnosis (v1.7.0)...")
    
    # 1. BTC 15m 데이터 로드
    msb = MultiSymbolBacktest(exchange='bybit')
    df_15m = msb.load_candle_data('BTCUSDT', '15m')
    
    if df_15m is None:
        print("❌ BTCUSDT 15m 데이터를 찾을 수 없습니다.")
        return

    print(f"✅ 데이터 로드 완료: {len(df_15m)} 캔들")
    
    # 2. 1H/4H 리샘플링
    from utils.data_utils import resample_data
    df_pattern = resample_data(df_15m, '1h', add_indicators=True)
    df_entry = df_15m.copy()
    # Indicators are needed for both
    from indicator_generator import IndicatorGenerator
    df_entry = IndicatorGenerator.add_all_indicators(df_entry)
    
    print(f"📊 리샘플링 완료: Pattern(1H)={len(df_pattern)}, Entry(15m)={len(df_entry)}")
    
    # 3. 백테스트 실행 (v1.5.8 스타일 파라미터 가정)
    strategy = AlphaX7Core(use_mtf=True)
    
    # 표준 파라미터 (v1.5.8에서 자주 쓰던 값 예시)
    params = {
        'atr_mult': 1.5,
        'trail_start_r': 0.8,
        'trail_dist_r': 0.5,
        'pattern_tolerance': 0.03,
        'entry_validity_hours': 12.0,
        'filter_tf': '4h',
        'slippage': 0.00105  # slippage(0.0005) + fee(0.00055)
    }
    
    print(f"⚙️ 백테스트 파라미터: {params}")
    
    trades = strategy.run_backtest(
        df_pattern=df_pattern,
        df_entry=df_entry,
        **params
    )
    
    if not trades:
        print("⚠️ 거래 내역이 없습니다.")
        return

    # 4. 결과 집계
    from utils.data_utils import calculate_pnl_metrics
    pnls = [t['pnl'] for t in trades]
    metrics = calculate_pnl_metrics(pnls)
    
    print("\n" + "="*40)
    print("📈 BTCUSDT 4H 백테스트 진단 결과 (v1.7.0)")
    print("="*40)
    print(f"총 거래 수: {metrics['total_trades'] if 'total_trades' in metrics else len(trades)}")
    print(f"승률: {metrics['win_rate']}%")
    print(f"수익률 (단리): {metrics['simple_return']}%")
    print(f"수익률 (복리): {metrics['compound_return']}%")
    print(f"Profit Factor: {metrics['profit_factor']}")
    print(f"MDD: {metrics['max_drawdown']}%")
    print("="*40)
    
    # 5. 샘플 거래 로그 (첫 3개)
    print("\n📝 샘플 거래 (첫 3개):")
    for i, t in enumerate(trades[:3]):
        print(f"{i+1}. {t['entry_time']} | {t['type']} | Entry: {t['entry']:.1f} | Exit: {t['exit']:.1f} | PnL: {t['pnl']:.2f}%")

if __name__ == "__main__":
    diagnose()
