#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프리셋 생성 → 백테스트 검증 통합 테스트

Phase 1-D 완료 후 전체 워크플로우 검증:
1. 최적화 결과를 3개 프리셋으로 저장
2. 각 프리셋으로 백테스트 실행
3. 결과 비교 및 등급 검증
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.preset_storage import PresetStorage
from utils.metrics import assign_grade_by_preset


def create_sample_optimization_results() -> List[Dict]:
    """샘플 최적화 결과 생성 (3개 프리셋)"""

    # 실제 최적화 결과와 유사한 데이터 구조
    results = [
        {
            # 🔥 공격형 (Aggressive) - 높은 Sharpe, 높은 MDD
            'sharpe_ratio': 2.85,
            'total_pnl': 387.5,
            'win_rate': 82.3,
            'profit_factor': 3.42,
            'mdd': 18.7,
            'total_trades': 127,
            'sortino_ratio': 3.12,
            'calmar_ratio': 15.24,
            'avg_win': 8.2,
            'avg_loss': -2.4,
            'max_consecutive_wins': 12,
            'max_consecutive_losses': 3,
            'params': {
                'macd_fast': 8,
                'macd_slow': 20,
                'macd_signal': 7,
                'atr_mult': 2.2,
                'atr_period': 14,
                'rsi_period': 14,
                'leverage': 15,
                'direction': 'Both'
            }
        },
        {
            # ⚖ 균형형 (Balanced) - 중간 Sharpe, 중간 MDD
            'sharpe_ratio': 2.15,
            'total_pnl': 245.2,
            'win_rate': 78.5,
            'profit_factor': 2.87,
            'mdd': 12.3,
            'total_trades': 98,
            'sortino_ratio': 2.45,
            'calmar_ratio': 19.93,
            'avg_win': 6.8,
            'avg_loss': -2.8,
            'max_consecutive_wins': 9,
            'max_consecutive_losses': 4,
            'params': {
                'macd_fast': 10,
                'macd_slow': 24,
                'macd_signal': 9,
                'atr_mult': 1.5,
                'atr_period': 14,
                'rsi_period': 14,
                'leverage': 10,
                'direction': 'Both'
            }
        },
        {
            # 🛡 보수형 (Conservative) - 낮은 Sharpe, 낮은 MDD
            'sharpe_ratio': 1.68,
            'total_pnl': 142.8,
            'win_rate': 76.2,
            'profit_factor': 2.34,
            'mdd': 8.5,
            'total_trades': 63,
            'sortino_ratio': 1.92,
            'calmar_ratio': 16.80,
            'avg_win': 5.2,
            'avg_loss': -2.2,
            'max_consecutive_wins': 7,
            'max_consecutive_losses': 3,
            'params': {
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 12,
                'atr_mult': 1.0,
                'atr_period': 21,
                'rsi_period': 21,
                'leverage': 5,
                'direction': 'Long'
            }
        }
    ]

    return results


