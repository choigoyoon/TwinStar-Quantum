"""단일 백테스트 디버그 (추출된 범위)

메타 최적화에서 추출한 최적 파라미터로 백테스트 1회 실행하여
문제 진단

Author: Claude Sonnet 4.5
Date: 2026-01-17
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG 레벨로 상세 로그
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# UTF-8 출력 설정 (Windows용)
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def main():
    """메인 함수"""
    print("=" * 80)
    print("단일 백테스트 디버그")
    print("=" * 80)
    print()

    # 1. 데이터 로드
    print("1. 데이터 로드 중...")
    from core.data_manager import BotDataManager

    dm = BotDataManager(
        exchange_name='bybit',
        symbol='BTCUSDT',
        strategy_params={'entry_tf': '15m'}
    )

    if not dm.load_historical():
        print("❌ 데이터 로드 실패")
        return

    df = dm.df_entry_full

    if df is None or df.empty:
        print("❌ 데이터가 비어있습니다")
        return

    print(f"✅ 데이터 로드 완료: {len(df):,}개 캔들")
    print(f"   기간: {df.index[0]} ~ {df.index[-1]}")
    print()

    # 2. 파라미터 설정 (메타 최적화 최고 결과)
    print("2. 파라미터 설정")
    params = {
        'trend_interval': '1h',
        'entry_tf': '15m',
        'leverage': 1,
        'direction': 'Both',
        'max_mdd': 20.0,
        'pattern_tolerance': 0.05,
        'pullback_rsi_long': 40,
        'pullback_rsi_short': 60,

        # 메타 최적화 최적 파라미터
        'atr_mult': 1.0,
        'filter_tf': '2h',
        'trail_start_r': 0.5,
        'trail_dist_r': 0.015,
        'entry_validity_hours': 12.0
    }

    for key, value in params.items():
        print(f"  {key}: {value}")
    print()

    # 3. 백테스트 실행
    print("3. 백테스트 실행 중...")
    print("-" * 80)

    from core.strategy_core import AlphaX7Core

    try:
        strategy = AlphaX7Core(use_mtf=True)

        # DataFrame 복사 (안전성)
        df_pattern = df.copy()
        df_entry = df.copy()

        print(f"  df_pattern: {len(df_pattern)}개 캔들")
        print(f"  df_entry: {len(df_entry)}개 캔들")
        print()

        # 백테스트 실행
        trades = strategy.run_backtest(
            df_pattern=df_pattern,
            df_entry=df_entry,
            slippage=0.0005,
            **{k: v for k, v in params.items() if k not in ['trend_interval', 'entry_tf', 'leverage', 'direction', 'max_mdd']}
        )

        print()
        print("-" * 80)

        if not trades:
            print("❌ 거래 내역이 없습니다")
            print("   원인: 신호 미발생 또는 전략 조건 불충족")
            return

        print(f"✅ 백테스트 완료: {len(trades)}개 거래")
        print()

        # 4. 메트릭 계산
        print("4. 메트릭 계산 중...")
        from utils.metrics import calculate_backtest_metrics

        metrics = calculate_backtest_metrics(
            trades=trades,
            leverage=params['leverage'],
            capital=100.0
        )

        print("✅ 메트릭 계산 완료")
        print()

        # 5. 결과 출력
        print("5. 백테스트 결과")
        print("=" * 80)
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
        print(f"  Win Rate: {metrics['win_rate']:.2f}%")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  MDD: {metrics['mdd']:.2f}%")
        print(f"  Total Return: {metrics['total_pnl']:.2f}%")
        print(f"  Total Trades: {metrics['total_trades']}")
        print()

        # 6. 거래 샘플 (처음 5개)
        print("6. 거래 샘플 (처음 5개)")
        print("-" * 80)
        for i, trade in enumerate(trades[:5], 1):
            print(f"  Trade {i}:")
            print(f"    Side: {trade.get('side', 'N/A')}")
            print(f"    Entry: {trade.get('entry_price', 0):.2f}")
            print(f"    Exit: {trade.get('exit_price', 0):.2f}")
            print(f"    PnL: {trade.get('pnl', 0):.2f}%")
            print()

        print("=" * 80)
        print("디버그 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"\n\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
