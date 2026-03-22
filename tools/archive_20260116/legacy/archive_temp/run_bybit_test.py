"""
Bybit BTC 백테스트 - AlphaX7 전략 (MACD + ADX + W/M Pattern)
필터 완화 버전 - 사용자님의 실제 20만 행 코드베이스 전략
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime

from core.strategy_core import AlphaX7Core, calculate_backtest_metrics
from utils.indicators import IndicatorGenerator
from config.parameters import DEFAULT_PARAMS

def main():
    print("=" * 80)
    print("Bybit BTC/USDT - AlphaX7 Strategy (MACD + ADX + W/M Pattern)")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n[1/4] Loading Parquet data...")
    data_path = Path("data/cache/bybit_btcusdt_15m.parquet")

    if not data_path.exists():
        print(f"[ERROR] File not found: {data_path}")
        return

    df = pd.read_parquet(data_path)
    print(f"[OK] Loaded {len(df):,} candles")

    # 2. 지표 계산 및 1h 리샘플링
    print("\n[2/4] Calculating indicators...")
    df_15m = IndicatorGenerator.add_all_indicators(df)

    # 1h 리샘플링
    from utils.data_utils import resample_data
    df_1h = resample_data(df_15m, '1h', add_indicators=True)

    print(f"[OK] Indicators added (15m: {len(df_15m)}, 1h: {len(df_1h)})")

    # 3. 전략 초기화 및 백테스트 (필터 완화)
    print("\n[3/4] Running backtest (RELAXED FILTERS)...")

    params = DEFAULT_PARAMS.copy()
    params['leverage'] = 3  # 3x leverage

    # 필터 완화 (W/M 패턴 감지 향상)
    params['pattern_tolerance'] = 0.05  # 0.03 → 0.05 (W/M 패턴 허용 범위 증가)
    params['entry_validity_hours'] = 12.0  # 6 → 12 (진입 유효 기간 연장)
    params['enable_adx_filter'] = False  # ADX 필터 비활성화
    params['adx_threshold'] = 20.0  # 25 → 20 (낮춤)

    print(f"  Pattern Tolerance: {params['pattern_tolerance']*100:.1f}%")
    print(f"  Entry Validity: {params['entry_validity_hours']}h")
    print(f"  ADX Filter: {params['enable_adx_filter']}")

    strategy = AlphaX7Core()

    # 백테스트 시뮬레이션
    capital = 100.0
    equity = capital
    position = None
    trades = []

    # 15m 기준으로 루프 (1h는 매핑 필요)
    for i in range(200, len(df_15m)):
        current = df_15m.iloc[i]

        # 포지션 없을 때
        if position is None:
            # 1h 인덱스 매핑 (15m 4개 = 1h 1개)
            i_1h = min(i // 4, len(df_1h) - 1)

            # 신호 감지 (1h, 15m 모두 전달 + 완화된 파라미터)
            df_1h_window = df_1h.iloc[:i_1h+1].copy()
            df_15m_window = df_15m.iloc[:i+1].copy()

            signal = strategy.detect_signal(
                df_1h_window,
                df_15m_window,
                pattern_tolerance=params.get('pattern_tolerance'),
                entry_validity_hours=params.get('entry_validity_hours'),
                enable_adx_filter=params.get('enable_adx_filter'),
                adx_threshold=params.get('adx_threshold')
            )

            if signal:
                position = {
                    'entry_idx': i,
                    'entry_price': current['close'],
                    'side': signal.signal_type,
                    'sl': signal.stop_loss,
                    'size': 0.01
                }

        # 포지션 있을 때
        else:
            # 손절 체크
            if position['side'] == 'Long':
                if current['low'] <= position['sl']:
                    # 청산
                    exit_price = position['sl']
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * params['leverage'] * 100

                    trades.append({'pnl': pnl_pct})
                    equity *= (1 + pnl_pct / 100)
                    position = None

            elif position['side'] == 'Short':
                if current['high'] >= position['sl']:
                    exit_price = position['sl']
                    pnl_pct = (position['entry_price'] - exit_price) / position['entry_price'] * params['leverage'] * 100

                    trades.append({'pnl': pnl_pct})
                    equity *= (1 + pnl_pct / 100)
                    position = None

    # 4. 결과 계산
    print("\n[4/4] Calculating results...")

    if len(trades) == 0:
        print("[ERROR] No trades executed")
        print("\n원인 분석:")
        print("  - 47일 데이터는 W/M 패턴 형성에 부족할 수 있음")
        print("  - MACD + ADX + W/M 패턴 필터가 여전히 엄격함")
        print("  - 더 긴 데이터(6개월~1년) 또는 추가 필터 완화 필요")
        return

    metrics = calculate_backtest_metrics(trades, leverage=params['leverage'])

    # 결과 출력
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)

    print(f"\n[Trade Statistics]")
    print(f"  Total Trades: {metrics['trade_count']:,}")
    print(f"  Win Rate: {metrics['win_rate']:.2f}%")

    print(f"\n[Returns]")
    print(f"  Total Return: {metrics['total_return']:.2f}%")
    print(f"  Final Capital: ${equity:.2f}")
    print(f"  Profit/Loss: ${equity - capital:.2f}")

    print(f"\n[Risk Metrics]")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")

    # 프리셋 저장
    preset_name = f"bybit_btc_alphax7_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    preset_data = {
        'name': preset_name,
        'exchange': 'bybit',
        'symbol': 'BTCUSDT',
        'timeframe': '15m',
        'strategy': 'AlphaX7',
        'params': params,
        'results': {
            'trades': len(trades),
            'win_rate': metrics['win_rate'],
            'total_return': metrics['total_return'],
            'max_drawdown': metrics['max_drawdown'],
            'profit_factor': metrics['profit_factor'],
            'sharpe_ratio': metrics['sharpe_ratio'],
            'final_capital': equity
        },
        'created_at': datetime.now().isoformat()
    }

    json_path = Path(f"data/{preset_name}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(preset_data, f, indent=2, ensure_ascii=False)

    print(f"\n[Preset Saved]")
    print(f"  {json_path}")

    print("\n" + "=" * 80)
    print("Completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
