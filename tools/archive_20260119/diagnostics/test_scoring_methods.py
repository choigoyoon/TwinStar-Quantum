#!/usr/bin/env python3
"""점수 공식 비교 테스트

Fine-Tuning 결과를 5가지 점수 공식으로 재정렬하여 비교

Author: Claude Sonnet 4.5
Date: 2026-01-19
"""

import json
from pathlib import Path


def load_results(filepath: str) -> list:
    """Fine-Tuning 결과 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # top_15를 전체 결과로 사용
    results = []
    for item in data.get('top_15', []):
        results.append({
            'rank': item['rank'],
            'sharpe': item['sharpe'],
            'win_rate': item['win_rate'],
            'mdd': item['mdd'],
            'pnl': item['pnl'],
            'trades': item['trades'],
            'pf': item['pf'],
            'avg_pnl': item['pnl'] / item['trades'] if item['trades'] > 0 else 0,
            'params': item['params']
        })

    return results


def score_method_1(r: dict) -> float:
    """방법 1: Sharpe 중심 (현재 Adaptive 방식)

    Sharpe만 보되 MDD 페널티 적용
    """
    return r['sharpe'] * (5.0 / max(r['mdd'], 5.0))


def score_method_2(r: dict) -> float:
    """방법 2: 4가지 균형 (Sharpe, avg_pnl, MDD, 거래수)

    각 25%씩 동등한 가중치
    """
    sharpe_norm = r['sharpe'] / 30.0  # 정규화 (최대 30 가정)
    avg_pnl_norm = r['avg_pnl'] / 0.5  # 정규화 (최대 0.5% 가정)
    mdd_score = 10.0 / max(r['mdd'], 1.0)  # MDD 역수
    mdd_norm = min(mdd_score / 10.0, 1.0)  # 정규화 (10배 이상이면 만점)
    trades_norm = min(r['trades'] / 2000.0, 1.0)  # 2000개 이상이면 만점

    return (sharpe_norm * 0.25 +
            avg_pnl_norm * 0.25 +
            mdd_norm * 0.25 +
            trades_norm * 0.25)


def score_method_3(r: dict) -> float:
    """방법 3: avg_pnl 중심 (전략 효율성 우선)

    거래당 평균 40%, Sharpe 30%, MDD 20%, 거래수 10%
    """
    sharpe_norm = r['sharpe'] / 30.0
    avg_pnl_norm = r['avg_pnl'] / 0.5
    mdd_score = 10.0 / max(r['mdd'], 1.0)
    mdd_norm = min(mdd_score / 10.0, 1.0)
    trades_norm = min(r['trades'] / 2000.0, 1.0)

    return (sharpe_norm * 0.30 +
            avg_pnl_norm * 0.40 +
            mdd_norm * 0.20 +
            trades_norm * 0.10)


def score_method_4(r: dict) -> float:
    """방법 4: MDD 안전성 우선

    MDD 40%, Sharpe 30%, avg_pnl 20%, 거래수 10%
    """
    sharpe_norm = r['sharpe'] / 30.0
    avg_pnl_norm = r['avg_pnl'] / 0.5
    mdd_score = 10.0 / max(r['mdd'], 1.0)
    mdd_norm = min(mdd_score / 10.0, 1.0)
    trades_norm = min(r['trades'] / 2000.0, 1.0)

    return (sharpe_norm * 0.30 +
            avg_pnl_norm * 0.20 +
            mdd_norm * 0.40 +
            trades_norm * 0.10)


def score_method_5(r: dict) -> float:
    """방법 5: 거래수 중심 (충분한 샘플 우선)

    거래수 30%, Sharpe 30%, avg_pnl 25%, MDD 15%
    """
    sharpe_norm = r['sharpe'] / 30.0
    avg_pnl_norm = r['avg_pnl'] / 0.5
    mdd_score = 10.0 / max(r['mdd'], 1.0)
    mdd_norm = min(mdd_score / 10.0, 1.0)
    trades_norm = min(r['trades'] / 2000.0, 1.0)

    return (sharpe_norm * 0.30 +
            avg_pnl_norm * 0.25 +
            mdd_norm * 0.15 +
            trades_norm * 0.30)


def print_top_5(method_name: str, results: list, score_func):
    """상위 5개 출력"""
    scored = [(r, score_func(r)) for r in results]
    scored.sort(key=lambda x: x[1], reverse=True)

    print(f"\n{'='*100}")
    print(f"{method_name}")
    print(f"{'='*100}")
    print(f"{'순위':>4} {'원순위':>6} {'점수':>8} {'Sharpe':>8} {'승률':>8} {'MDD':>8} "
          f"{'수익':>10} {'거래':>6} {'거래당':>8} 파라미터")
    print("-" * 100)

    for rank, (r, score) in enumerate(scored[:5], 1):
        params_str = f"atr={r['params']['atr_mult']}, filter={r['params']['filter_tf']}, " \
                     f"ts={r['params']['trail_start_r']}, td={r['params']['trail_dist_r']}"

        print(f"{rank:>4} {r['rank']:>6} {score:>8.3f} {r['sharpe']:>8.2f} {r['win_rate']:>7.1f}% "
              f"{r['mdd']:>7.1f}% {r['pnl']:>9.1f}% {int(r['trades']):>6} {r['avg_pnl']:>7.2f}% {params_str}")

    return scored[0][0]  # 1등 반환


def main():
    """메인 함수"""
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 100)
    print("점수 공식 비교 테스트")
    print("=" * 100)

    # 결과 로드
    filepath = "reports/fine_tuning/fine_tuning_quick_20260118_203834.json"
    results = load_results(filepath)

    print(f"\n✅ 데이터 로드: {len(results)}개 결과")
    print(f"원본 1등: Sharpe={results[0]['sharpe']:.2f}, MDD={results[0]['mdd']:.1f}%, "
          f"avg_pnl={results[0]['avg_pnl']:.2f}%, trades={int(results[0]['trades'])}")

    # 각 방법으로 정렬
    methods = [
        ("방법 1: Sharpe 중심 (현재)", score_method_1),
        ("방법 2: 4가지 균형 (25% 동등)", score_method_2),
        ("방법 3: avg_pnl 중심 (효율성 40%)", score_method_3),
        ("방법 4: MDD 안전성 우선 (40%)", score_method_4),
        ("방법 5: 거래수 중심 (샘플 30%)", score_method_5)
    ]

    winners = []
    for method_name, score_func in methods:
        winner = print_top_5(method_name, results, score_func)
        winners.append((method_name, winner))

    # 비교 요약
    print(f"\n{'='*100}")
    print("1등 비교 요약")
    print(f"{'='*100}")
    print(f"{'방법':<40} {'원순위':>6} {'Sharpe':>8} {'승률':>8} {'MDD':>8} {'수익':>10} {'거래당':>8}")
    print("-" * 100)

    for method_name, winner in winners:
        print(f"{method_name:<40} {winner['rank']:>6} {winner['sharpe']:>8.2f} "
              f"{winner['win_rate']:>7.1f}% {winner['mdd']:>7.1f}% {winner['pnl']:>9.1f}% "
              f"{winner['avg_pnl']:>7.2f}%")

    print(f"\n{'='*100}")
    print("권장: 여러 방법의 1등을 비교하여 가장 균형잡힌 공식 선택")
    print(f"{'='*100}")


if __name__ == '__main__':
    main()
