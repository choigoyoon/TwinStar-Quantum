"""
실제 GUI 워크플로우 재현 테스트
프리셋 생성 → 저장 → 로드 → 백테스트
"""

import sys
import os
from pathlib import Path

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import Optional, Dict, Any

# Core modules
from core.optimization_logic import OptimizationEngine
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.preset_storage import PresetStorage
from utils.metrics import calculate_backtest_metrics, format_metrics_report


def print_section(title: str):
    """섹션 구분선 출력"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def step1_optimize_and_save_preset(exchange: str = 'bybit',
                                   symbol: str = 'BTCUSDT',
                                   entry_tf: str = '15m') -> Optional[Dict[str, Any]]:
    """
    Step 1: 최적화 실행 및 프리셋 저장 (GUI 동작 재현)

    GUI 경로: 최적화 탭 → '순차 최적화' 버튼 클릭 → '적용' 버튼 클릭
    """
    print_section("Step 1: 최적화 실행 및 프리셋 저장")

    # 1-1. 데이터 로드
    print(f"📊 데이터 로드 중... ({exchange} {symbol} {entry_tf})")
    dm = BotDataManager(exchange, symbol)

    if not dm.load_historical():
        print("❌ 데이터 로드 실패")
        return None

    df_entry_full = dm.df_entry_full
    df_pattern_full = dm.df_pattern_full

    if df_entry_full is None or df_entry_full.empty:
        print("❌ 빈 데이터프레임 (entry)")
        return None

    if df_pattern_full is None or df_pattern_full.empty:
        print("❌ 빈 데이터프레임 (pattern)")
        return None

    print(f"✅ 데이터 로드 완료:")
    print(f"   Entry: {len(df_entry_full)} 행")
    print(f"   Pattern: {len(df_pattern_full)} 행")

    # 1-2. 순차 최적화 실행 (GUI의 _run_staged_optimization 재현)
    print(f"\n🎯 순차 최적화 시작 (mode='standard')")

    engine = OptimizationEngine()

    def stage_callback(stage_num, message, params):
        print(f"   Stage {stage_num}: {message}")
        print(f"   Params: {params}")

    # 최적화는 entry 데이터만 사용
    result = engine.run_staged_optimization(
        df=df_entry_full,
        target_mdd=20.0,
        max_workers=4,
        stage_callback=stage_callback,
        mode='standard',  # quick/standard/deep
        capital_mode='compound'
    )

    if not result or not result.get('candidates'):
        print("❌ 최적화 결과 없음")
        return None

    # 1-3. 최적 결과 선택 (1순위)
    best = result['candidates'][0]
    leverage = result.get('leverage', 1)

    print(f"\n✅ 최적화 완료!")
    print(f"   총 조합: {result.get('total_combinations', 0)}")
    print(f"   최적 레버리지: {leverage}x")
    print(f"   승률: {best.win_rate:.1f}%")
    print(f"   수익률: {best.simple_return:+.1f}%")
    print(f"   MDD: {best.max_drawdown:.1f}%")
    print(f"   Sharpe: {best.sharpe_ratio:.2f}")

    # 1-4. 프리셋 데이터 구성 (GUI의 _apply_result 재현)
    params = best.params.copy()

    # 1-4-1. 실제 백테스트 실행 (검증용)
    print(f"\n🔍 최적 파라미터로 백테스트 검증 중...")

    core = AlphaX7Core()
    verification_trades = core.run_backtest(
        df_pattern=df_pattern_full,
        df_entry=df_entry_full,
        **params
    )

    if not verification_trades:
        print("❌ 검증 백테스트 실패")
        return None

    # 검증 메트릭 계산
    verification_metrics = calculate_backtest_metrics(verification_trades, leverage=leverage, capital=100.0)

    print(f"✅ 검증 백테스트 완료: {len(verification_trades)} 거래")
    print(f"   승률: {verification_metrics['win_rate']:.1f}%")
    print(f"   수익률: {verification_metrics['total_pnl']:+.1f}%")
    print(f"   MDD: {verification_metrics['mdd']:.1f}%")
    print(f"   Sharpe: {verification_metrics['sharpe_ratio']:.2f}")

    # 메타데이터는 실제 백테스트 결과 사용 (최적화 결과 아님!)
    result_info = {
        'win_rate': verification_metrics['win_rate'],
        'total_return': verification_metrics['total_pnl'],
        'max_drawdown': verification_metrics['mdd'],
        'sharpe_ratio': verification_metrics['sharpe_ratio'],
        'total_trades': verification_metrics['total_trades'],
        'profit_factor': verification_metrics['profit_factor']
    }

    # 1-5. PresetStorage를 사용하여 프리셋 저장
    print(f"\n💾 프리셋 저장 중...")

    storage = PresetStorage(exchange)
    filter_tf = params.get('filter_tf', '4h')

    # PresetType 자동 결정 (MDD 기준)
    # aggressive: MDD < 20%, balanced: MDD < 10%, conservative: MDD < 5%
    mdd = verification_metrics['mdd']
    if mdd < 5.0:
        preset_type = 'conservative'
    elif mdd < 10.0:
        preset_type = 'balanced'
    else:
        preset_type = 'aggressive'

    # PresetStorage.save_preset() API에 맞게 호출
    # save_preset(symbol, tf, params, optimization_result, chart_profile, mode, exchange)
    success = storage.save_preset(
        symbol=symbol,
        tf=filter_tf,
        params=params,
        optimization_result=result_info,
        chart_profile=None,
        mode=preset_type,  # mode 파라미터를 preset_type으로 사용
        exchange=None  # self.exchange 사용
    )

    if success:
        print(f"✅ 프리셋 저장 완료: {preset_type}")
        print(f"   경로: config/presets/{exchange.lower()}_{symbol}_{filter_tf}_*_{preset_type}.json")
    else:
        print(f"❌ 프리셋 저장 실패")
        return None

    return {
        'symbol': symbol,
        'filter_tf': filter_tf,
        'entry_tf': params.get('entry_tf', entry_tf),
        'preset_type': preset_type,
        'params': params,
        'leverage': leverage,
        'result_info': result_info
    }


def step2_load_preset(exchange: str, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    """
    Step 2: 저장된 프리셋 로드 (GUI 동작 재현)

    GUI 경로: 매매 탭 → 심볼/타임프레임 선택 → 자동 로드
    """
    print_section("Step 2: 프리셋 로드")

    storage = PresetStorage(exchange)

    print(f"📂 프리셋 로드 중... ({exchange} {symbol} {timeframe})")

    # 단일 프리셋 로드 (load_preset은 단일 딕셔너리 반환)
    preset_data = storage.load_preset(symbol, timeframe)

    if not preset_data:
        print("❌ 프리셋 없음")
        return None

    # 프리셋 정보 출력
    opt_result = preset_data.get('optimization', {})
    print(f"✅ 프리셋 발견:")
    print(f"   WinRate: {opt_result.get('win_rate', 0):.1f}% | "
          f"Return: {opt_result.get('total_return', 0):+.1f}%")

    return {
        'preset_type': 'loaded',
        'params': preset_data.get('params', {}),
        'leverage': 1,  # PresetStorage에는 leverage 필드 없음
        'metadata': opt_result
    }


def step3_backtest_with_preset(exchange: str,
                               symbol: str,
                               preset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Step 3: 프리셋으로 백테스트 실행 (GUI 동작 재현)

    GUI 경로: 백테스트 탭 → 프리셋 선택 → '실행' 버튼 클릭
    """
    print_section("Step 3: 백테스트 실행")

    params = preset['params']
    leverage = preset['leverage']

    print(f"🔍 백테스트 파라미터:")
    print(f"   Filter TF: {params.get('filter_tf', 'N/A')}")
    print(f"   Entry TF: {params.get('entry_tf', 'N/A')}")
    print(f"   Leverage: {leverage}x")
    print(f"   ATR Mult: {params.get('atr_mult', 'N/A')}")
    print(f"   Direction: {params.get('direction', 'Both')}")

    # 3-1. 데이터 로드
    print(f"\n📊 데이터 로드 중...")
    dm = BotDataManager(exchange, symbol)

    if not dm.load_historical():
        print("❌ 데이터 로드 실패")
        return None

    df_entry = dm.df_entry_full
    df_pattern = dm.df_pattern_full

    if df_entry is None or df_entry.empty:
        print("❌ 빈 데이터프레임 (entry)")
        return None

    if df_pattern is None or df_pattern.empty:
        print("❌ 빈 데이터프레임 (pattern)")
        return None

    print(f"✅ 데이터 로드 완료:")
    print(f"   Entry: {len(df_entry)} 행")
    print(f"   Pattern: {len(df_pattern)} 행")

    # 3-2. 백테스트 실행
    print(f"\n🚀 백테스트 시작...")

    core = AlphaX7Core()

    # run_backtest는 df_pattern, df_entry 순서로 받음
    trades = core.run_backtest(
        df_pattern=df_pattern,
        df_entry=df_entry,
        **params  # params 딕셔너리를 키워드 인수로 풀어서 전달
    )

    if not trades:
        print("❌ 거래 내역 없음")
        return None

    print(f"✅ 백테스트 완료: {len(trades)} 거래")

    # 3-3. 메트릭 계산
    metrics = calculate_backtest_metrics(trades, leverage=leverage, capital=100.0)

    print(f"\n📊 백테스트 결과:")
    print(format_metrics_report(metrics))

    # 3-4. 원본 프리셋과 비교
    original_meta = preset.get('metadata', {})

    print(f"\n🔄 프리셋 vs 백테스트 비교:")
    print(f"{'지표':<15} {'프리셋':<12} {'백테스트':<12} {'차이'}")
    print(f"{'-'*50}")

    comparisons = [
        ('Win Rate %', original_meta.get('win_rate', 0), metrics['win_rate']),
        ('Return %', original_meta.get('total_return', 0), metrics['total_pnl']),
        ('MDD %', original_meta.get('max_drawdown', 0), metrics['mdd']),
        ('Sharpe', original_meta.get('sharpe_ratio', 0), metrics['sharpe_ratio']),
        ('Trades', original_meta.get('total_trades', 0), metrics['total_trades'])
    ]

    for label, preset_val, backtest_val in comparisons:
        diff = backtest_val - preset_val
        diff_str = f"{diff:+.2f}"
        print(f"{label:<15} {preset_val:<12.2f} {backtest_val:<12.2f} {diff_str}")

    return {
        'trades': trades,
        'metrics': metrics,
        'params': params,
        'leverage': leverage
    }


