#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v7.22 Coarse-to-Fine 최적화 실데이터 검증 스크립트

15분봉 Parquet → 자동 리샘플링 → Coarse-to-Fine 백테스트
"""

import sys
from pathlib import Path
import argparse
import time
from typing import Optional

# UTF-8 출력 강제 (Windows cp949 문제 해결)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Root 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import json
from datetime import datetime
from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core


def load_and_resample(
    exchange: str,
    symbol: str,
    target_tf: str = "1h"
) -> Optional[pd.DataFrame]:
    """
    15분봉 Parquet 로드 → 타겟 타임프레임으로 리샘플링

    Args:
        exchange: 거래소 (예: 'bybit')
        symbol: 심볼 (예: 'BTCUSDT')
        target_tf: 타겟 타임프레임 (예: '1h', '4h', '1d')

    Returns:
        리샘플링된 DataFrame (None이면 실패)
    """
    print(f"\n{'='*70}")
    print(f"데이터 로드 및 리샘플링")
    print(f"{'='*70}")

    try:
        # 1. BotDataManager 생성 (entry_tf='15m' 고정)
        dm = BotDataManager(exchange, symbol, {'entry_tf': '15m'})

        # 2. 15분봉 로드
        print(f"📂 15분봉 로드 중... ({exchange}_{symbol.lower()}_15m.parquet)")
        df_15m = dm.get_full_history(with_indicators=False)

        if df_15m is None or df_15m.empty:
            print(f"❌ 15분봉 데이터 없음")
            return None

        print(f"✓ 15분봉 로드 완료: {len(df_15m):,}개 캔들")

        # timestamp 컬럼 확인 및 변환
        if 'timestamp' not in df_15m.columns:
            print(f"❌ timestamp 컬럼 없음. 컬럼 목록: {list(df_15m.columns)}")
            return None

        # timestamp를 datetime으로 변환 (밀리초 Unix 타임스탬프 가능성)
        if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
            df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
        else:
            df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

        # 기간 정보 출력
        first_time = df_15m['timestamp'].iloc[0]
        last_time = df_15m['timestamp'].iloc[-1]
        duration = (last_time - first_time).days

        print(f"  기간: {first_time} ~ {last_time}")
        print(f"  일수: {duration}일")

        # 3. 리샘플링
        if target_tf == '15m':
            print(f"✓ 타겟이 15m이므로 리샘플링 스킵")
            return df_15m

        print(f"\n🔄 리샘플링 중... (15m → {target_tf})")
        from utils.data_utils import resample_data
        df_target = resample_data(df_15m, target_tf, add_indicators=False)

        if df_target is None or df_target.empty:
            print(f"❌ 리샘플링 실패")
            return None

        print(f"✓ 리샘플링 완료: {len(df_target):,}개 캔들")
        print(f"  압축률: {len(df_15m) / len(df_target):.1f}x")

        return df_target

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_preset(
    best_result,
    exchange: str,
    symbol: str,
    timeframe: str,
    strategy_type: str,
    coarse_time: float,
    fine_time: float,
    df: Optional[pd.DataFrame] = None
) -> Path:
    """
    Coarse-to-Fine 결과를 프리셋으로 저장

    Args:
        best_result: 최고 백테스트 결과
        exchange: 거래소
        symbol: 심볼
        timeframe: 타임프레임
        strategy_type: 전략 타입
        coarse_time: Coarse 실행 시간
        fine_time: Fine 실행 시간

    Returns:
        저장된 프리셋 파일 경로
    """
    # 프리셋 디렉토리
    preset_dir = Path(__file__).parent.parent / 'presets' / 'coarse_fine'
    preset_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 (타임스탬프 포함)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{exchange}_{symbol}_{timeframe}_{strategy_type}_{timestamp}.json"
    filepath = preset_dir / filename

    # 데이터 범위 정보 추출
    data_info = {}
    if df is not None and len(df) > 0:
        if 'timestamp' in df.columns:
            first_time = df['timestamp'].iloc[0]
            last_time = df['timestamp'].iloc[-1]
            data_info = {
                'total_candles': len(df),
                'start_date': str(first_time),
                'end_date': str(last_time),
                'period_days': (pd.to_datetime(last_time) - pd.to_datetime(first_time)).days
            }

    # 프리셋 데이터
    preset_data = {
        'meta_info': {
            'exchange': exchange,
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy_type': strategy_type,
            'optimization_method': 'coarse_to_fine',
            'created_at': datetime.now().isoformat(),
            'coarse_time_seconds': round(coarse_time, 2),
            'fine_time_seconds': round(fine_time, 2),
            'total_time_seconds': round(coarse_time + fine_time, 2),
            **data_info  # 데이터 범위 정보 병합
        },
        'best_params': {
            'atr_mult': best_result.params.get('atr_mult'),
            'filter_tf': best_result.params.get('filter_tf'),
            'trail_start_r': best_result.params.get('trail_start_r'),
            'trail_dist_r': best_result.params.get('trail_dist_r'),
            'entry_validity_hours': best_result.params.get('entry_validity_hours'),
            'leverage': best_result.params.get('leverage', 1),
            # MACD 파라미터 (None이면 기본값 사용)
            'macd_fast': best_result.params.get('macd_fast', 6 if strategy_type == 'macd' else None),
            'macd_slow': best_result.params.get('macd_slow', 18 if strategy_type == 'macd' else None),
            'macd_signal': best_result.params.get('macd_signal', 7 if strategy_type == 'macd' else None),
            'slippage': best_result.params.get('slippage'),
            'fee': best_result.params.get('fee')
        },
        'best_metrics': {
            'win_rate': round(best_result.win_rate, 2),
            'mdd': round(best_result.max_drawdown, 2),
            'sharpe_ratio': round(best_result.sharpe_ratio, 2),
            'profit_factor': round(best_result.profit_factor, 2),
            'total_trades': best_result.trades,
            'total_pnl': round(best_result.total_return, 2)
        }
    }

    # JSON 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(preset_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"✅ 프리셋 저장 완료")
    print(f"{'='*70}")
    print(f"📁 경로: {filepath}")
    print(f"\n📊 저장된 파라미터:")
    for k, v in preset_data['best_params'].items():
        if v is not None:
            print(f"  {k}: {v}")
    print(f"\n📈 저장된 성능:")
    for k, v in preset_data['best_metrics'].items():
        print(f"  {k}: {v}")

    return filepath


def run_coarse_to_fine_backtest(
    df: pd.DataFrame,
    exchange: str,
    symbol: str,
    trend_tf: str = "1h",
    metric: str = "sharpe_ratio",
    strategy_type: str = "macd"
):
    """
    Coarse-to-Fine 최적화 실행 및 프리셋 저장

    Args:
        df: 백테스트 데이터
        exchange: 거래소
        symbol: 심볼
        trend_tf: 추세 타임프레임
        metric: 최적화 메트릭
        strategy_type: 전략 타입 ('macd' or 'adx')
    """
    print(f"\n{'='*70}")
    print(f"Coarse-to-Fine 최적화 실행")
    print(f"{'='*70}")
    print(f"전략 타입: {strategy_type.upper()}")
    print(f"메트릭: {metric}")
    print(f"추세 TF: {trend_tf}")

    # BacktestOptimizer 생성 (v7.23: exchange 파라미터 추가)
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type=strategy_type,
        exchange=exchange  # 거래소별 최적화
    )

    # Phase 1: Coarse Grid
    print(f"\n{'─'*70}")
    print(f"Phase 1: Coarse Grid (넓은 범위 탐색)")
    print(f"{'─'*70}")

    start_time = time.time()
    coarse_results = optimizer.run_coarse_grid_optimization(
        df=df,
        trend_tf=trend_tf,
        metric=metric
    )
    coarse_time = time.time() - start_time

    if not coarse_results:
        print(f"❌ Coarse Grid 실패")
        return

    print(f"✓ Coarse Grid 완료")
    print(f"  조합 수: {len(coarse_results):,}개")
    print(f"  실행 시간: {coarse_time:.1f}초")
    print(f"  최고 점수: {coarse_results[0].sharpe_ratio:.2f}")

    # Phase 2: Fine Grid
    print(f"\n{'─'*70}")
    print(f"Phase 2: Fine Grid (정밀 탐색)")
    print(f"{'─'*70}")

    start_time = time.time()
    fine_results = optimizer.run_fine_grid_optimization(
        df=df,
        trend_tf=trend_tf,
        coarse_results=coarse_results,
        top_n=20,
        metric=metric
    )
    fine_time = time.time() - start_time

    if not fine_results:
        print(f"❌ Fine Grid 실패")
        return

    print(f"✓ Fine Grid 완료")
    print(f"  조합 수: {len(fine_results):,}개")
    print(f"  실행 시간: {fine_time:.1f}초")
    print(f"  최고 점수: {fine_results[0].sharpe_ratio:.2f}")

    # 결과 분석
    print(f"\n{'='*70}")
    print(f"최종 결과")
    print(f"{'='*70}")

    best = fine_results[0]
    print(f"\n📊 최적 파라미터:")
    for k, v in best.params.items():
        print(f"  {k}: {v}")

    print(f"\n📈 성능 지표:")
    print(f"  승률: {best.win_rate:.1f}%")
    print(f"  MDD: {best.max_drawdown:.2f}%")
    print(f"  Sharpe Ratio: {best.sharpe_ratio:.2f}")
    print(f"  Profit Factor: {best.profit_factor:.2f}")
    print(f"  총 거래: {best.trades}회")

    if best.backtest_duration_days > 0:
        print(f"  거래 기간: {best.backtest_duration_days}일")
    elif best.backtest_start_time and best.backtest_end_time:
        duration = (best.backtest_end_time - best.backtest_start_time).days
        print(f"  거래 기간: {duration}일")

    print(f"\n⏱️  실행 시간:")
    print(f"  Coarse: {coarse_time:.1f}초")
    print(f"  Fine: {fine_time:.1f}초")
    print(f"  총 시간: {coarse_time + fine_time:.1f}초")

    # 개선율 계산
    improvement = (fine_results[0].sharpe_ratio - coarse_results[0].sharpe_ratio) / coarse_results[0].sharpe_ratio * 100
    print(f"\n📈 Phase 간 개선율: {improvement:+.2f}%")

    # 프리셋 저장
    preset_path = save_preset(
        best_result=best,
        exchange=exchange,
        symbol=symbol,
        timeframe=trend_tf,
        strategy_type=strategy_type,
        coarse_time=coarse_time,
        fine_time=fine_time,
        df=df  # 데이터 범위 정보 전달
    )

    return preset_path


def main():
    parser = argparse.ArgumentParser(description="v7.22 Coarse-to-Fine 실데이터 검증")
    parser.add_argument('--exchange', default='bybit', help='거래소 (기본값: bybit)')
    parser.add_argument('--symbol', default='BTCUSDT', help='심볼 (기본값: BTCUSDT)')
    parser.add_argument('--timeframe', default='1h', help='타겟 타임프레임 (기본값: 1h)')
    parser.add_argument('--metric', default='sharpe_ratio', help='최적화 메트릭 (기본값: sharpe_ratio)')
    parser.add_argument('--strategy', default='macd', choices=['macd', 'adx'],
                        help='전략 타입 (기본값: macd, 선택: macd/adx)')

    args = parser.parse_args()

    print(f"{'='*70}")
    print(f"v7.22 Coarse-to-Fine 최적화 실데이터 검증")
    print(f"{'='*70}")
    print(f"거래소: {args.exchange}")
    print(f"심볼: {args.symbol}")
    print(f"타임프레임: {args.timeframe}")
    print(f"전략 타입: {args.strategy.upper()}")
    print(f"메트릭: {args.metric}")

    # 1. 데이터 로드 및 리샘플링
    df = load_and_resample(args.exchange, args.symbol, args.timeframe)

    if df is None:
        print(f"\n❌ 데이터 로드 실패. 종료합니다.")
        return 1

    # 2. Coarse-to-Fine 백테스트 실행
    preset_path = run_coarse_to_fine_backtest(
        df=df,
        exchange=args.exchange,
        symbol=args.symbol,
        trend_tf=args.timeframe,
        metric=args.metric,
        strategy_type=args.strategy
    )

    print(f"\n{'='*70}")
    print(f"✅ 검증 완료!")
    print(f"{'='*70}")

    if preset_path:
        print(f"\n💾 프리셋 파일: {preset_path}")
        print(f"\n다음 명령어로 검증하세요:")
        print(f"python tools/verify_preset_backtest.py --preset {preset_path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