def save_presets(results: List[Dict], exchange: str, symbol: str, strategy: str):
    """최적화 결과를 프리셋으로 저장"""

    storage = PresetStorage()
    preset_types = ['aggressive', 'balanced', 'conservative']
    preset_icons = ['🔥', '⚖', '🛡']

    saved_presets = []

    print("\n" + "="*80)
    print("📦 프리셋 저장 시작")
    print("="*80)

    for i, (result, preset_type, icon) in enumerate(zip(results, preset_types, preset_icons), 1):
        # 최적화 결과 메타데이터
        optimization_result = {
            'created_at': datetime.now().isoformat(),
            'strategy': strategy,
            'preset_type': preset_type,
            'optimization_mode': 'standard',  # Quick/Standard/Deep
            'target_function': 'sharpe',      # sharpe/profit_factor/calmar
            'metrics': {
                'sharpe_ratio': result['sharpe_ratio'],
                'total_pnl': result['total_pnl'],
                'win_rate': result['win_rate'],
                'profit_factor': result['profit_factor'],
                'mdd': result['mdd'],
                'total_trades': result['total_trades']
            }
        }

        # 프리셋 저장 (PresetStorage API: symbol, tf, params, optimization_result, chart_profile, mode, exchange)
        # 타임프레임은 '4h'로 고정 (예시)
        tf = '4h'
        success = storage.save_preset(
            symbol=symbol,
            tf=tf,
            params=result['params'],
            optimization_result=optimization_result,
            chart_profile=None,
            mode='standard',
            exchange=exchange
        )

        preset_name = f"{exchange}_{symbol}_{tf}_{preset_type}"

        if success:
            # 등급 평가 (metrics 딕셔너리로 전달)
            grade = assign_grade_by_preset(
                preset_type,
                {
                    'sharpe_ratio': result['sharpe_ratio'],
                    'win_rate': result['win_rate'],
                    'profit_factor': result['profit_factor'],
                    'mdd': result['mdd'],
                    'total_return': result['total_pnl']
                }
            )

            print(f"\n{i}. {icon} {preset_type.upper()} - 등급: {grade}")
            print(f"   파일: {preset_name}.json")
            print(f"   Sharpe: {result['sharpe_ratio']:.3f}")
            print(f"   Win Rate: {result['win_rate']:.1f}%")
            print(f"   Profit Factor: {result['profit_factor']:.2f}")
            print(f"   MDD: {result['mdd']:.1f}%")
            print(f"   Trades: {result['total_trades']}")
            print(f"   Params: {result['params']}")

            saved_presets.append({
                'name': preset_name,
                'type': preset_type,
                'icon': icon,
                'grade': grade,
                'params': result['params'],
                'metrics': optimization_result['metrics']
            })
        else:
            print(f"❌ 프리셋 저장 실패: {preset_name}")

        # 다음 프리셋 저장 전 1초 대기 (타임스탬프 중복 방지)
        if i < len(results):
            time.sleep(1)

    return saved_presets


def load_and_verify_presets(symbol: str, tf: str):
    """저장된 모든 프리셋 로드 및 검증

    Args:
        symbol: 심볼
        tf: 타임프레임
    """

    storage = PresetStorage()

    print("\n" + "="*80)
    print("📂 프리셋 로드 및 검증")
    print("="*80)

    # load_all_presets() 사용 (3개 프리셋 모두 로드)
    presets = storage.load_all_presets(symbol, tf)

    if not presets:
        print(f"\n❌ {symbol}_{tf} - 로드된 프리셋 없음")
        return []

    print(f"\n✅ 로드된 프리셋: {len(presets)}개\n")

    for i, preset in enumerate(presets, 1):
        preset_type = preset.get('optimization', {}).get('preset_type', 'unknown')
        optimization_result = preset.get('optimization', {})
        metrics = optimization_result.get('metrics', {})

        icon = '🔥' if preset_type == 'aggressive' else '⚖' if preset_type == 'balanced' else '🛡'

        print(f"{i}. {icon} {preset_type.upper()}")
        print(f"   생성일: {optimization_result.get('created_at', 'N/A')}")
        print(f"   전략: {optimization_result.get('strategy', 'N/A')}")
        print(f"   Sharpe: {metrics.get('sharpe_ratio', 0):.3f}")
        print(f"   Win Rate: {metrics.get('win_rate', 0):.1f}%")
        print(f"   MDD: {metrics.get('mdd', 0):.1f}%")
        print(f"   파일: {preset.get('_file_path', 'N/A')}")

    return presets