def main():
    """메인 워크플로우 실행"""
    print("="*80)
    print("  TwinStar Quantum - 실제 GUI 워크플로우 재현 테스트")
    print("  프리셋 생성 → 저장 → 로드 → 백테스트")
    print("="*80)

    # 설정
    exchange = 'bybit'
    symbol = 'BTCUSDT'
    entry_tf = '15m'

    try:
        # Step 1: 최적화 및 프리셋 저장
        opt_result = step1_optimize_and_save_preset(exchange, symbol, entry_tf)
        if not opt_result:
            print("\n❌ Step 1 실패")
            return

        filter_tf = opt_result['filter_tf']

        # Step 2: 프리셋 로드
        preset = step2_load_preset(exchange, symbol, filter_tf)
        if not preset:
            print("\n❌ Step 2 실패")
            return

        # Step 3: 백테스트 실행
        backtest_result = step3_backtest_with_preset(exchange, symbol, preset)
        if not backtest_result:
            print("\n❌ Step 3 실패")
            return

        # 최종 요약
        print_section("✅ 전체 워크플로우 완료")
        print(f"Exchange: {exchange}")
        print(f"Symbol: {symbol}")
        print(f"Timeframe: {filter_tf} → {opt_result['entry_tf']}")
        print(f"Preset Type: {opt_result['preset_type']}")
        print(f"Leverage: {opt_result['leverage']}x")
        print(f"\n최종 백테스트 메트릭:")
        print(format_metrics_report(backtest_result['metrics']))

    except Exception as e:
        import traceback
        print(f"\n❌ 에러 발생: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    main()
