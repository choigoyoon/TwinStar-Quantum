# C:\매매전략\test_params_compare.py

import sys
import os
import pandas as pd
from datetime import datetime

# 프로젝트 루트 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.strategy_core import AlphaX7Core

# [FIX] DataManager 대신 직접 데이터 로드
def load_data(symbol, tf, exchange="bybit"):
    # 파일명 소문자 처리 및 거래소 접두어 추가
    filename = f"{exchange.lower()}_{symbol.lower()}_{tf.lower()}.parquet"
    cache_path = os.path.join(current_dir, 'data', 'cache', filename)
    if os.path.exists(cache_path):
        return pd.read_parquet(cache_path)
    return None

# 테스트 심볼
SYMBOL = "BTCUSDT"
EXCHANGE = "bybit"

# 두 가지 설정
STRICT_PARAMS = {
    'pattern_tolerance': 0.03,
    'entry_validity_hours': 12,
    'pullback_rsi_long': 40,
    'pullback_rsi_short': 60,
    'atr_mult': 1.5,
    'trail_start_r': 0.8,
    'trail_dist_r': 0.5,
}

LOOSE_PARAMS = {
    'pattern_tolerance': 0.05,
    'entry_validity_hours': 48,
    'pullback_rsi_long': 45,
    'pullback_rsi_short': 55,
    'atr_mult': 1.5,
    'trail_start_r': 0.8,
    'trail_dist_r': 0.5,
}

def run_test(params, name):
    print(f"\n{'='*50}")
    print(f"테스트: {name}")
    print(f"{'='*50}")
    
    # 데이터 로드
    df_1h = load_data(SYMBOL, '1h', EXCHANGE)
    df_15m = load_data(SYMBOL, '15m', EXCHANGE)
    
    if df_1h is None or df_15m is None:
        print(f"데이터 없음: {SYMBOL} 1h/15m 캐시 파일을 찾을 수 없습니다.")
        return None
    
    # 백테스트 실행
    core = AlphaX7Core(use_mtf=True)
    trades = core.run_backtest(
        df_pattern=df_1h,
        df_entry=df_15m,
        **params
    )
    
    if not trades:
        print("거래 없음")
        return None
    
    # 결과 계산
    def to_float(val):
        if isinstance(val, str):
            return float(val.replace('%',''))
        return float(val)

    wins = [t for t in trades if to_float(t['pnl']) > 0]
    total = len(trades)
    win_rate = len(wins) / total * 100 if total > 0 else 0
    total_pnl = sum(to_float(t['pnl']) for t in trades)
    avg_pnl = total_pnl / total if total > 0 else 0
    
    print(f"거래 수: {total}")
    print(f"승률: {win_rate:.1f}%")
    print(f"총 수익: {total_pnl:.2f}%")
    print(f"평균 수익: {avg_pnl:.2f}%")
    
    return {
        'trades': total,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl
    }

if __name__ == "__main__":
    print(f"🚀 파라미터 비교 분석 시작 (Target: {SYMBOL})")
    strict = run_test(STRICT_PARAMS, "엄격 (3%, 12h, 40/60)")
    loose = run_test(LOOSE_PARAMS, "느슨 (5%, 48h, 45/55)")
    
    print(f"\n{'='*50}")
    print("최종 비교 리포트")
    print(f"{'='*50}")
    
    if strict and loose:
        print(f"| 항목 | 엄격 | 느슨 | 차이 |")
        print(f"|------|------|------|------|")
        print(f"| 거래 수 | {strict['trades']} | {loose['trades']} | {loose['trades'] - strict['trades'] :+d} |")
        print(f"| 승률 | {strict['win_rate']:.1f}% | {loose['win_rate']:.1f}% | {loose['win_rate'] - strict['win_rate'] :+.1f}% |")
        print(f"| 총 수익 | {strict['total_pnl']:.1f}% | {loose['total_pnl']:.1f}% | {loose['total_pnl'] - strict['total_pnl'] :+.1f}% |")
    else:
        print("결과를 산출할 수 없습니다. 데이터가 충분한지 확인하세요.")
