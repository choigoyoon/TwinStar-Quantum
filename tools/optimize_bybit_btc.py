"""
Bybit BTC/USDT 최적화 및 백테스트 스크립트
- 15분봉 Parquet 데이터 사용
- 최적화 → 백테스트 → 프리셋 저장
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime
import json

# Core modules
from core.optimizer import BacktestOptimizer
from config.parameters import DEFAULT_PARAMS
from utils.preset_storage import PresetStorage
from utils.logger import get_module_logger

logger = get_module_logger(__name__)

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("Bybit BTC/USDT 최적화 및 백테스트")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n[1/4] Parquet 데이터 로드 중...")
    parquet_path = project_root / "data" / "cache" / "bybit_btcusdt_15m.parquet"

    if not parquet_path.exists():
        print(f"❌ 에러: Parquet 파일을 찾을 수 없습니다: {parquet_path}")
        return

    df = pd.read_parquet(parquet_path)
    print(f"✅ 데이터 로드 완료")
    print(f"   - 총 캔들 수: {len(df):,}개")
    print(f"   - 기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    print(f"   - 컬럼: {list(df.columns)}")

    # 2. 최적화 실행
    print("\n[2/4] 파라미터 최적화 실행 중...")

    # BacktestOptimizer 사용 (core.optimizer)
    from core.strategy_core import AlphaX7Core
    optimizer = BacktestOptimizer(AlphaX7Core, df)

    # 최적화 파라미터 그리드 (빠른 테스트용)
    param_grid = {
        'rsi_period': [10, 14, 20],
        'rsi_low': [25, 30, 35],
        'rsi_high': [65, 70, 75],
        'atr_period': [10, 14, 20],
        'atr_multi': [1.5, 2.0, 2.5],
        'leverage': [5, 10, 15]
    }

    print(f"   - 탐색 공간: {np.prod([len(v) for v in param_grid.values()]):,}개 조합")

    try:
        # 최적화 실행 (상위 3개 결과)
        optimization_results = optimizer.run_optimization(
            df=df,
            grid=param_grid,
            max_workers=4,
            mode='standard'  # 'quick', 'standard', 'deep'
        )

        if not optimization_results or len(optimization_results) == 0:
            print("❌ 최적화 결과가 없습니다.")
            return

        print(f"✅ 최적화 완료: 상위 {len(optimization_results)}개 결과")

        # 최적 파라미터 선택 (1등)
        best_result = optimization_results[0]
        best_params = best_result.params

        print(f"\n[최적 파라미터 (1등)]")
        print(f"   - RSI Period: {best_params.get('rsi_period', 14)}")
        print(f"   - RSI Low: {best_params.get('rsi_low', 30)}")
        print(f"   - RSI High: {best_params.get('rsi_high', 70)}")
        print(f"   - ATR Period: {best_params.get('atr_period', 14)}")
        print(f"   - ATR Multi: {best_params.get('atr_multi', 2.0)}")
        print(f"   - Leverage: {best_params.get('leverage', 10)}")
        print(f"   - 승률: {best_result.win_rate:.2f}%")
        print(f"   - 총 수익률: {best_result.compound_return:.2f}%")
        print(f"   - Sharpe Ratio: {best_result.sharpe_ratio:.2f}")
        print(f"   - 총 거래 수: {best_result.trades}회")

        # 백테스트 결과를 best_result에서 직접 사용
        backtest_result = {
            'total_trades': best_result.trades,
            'win_rate': best_result.win_rate,
            'total_return': best_result.compound_return,
            'max_drawdown': best_result.max_drawdown,
            'profit_factor': best_result.profit_factor,
            'sharpe_ratio': best_result.sharpe_ratio,
            'final_capital': best_result.final_capital
        }

    except Exception as e:
        print(f"❌ 최적화 중 에러: {e}")
        import traceback
        traceback.print_exc()

        # 기본 파라미터 사용
        print("\n⚠️ 기본 파라미터로 대체합니다.")
        best_params = DEFAULT_PARAMS.copy()
        best_result = None
        backtest_result = None

    # 4. 프리셋 저장
    print("\n[4/4] 프리셋 저장 중...")

    preset_name = f"bybit_btc_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # PresetStorage.save_preset(symbol, tf, params, optimization_result, chart_profile, mode, exchange)
    optimization_result_dict = None
    if best_result:
        optimization_result_dict = {
            'win_rate': best_result.win_rate,
            'compound_return': best_result.compound_return,
            'max_drawdown': best_result.max_drawdown,
            'sharpe_ratio': best_result.sharpe_ratio,
            'profit_factor': best_result.profit_factor,
            'trades': best_result.trades,
            'final_capital': best_result.final_capital
        }

    try:
        storage = PresetStorage()
        storage.save_preset(
            symbol='BTCUSDT',
            tf='15m',
            params=best_params,
            optimization_result=optimization_result_dict,
            mode='standard',
            exchange='bybit'
        )
        print(f"✅ 프리셋 저장 완료: {preset_name}")

        # JSON 파일로도 저장 (백업)
        json_path = project_root / "data" / f"{preset_name}.json"
        backup_data = {
            'name': preset_name,
            'exchange': 'bybit',
            'symbol': 'BTCUSDT',
            'timeframe': '15m',
            'params': best_params,
            'optimization_result': optimization_result_dict if optimization_result_dict else {},
            'backtest_result': backtest_result if backtest_result else {},
            'created_at': datetime.now().isoformat(),
            'data_period': {
                'start': str(df['timestamp'].min()),
                'end': str(df['timestamp'].max()),
                'candles': len(df)
            }
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON 백업 저장: {json_path}")

    except Exception as e:
        print(f"❌ 프리셋 저장 중 에러: {e}")
        import traceback
        traceback.print_exc()

    # 결과 요약
    print("\n" + "=" * 80)
    print("작업 완료")
    print("=" * 80)
    print(f"\n[최종 요약]")
    print(f"✅ 데이터: {len(df):,}개 캔들 (Bybit BTC/USDT 15m)")
    print(f"✅ 최적화: 완료" if best_result else "⚠️ 최적화: 기본 파라미터 사용")
    print(f"✅ 백테스트: 완료" if backtest_result else "❌ 백테스트: 실패")
    print(f"✅ 프리셋: {preset_name}")

    if backtest_result:
        print(f"\n[핵심 지표]")
        print(f"   승률: {backtest_result.get('win_rate', 0):.2f}%")
        print(f"   수익률: {backtest_result.get('total_return', 0):.2f}%")
        print(f"   Sharpe: {backtest_result.get('sharpe_ratio', 0):.2f}")
        print(f"   MDD: {backtest_result.get('max_drawdown', 0):.2f}%")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
