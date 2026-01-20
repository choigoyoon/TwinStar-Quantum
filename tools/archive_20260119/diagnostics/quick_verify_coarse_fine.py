"""
Coarse-to-Fine 프리셋 간단 검증 스크립트
"""
import json
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
import pandas as pd


def main():
    # UTF-8 출력 설정
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # 프리셋 로드 (최신 파일 사용)
    preset_path = Path("presets/coarse_fine/bybit_BTCUSDT_1h_macd_20260117_235704.json")

    if not preset_path.exists():
        print(f"[ERROR] 프리셋 파일을 찾을 수 없습니다: {preset_path}")
        return

    with open(preset_path, 'r', encoding='utf-8') as f:
        preset = json.load(f)

    print("=" * 80)
    print("[PRESET VERIFICATION]")
    print("=" * 80)
    print(f"파일: {preset_path}")
    print(f"거래소: {preset['meta_info']['exchange']}")
    print(f"심볼: {preset['meta_info']['symbol']}")
    print(f"타임프레임: {preset['meta_info']['timeframe']}")
    print(f"전략: {preset['meta_info']['strategy_type']}")
    print()

    # 파라미터 출력
    params = preset['best_params']
    print("[SAVED PARAMETERS]:")
    for key, value in params.items():
        if value is not None:
            print(f"  {key}: {value}")
    print()

    # 저장된 성능 출력
    metrics = preset['best_metrics']
    print("[SAVED METRICS]:")
    print(f"  Win Rate: {metrics['win_rate']:.2f}%")
    print(f"  MDD: {metrics['mdd']:.2f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Total Trades: {metrics['total_trades']}")
    print(f"  Total PnL: {metrics['total_pnl']:.2f}")
    print()

    # 데이터 로드
    print("=" * 80)
    print("[DATA LOAD & BACKTEST]")
    print("=" * 80)

    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    print("[INFO] Loading 15m data...")
    dm.load_historical()
    df_15m = dm.df_entry_full

    if df_15m is None or len(df_15m) == 0:
        print("[ERROR] Failed to load 15m data")
        return

    print(f"[OK] 15m data loaded: {len(df_15m)} candles")

    # 1시간봉 리샘플링
    print("[INFO] Resampling (15m -> 1h)...")
    from utils.data_utils import resample_data
    df_1h = resample_data(df_15m, '1h', add_indicators=True)
    print(f"[OK] Resampling done: {len(df_1h)} candles")

    # 프리셋과 동일한 데이터 범위로 제한
    if 'total_candles' in preset['meta_info']:
        expected_candles = preset['meta_info']['total_candles']
        if len(df_1h) > expected_candles:
            print(f"[WARN] Data size mismatch: {len(df_1h)} vs {expected_candles} (expected)")
            print(f"[INFO] Truncating to match preset data range...")
            df_1h = df_1h.iloc[:expected_candles].copy()
            print(f"[OK] Data truncated: {len(df_1h)} candles")
    print()

    # 백테스트 실행
    print("[INFO] Running backtest...")

    # MACD 파라미터 확인 (프리셋에서 가져오기)
    params_with_macd = params.copy()
    print(f"[INFO] MACD params: fast={params_with_macd.get('macd_fast')}, "
          f"slow={params_with_macd.get('macd_slow')}, signal={params_with_macd.get('macd_signal')}")

    strategy = AlphaX7Core(
        use_mtf=True,
        strategy_type='macd'
    )

    # run_backtest는 df_pattern, df_entry 필요 (동일 데이터 사용)
    trades = strategy.run_backtest(
        df_pattern=df_1h,
        df_entry=df_1h,
        slippage=params_with_macd.get('slippage', 0),
        atr_mult=params_with_macd.get('atr_mult'),
        trail_start_r=params_with_macd.get('trail_start_r'),
        trail_dist_r=params_with_macd.get('trail_dist_r'),
        entry_validity_hours=params_with_macd.get('entry_validity_hours'),
        filter_tf=params_with_macd.get('filter_tf')
    )

    print(f"[OK] Backtest completed: {len(trades)} trades")
    print()

    # 메트릭 계산
    from utils.metrics import calculate_backtest_metrics
    actual_metrics = calculate_backtest_metrics(
        trades,
        leverage=params_with_macd.get('leverage', 1),
        capital=100.0
    )

    # 결과 비교
    print("=" * 80)
    print("[RESULT COMPARISON]")
    print("=" * 80)
    print(f"{'지표':<20} {'저장된 값':>15} {'백테스트 값':>15} {'차이':>15}")
    print("-" * 80)

    saved = metrics
    actual = actual_metrics

    comparisons = [
        ('Win Rate', saved['win_rate'], actual.get('win_rate', 0), '%'),
        ('MDD', saved['mdd'], actual.get('mdd', 0), '%'),
        ('Sharpe Ratio', saved['sharpe_ratio'], actual.get('sharpe_ratio', 0), ''),
        ('Profit Factor', saved['profit_factor'], actual.get('profit_factor', 0), ''),
        ('Total Trades', saved['total_trades'], actual.get('total_trades', 0), ''),
    ]

    for label, saved_val, actual_val, unit in comparisons:
        diff = actual_val - saved_val
        if unit:
            diff_str = f"{diff:+.2f}{unit}"
            print(f"{label:<20} {saved_val:>15.2f}{unit:<5} {actual_val:>15.2f}{unit:<5} {diff_str:>15}")
        else:
            diff_str = f"{diff:+.2f}"
            print(f"{label:<20} {saved_val:>15.2f}     {actual_val:>15.2f}     {diff_str:>15}")

    print("=" * 80)

    # 검증 결과
    print()
    print("[VERIFICATION RESULT]:")

    # 허용 오차 (±5%)
    tolerance = 0.05
    win_rate_match = abs(saved['win_rate'] - actual.get('win_rate', 0)) / saved['win_rate'] < tolerance
    sharpe_match = abs(saved['sharpe_ratio'] - actual.get('sharpe_ratio', 0)) / saved['sharpe_ratio'] < tolerance

    if win_rate_match and sharpe_match:
        print("[OK] Verification passed! Saved metrics match backtest results.")
    else:
        print("[WARNING] Saved metrics differ from backtest results.")
        print("          (Possible data update or parameter change)")


if __name__ == '__main__':
    main()
