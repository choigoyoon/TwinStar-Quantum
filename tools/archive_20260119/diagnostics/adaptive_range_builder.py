"""적응형 파라미터 범위 생성기 - v7.25

프리셋 백테스트 결과를 분석하여 파라미터 범위를 자동 조정

핵심 원리:
- 프리셋 메트릭(승률, MDD, 거래수) 분석
- 각 파라미터의 영향도 고려 (ATR→MDD/승률, 레버리지→수익/MDD, 필터→승률/거래수)
- 목표 지표(승률 85-90%, MDD 3-5%, 거래수 5000+)에 맞춰 범위 자동 조정

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

from typing import Dict, List


# 목표 지표 (SSOT)
TARGET_METRICS = {
    'win_rate': (85.0, 90.0),  # 승률 범위 (%, 하한, 상한)
    'mdd': (3.0, 5.0),         # MDD 범위 (%, 하한, 상한)
    'min_trades': 5000,        # 최소 거래 수
    'min_pnl': 1000.0          # 최소 수익률 (%)
}

# 파라미터 민감도 (Phase 1 결과)
SENSITIVITY = {
    'atr_mult': 1.15,          # 1.0 변화 시 Sharpe +1.15
    'filter_tf': 4.01,         # 1단계 변화 시 Sharpe +4.01
    'trail_start_r': 3.51,     # 0.1 변화 시 Sharpe +0.35 (3.51 / 10)
    'trail_dist_r': 2.47       # 0.01 변화 시 Sharpe +0.25 (2.47 / 10)
}


def analyze_preset_metrics(preset: Dict) -> Dict:
    """프리셋 메트릭 분석

    Args:
        preset: 프리셋 JSON dict

    Returns:
        분석 결과 dict {
            'status': 'conservative' | 'aggressive' | 'balanced',
            'issues': List[str],  # 문제점 목록
            'recommendations': Dict  # 파라미터별 추천 조정
        }
    """
    metrics = preset['best_metrics']
    params = preset['best_params']

    issues = []
    recommendations = {}

    # 1. 승률 분석
    win_rate = metrics['win_rate']
    if win_rate > TARGET_METRICS['win_rate'][1]:
        issues.append(f"승률 너무 높음 ({win_rate:.1f}% > {TARGET_METRICS['win_rate'][1]}%)")
        recommendations['aggressive_needed'] = True
    elif win_rate < TARGET_METRICS['win_rate'][0]:
        issues.append(f"승률 낮음 ({win_rate:.1f}% < {TARGET_METRICS['win_rate'][0]}%)")
        recommendations['conservative_needed'] = True

    # 2. MDD 분석
    mdd = metrics['mdd']
    if mdd < TARGET_METRICS['mdd'][0]:
        issues.append(f"MDD 너무 낮음 ({mdd:.1f}% < {TARGET_METRICS['mdd'][0]}%) - 리스크 여유")
        recommendations['leverage_room'] = True
    elif mdd > TARGET_METRICS['mdd'][1]:
        issues.append(f"MDD 높음 ({mdd:.1f}% > {TARGET_METRICS['mdd'][1]}%)")
        recommendations['reduce_risk'] = True

    # 3. 거래 수 분석
    trades = metrics.get('total_trades', 0)
    if trades < TARGET_METRICS['min_trades']:
        issues.append(f"거래 부족 ({trades:,}회 < {TARGET_METRICS['min_trades']:,}회)")
        recommendations['relax_filter'] = True

    # 4. 수익 분석
    pnl = metrics.get('total_pnl', 0)
    if pnl < TARGET_METRICS['min_pnl']:
        issues.append(f"수익 낮음 ({pnl:.1f}% < {TARGET_METRICS['min_pnl']:.1f}%)")
        recommendations['improve_pnl'] = True

    # 5. 상태 판단
    if recommendations.get('aggressive_needed') or recommendations.get('leverage_room'):
        status = 'conservative'
    elif recommendations.get('conservative_needed') or recommendations.get('reduce_risk'):
        status = 'aggressive'
    else:
        status = 'balanced'

    return {
        'status': status,
        'issues': issues,
        'recommendations': recommendations,
        'metrics': metrics,
        'params': params
    }


def build_coarse_ranges() -> Dict[str, List]:
    """Coarse Grid 범위 생성 (Stage 1) - v7.25.11 확장

    범위 설정:
    - 더 넓은 탐색 범위 (540개 조합)
    - filter_tf는 entry_tf('1h')보다 큰 값만 사용
    - entry_validity_hours는 6.0 고정

    Returns:
        540개 조합 (6×3×6×5) - 5배 확장
    """
    return {
        'atr_mult': [0.8, 0.9, 1.0, 1.1, 1.25, 1.5],  # 6개 (0.8, 1.5 추가)
        'filter_tf': ['4h', '6h', '8h'],               # 3개 유지
        'entry_validity_hours': [6],                   # 고정값
        'trail_start_r': [0.3, 0.4, 0.5, 0.6, 0.8, 1.0],  # 6개 (0.3, 0.5, 1.0 추가)
        'trail_dist_r': [0.03, 0.05, 0.08, 0.1, 0.12]     # 5개 (0.03, 0.12 추가)
    }


def build_fine_ranges(coarse_optimal: Dict) -> Dict[str, List]:
    """Fine-Tuning 범위 생성 (Stage 2) - v7.25.11 정밀도 향상

    Args:
        coarse_optimal: Stage 1 최적 파라미터

    Returns:
        ~1,029개 조합 (7×3×1×7×7) - 정밀도 2배 향상
    """
    # ATR ±20%
    atr_center = coarse_optimal['atr_mult']
    atr_min = max(0.3, atr_center * 0.8)
    atr_max = min(3.0, atr_center * 1.2)

    # filter_tf 전후 1단계
    tf_map = ['1h', '2h', '3h', '4h', '6h', '8h', '12h', '1d', '2d']
    tf_idx = tf_map.index(coarse_optimal['filter_tf'])
    tf_range = [
        tf_map[max(0, tf_idx - 1)],
        tf_map[tf_idx],
        tf_map[min(len(tf_map) - 1, tf_idx + 1)]
    ]

    # entry_validity_hours 고정
    entry_center = coarse_optimal['entry_validity_hours']

    # trail_start_r ±15%
    ts_center = coarse_optimal['trail_start_r']
    ts_min = max(0.2, ts_center * 0.85)
    ts_max = min(1.5, ts_center * 1.15)

    # trail_dist_r ±20%
    td_center = coarse_optimal['trail_dist_r']
    td_min = max(0.01, td_center * 0.8)
    td_max = min(0.12, td_center * 1.2)

    # 7개 균등 분할 (정밀도 향상)
    def linspace_7(min_val, max_val):
        """7개 균등 분할"""
        step = (max_val - min_val) / 6
        return [round(min_val + i * step, 3) for i in range(7)]

    return {
        'atr_mult': linspace_7(atr_min, atr_max),        # 7개
        'filter_tf': list(set(tf_range)),                # 3개
        'entry_validity_hours': [entry_center],          # 1개 (고정)
        'trail_start_r': linspace_7(ts_min, ts_max),     # 7개
        'trail_dist_r': linspace_7(td_min, td_max)       # 7개
    }


def build_adaptive_ranges(preset: Dict) -> Dict[str, List]:
    """프리셋 분석 결과 기반 파라미터 범위 자동 생성

    ⚠️ DEPRECATED: v7.25.2부터 build_coarse_ranges() + build_fine_ranges() 사용 권장

    Args:
        preset: 프리셋 JSON dict

    Returns:
        파라미터 범위 dict
    """
    analysis = analyze_preset_metrics(preset)
    metrics = analysis['metrics']
    params = analysis['params']
    recs = analysis['recommendations']

    ranges = {}

    # 1. ATR 배수
    current_atr = params.get('atr_mult', 0.5)
    if recs.get('leverage_room'):  # MDD 여유 → ATR 확대
        ranges['atr_mult'] = [0.5, 0.7, 1.0, 1.5, 2.0, 2.5]
    elif recs.get('reduce_risk'):  # MDD 높음 → ATR 축소
        ranges['atr_mult'] = [0.3, 0.4, 0.5]
    else:  # 균형
        ranges['atr_mult'] = [
            round(current_atr * 0.8, 2),
            current_atr,
            round(current_atr * 1.2, 2)
        ]

    # 2. 레버리지 (DEPRECATED - 자동 계산으로 변경)
    mdd = metrics['mdd']
    safe_lev = 10.0 / mdd if mdd > 0 else 1.0
    if safe_lev > 10:
        ranges['leverage'] = [1, 3, 5, 10, 15]
    elif safe_lev > 5:
        ranges['leverage'] = [1, 3, 5, 8, 10]
    else:
        ranges['leverage'] = [1, 3, 5]

    # 3. 필터 타임프레임
    if recs.get('relax_filter'):  # 거래 부족 → 짧은 TF
        ranges['filter_tf'] = ['1h', '2h', '3h', '4h']
    elif recs.get('conservative_needed'):  # 승률 낮음 → 긴 TF
        ranges['filter_tf'] = ['6h', '12h', '1d']
    else:  # 균형
        current_filter = params.get('filter_tf', '4h')
        ranges['filter_tf'] = [current_filter]

    # 4. 트레일링 시작 배수
    current_ts = params.get('trail_start_r', 0.4)
    if recs.get('improve_pnl'):  # 수익 낮음 → 넓게
        ranges['trail_start_r'] = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2]
    else:  # 미세 조정
        ranges['trail_start_r'] = [
            round(current_ts * 0.8, 2),
            current_ts,
            round(current_ts * 1.2, 2)
        ]

    # 5. 트레일링 간격
    current_td = params.get('trail_dist_r', 0.02)
    if recs.get('aggressive_needed'):  # 승률 높음 → 넓게
        ranges['trail_dist_r'] = [0.02, 0.04, 0.06, 0.08, 0.10]
    elif recs.get('conservative_needed'):  # 승률 낮음 → 타이트
        ranges['trail_dist_r'] = [0.01, 0.015, 0.02]
    else:  # 미세 조정
        ranges['trail_dist_r'] = [
            round(current_td * 0.8, 3),
            current_td,
            round(current_td * 1.2, 3)
        ]

    return ranges


def print_analysis_report(preset: Dict, ranges: Dict):
    """분석 리포트 출력"""
    analysis = analyze_preset_metrics(preset)

    print("=" * 80)
    print("📊 프리셋 분석 결과")
    print("=" * 80)

    print(f"\n상태: {analysis['status'].upper()}")
    print(f"  - Conservative: 너무 보수적 (승률/MDD 여유)")
    print(f"  - Aggressive: 너무 공격적 (승률 낮음/MDD 높음)")
    print(f"  - Balanced: 균형 잡힘")

    print(f"\n현재 메트릭:")
    print(f"  승률:    {analysis['metrics']['win_rate']:.1f}% (목표: {TARGET_METRICS['win_rate'][0]}-{TARGET_METRICS['win_rate'][1]}%)")
    print(f"  MDD:     {analysis['metrics']['mdd']:.1f}% (목표: {TARGET_METRICS['mdd'][0]}-{TARGET_METRICS['mdd'][1]}%)")
    print(f"  거래수:  {analysis['metrics'].get('total_trades', 0):,}회 (목표: {TARGET_METRICS['min_trades']:,}회+)")
    print(f"  수익:    {analysis['metrics'].get('total_pnl', 0):.1f}% (목표: {TARGET_METRICS['min_pnl']:.1f}%+)")

    if analysis['issues']:
        print(f"\n문제점:")
        for issue in analysis['issues']:
            print(f"  ⚠️ {issue}")

    print(f"\n권장 조치:")
    for key, value in analysis['recommendations'].items():
        if value:
            action = {
                'aggressive_needed': '더 공격적으로 → trail_dist_r ↑',
                'conservative_needed': '더 보수적으로 → filter_tf ↑',
                'leverage_room': '레버리지 활용 → leverage ↑',
                'reduce_risk': '리스크 축소 → atr_mult ↓',
                'relax_filter': '필터 완화 → filter_tf ↓',
                'improve_pnl': '수익 개선 → trail_start_r 범위 확대'
            }.get(key, key)
            print(f"  ✅ {action}")

    print(f"\n생성된 범위:")
    total_combinations = 1
    for param, values in ranges.items():
        print(f"  {param}: {len(values)}개 - {values}")
        total_combinations *= len(values)

    print(f"\n총 조합 수: {total_combinations:,}개")
    print(f"예상 시간: {total_combinations * 1.9 / 8 / 60:.1f}분 (8워커 기준)")
