"""
AlphaX7 전략 백테스트 (필터 완화 버전)
MACD + ADX + W/M 패턴 기반
"""
import pandas as pd
from pathlib import Path
import json
from datetime import datetime

from core.strategy_core import AlphaX7Core, calculate_backtest_metrics
from utils.indicators import IndicatorGenerator
from config.parameters import DEFAULT_PARAMS
from utils.data_utils import resample_data

def main():
    print("=" * 80)
    print("AlphaX7 Strategy Backtest (MACD + ADX + W/M Pattern)")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n[1/4] Loading data...")
    data_path = Path("data/cache/bybit_btcusdt_15m.parquet")

    if not data_path.exists():
        print(f"[ERROR] File not found: {data_path}")
        return

    df = pd.read_parquet(data_path)
    print(f"[OK] Loaded {len(df):,} candles")
    print(f"     Period: {df['timestamp'].min()} ~ {df['timestamp'].max()}")

    # 2. 지표 계산
    print("\n[2/4] Calculating indicators...")
    df_15m = IndicatorGenerator.add_all_indicators(df)
    df_1h = resample_data(df_15m, '1h', add_indicators=True)
    print(f"[OK] 15m: {len(df_15m)}, 1h: {len(df_1h)}")

    # 3. 전략 파라미터 (필터 완화)
    print("\n[3/4] Initializing strategy (relaxed filters)...")

    params = DEFAULT_PARAMS.copy()
    params['leverage'] = 3  # 3x leverage

    # 필터 완화
    params['pattern_tolerance'] = 0.05  # 0.03 → 0.05 (W/M 패턴 허용 범위 증가)
    params['entry_validity_hours'] = 12.0  # 6 → 12 (진입 유효 기간 연장)
    params['enable_adx_filter'] = False  # ADX 필터 비활성화 (트렌드 강도 무시)
    params['adx_threshold'] = 20.0  # 25 → 20 (ADX 필터 사용 시 낮춤)

    print(f"[Parameters]")
    print(f"  Pattern Tolerance: {params['pattern_tolerance']*100:.1f}%")
    print(f"  Entry Validity: {params['entry_validity_hours']}h")
    print(f"  ADX Filter: {params['enable_adx_filter']}")
    print(f"  Leverage: {params['leverage']}x")

    strategy = AlphaX7Core()

    # 4. 백테스트 시뮬레이션
    capital = 100.0
    equity = capital
    position = None
    trades = []

    print("\n[4/4] Running backtest...")

    for i in range(200, len(df_15m)):
        current = df_15m.iloc[i]

        # 포지션 없을 때 - 신호 감지
        if position is None:
            i_1h = min(i // 4, len(df_1h) - 1)
            df_1h_window = df_1h.iloc[:i_1h+1].copy()
            df_15m_window = df_15m.iloc[:i+1].copy()

            # 신호 감지 (완화된 파라미터 전달)
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

        # 포지션 있을 때 - 손절 체크
        else:
            exit_triggered = False

            if position['side'] == 'Long':
                if current['low'] <= position['sl']:
                    exit_price = position['sl']
                    exit_triggered = True
            elif position['side'] == 'Short':
                if current['high'] >= position['sl']:
                    exit_price = position['sl']
                    exit_triggered = True

            if exit_triggered:
                entry_price = position['entry_price']

                # PnL 계산
                if position['side'] == 'Long':
                    pnl_pct = (exit_price - entry_price) / entry_price * params['leverage'] * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * params['leverage'] * 100

                # 수수료 차감 (0.1% × 2)
                fee_pct = 0.1 * 2
                pnl_pct -= fee_pct

                trades.append({'pnl': pnl_pct})
                equity *= (1 + pnl_pct / 100)
                position = None

    # 5. 결과 계산
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)

    if len(trades) == 0:
        print("\n[ERROR] No trades executed")
        print("\n원인 분석:")
        print("  - 47일 데이터는 W/M 패턴 형성에 부족할 수 있음")
        print("  - 필터를 더 완화하거나 더 긴 데이터(6개월~1년) 필요")
        return

    # utils.metrics 사용 (SSOT)
    metrics = calculate_backtest_metrics(trades, leverage=params['leverage'])

    print(f"\n[Trade Statistics]")
    print(f"  Total Trades: {len(trades):,}")
    print(f"  Win Rate: {metrics['win_rate']:.2f}%")
    print(f"  Winning Trades: {metrics['winning_trades']}")
    print(f"  Losing Trades: {metrics['losing_trades']}")

    print(f"\n[Returns]")
    print(f"  Total Return: {metrics['total_pnl']:.2f}%")
    print(f"  Final Capital: ${equity:.2f}")
    print(f"  Profit/Loss: ${equity - capital:.2f}")

    print(f"\n[Risk Metrics]")
    print(f"  Max Drawdown: {metrics['mdd']:.2f}%")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Sortino Ratio: {metrics['sortino_ratio']:.2f}")
    print(f"  Calmar Ratio: {metrics['calmar_ratio']:.2f}")

    # 6. 프리셋 저장
    preset_name = f"bybit_btc_alphax7_relaxed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    preset_data = {
        'name': preset_name,
        'exchange': 'bybit',
        'symbol': 'BTCUSDT',
        'timeframe': '15m',
        'strategy': 'AlphaX7 (MACD + ADX + W/M Pattern)',
        'params': params,
        'results': {
            'trades': len(trades),
            'win_rate': metrics['win_rate'],
            'total_return': metrics['total_pnl'],
            'max_drawdown': metrics['mdd'],
            'profit_factor': metrics['profit_factor'],
            'sharpe_ratio': metrics['sharpe_ratio'],
            'sortino_ratio': metrics['sortino_ratio'],
            'calmar_ratio': metrics['calmar_ratio'],
            'final_capital': equity
        },
        'filters': {
            'pattern_tolerance': params['pattern_tolerance'],
            'entry_validity_hours': params['entry_validity_hours'],
            'enable_adx_filter': params['enable_adx_filter'],
            'adx_threshold': params['adx_threshold']
        },
        'created_at': datetime.now().isoformat(),
        'data_period': {
            'start': str(df['timestamp'].min()),
            'end': str(df['timestamp'].max()),
            'candles': len(df)
        }
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