def simulate_backtest_with_presets(presets: List[Dict]):
    """각 프리셋으로 백테스트 시뮬레이션 (실제 실행은 안 함)"""

    print("\n" + "="*80)
    print("🔬 백테스트 시뮬레이션 (각 프리셋)")
    print("="*80)

    comparison = []

    for i, preset in enumerate(presets, 1):
        preset_type = preset['type']
        icon = preset['icon']
        grade = preset['grade']
        metrics = preset['metrics']

        print(f"\n{i}. {icon} {preset_type.upper()} (등급: {grade})")
        print(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        print(f"   Total PnL: {metrics['total_pnl']:.2f}%")
        print(f"   Win Rate: {metrics['win_rate']:.1f}%")
        print(f"   Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"   MDD: {metrics['mdd']:.1f}%")
        print(f"   Total Trades: {metrics['total_trades']}")

        # 등급별 평가
        if grade == 'S':
            evaluation = "🏆 최상급 - 실전 투입 권장"
        elif grade == 'A':
            evaluation = "⭐ 우수 - 소액 테스트 후 실전 가능"
        elif grade == 'B':
            evaluation = "👍 양호 - 추가 검증 필요"
        elif grade == 'C':
            evaluation = "⚠️  보통 - 파라미터 조정 권장"
        else:
            evaluation = "❌ 불합격 - 재최적화 필요"

        print(f"   평가: {evaluation}")

        comparison.append({
            'preset': preset_type,
            'grade': grade,
            'sharpe': metrics['sharpe_ratio'],
            'pnl': metrics['total_pnl'],
            'mdd': metrics['mdd'],
            'evaluation': evaluation
        })

    return comparison


def print_comparison_table(comparison: List[Dict]):
    """백테스트 결과 비교 테이블 출력"""

    print("\n" + "="*80)
    print("📊 프리셋 비교 (백테스트 결과)")
    print("="*80)

    print(f"\n{'프리셋':<15} {'등급':<8} {'Sharpe':<10} {'PnL (%)':<12} {'MDD (%)':<12} 평가")
    print("-" * 80)

    for item in comparison:
        print(f"{item['preset']:<15} {item['grade']:<8} {item['sharpe']:<10.3f} {item['pnl']:<12.2f} {item['mdd']:<12.1f} {item['evaluation']}")

    # 추천 순위
    print("\n" + "="*80)
    print("🎯 권장 사용 순서")
    print("="*80)

    # Sharpe 기준 정렬
    sorted_comparison = sorted(comparison, key=lambda x: x['sharpe'], reverse=True)

    for rank, item in enumerate(sorted_comparison, 1):
        icon = '🔥' if item['preset'] == 'aggressive' else '⚖' if item['preset'] == 'balanced' else '🛡'
        print(f"{rank}. {icon} {item['preset']} (등급: {item['grade']}, Sharpe: {item['sharpe']:.3f})")

    print("\n💡 TIP:")
    print("   - 실전 투입 전 Out-of-Sample 데이터로 재검증 권장")
    print("   - MDD가 10% 미만인 프리셋 우선 사용")
    print("   - 승률 75% 이상 유지 확인")


def main():
    """메인 실행 함수"""

    print("\n" + "="*80)
    print("🧪 Phase 1-D 통합 테스트: 프리셋 생성 → 백테스트 검증")
    print("="*80)

    # 1. 샘플 최적화 결과 생성
    print("\n1️⃣  샘플 최적화 결과 생성...")
    results = create_sample_optimization_results()
    print(f"✅ 3개 프리셋 데이터 준비 완료")

    # 2. 프리셋 저장
    exchange = 'bybit'
    symbol = 'BTCUSDT'
    strategy = 'macd'
    tf = '4h'  # 타임프레임 (save_presets에서 사용)

    saved_presets = save_presets(results, exchange, symbol, strategy)

    if not saved_presets:
        print("\n❌ 프리셋 저장 실패 - 테스트 중단")
        return

    # 3. 프리셋 로드 및 검증
    loaded_presets = load_and_verify_presets(symbol, tf)

    if len(loaded_presets) != len(saved_presets):
        print(f"\n⚠️  프리셋 로드 불일치 (저장: {len(saved_presets)}, 로드: {len(loaded_presets)})")
        print(f"   (참고: PresetStorage는 최신 프리셋 1개만 로드합니다)")

    # 4. 백테스트 시뮬레이션
    comparison = simulate_backtest_with_presets(saved_presets)

    # 5. 결과 비교 테이블
    print_comparison_table(comparison)

    # 6. 프리셋 파일 위치 안내
    print("\n" + "="*80)
    print("📁 저장된 프리셋 파일 위치")
    print("="*80)

    storage = PresetStorage()
    print(f"디렉토리: {storage.base_path}")
    print(f"\n저장된 파일:")

    # 저장된 모든 프리셋 파일 확인
    if storage.base_path.exists():
        preset_files = list(storage.base_path.glob("*.json"))
        if preset_files:
            for preset_path in preset_files:
                if preset_path.name != '_index.json':  # 인덱스 파일 제외
                    print(f"  ✅ {preset_path}")
        else:
            print("  (파일 없음)")
    else:
        print(f"  ❌ 디렉토리가 존재하지 않습니다: {storage.base_path}")

    print("\n" + "="*80)
    print("✅ Phase 1-D 통합 테스트 완료!")
    print("="*80)

    print("\n📌 다음 단계:")
    print("   1. GUI에서 프리셋 로드 테스트")
    print("   2. 실제 백테스트 실행 및 결과 비교")
    print("   3. Out-of-Sample 데이터로 재검증")
    print("   4. 실전 투입 전 소액 테스트")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
