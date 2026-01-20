"""진입 시점 Open/Close 갭 분석

최적 파라미터로 백테스트 실행 후
실제 진입 봉들의 O→C 가격 변동 분석

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.parameters import DEFAULT_PARAMS
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.metrics import calculate_backtest_metrics


class EntryOCGapAnalyzer:
    """진입 시점 O/C 갭 분석기"""

    def __init__(self, df: pd.DataFrame, strategy_type: str = 'macd'):
        self.df = df
        self.strategy_type = strategy_type

    def run_backtest_with_oc_tracking(self, params: dict) -> Tuple[List[dict], pd.DataFrame]:
        """백테스트 실행하면서 O/C 갭 추적

        Args:
            params: 백테스트 파라미터

        Returns:
            (trades, oc_gap_df)
            - trades: 거래 내역
            - oc_gap_df: 진입 봉의 O/C 갭 통계
        """
        strategy = AlphaX7Core(use_mtf=True, strategy_type=self.strategy_type)

        # 백테스트 실행
        trades = strategy.run_backtest(
            df_pattern=self.df,
            df_entry=self.df,
            **params
        )

        if isinstance(trades, tuple):
            trades = trades[0]

        # 진입 봉의 O/C 갭 추출
        oc_gaps = []
        for trade in trades:
            entry_time = trade.get('entry_time')
            if entry_time is None:
                continue

            # 진입 봉 찾기 (신호 발생 다음 봉)
            try:
                signal_idx_raw = self.df.index.get_loc(entry_time)
                # get_loc can return int, slice, or array
                if isinstance(signal_idx_raw, int):
                    signal_idx = signal_idx_raw
                else:
                    continue

                entry_idx = signal_idx + 1

                if entry_idx >= len(self.df):
                    continue

                entry_candle = self.df.iloc[entry_idx]

                # O/H/L 갭 계산
                open_price = entry_candle['open']
                high_price = entry_candle['high']
                low_price = entry_candle['low']
                close_price = entry_candle['close']

                side = trade.get('side', 'Long')

                # Long: Low가 Open보다 낮으면 유리 (더 싸게 살 기회)
                # Short: High가 Open보다 높으면 유리 (더 비싸게 팔 기회)
                if side == 'Long':
                    low_drop_pct = (low_price - open_price) / open_price * 100  # 음수 = 떨어짐
                    high_rise_pct = (high_price - open_price) / open_price * 100  # 양수 = 올랐음
                else:  # Short
                    high_rise_pct = (high_price - open_price) / open_price * 100  # 양수 = 올랐음 (유리)
                    low_drop_pct = (low_price - open_price) / open_price * 100  # 음수 = 떨어짐

                oc_gaps.append({
                    'entry_time': self.df.index[entry_idx],
                    'side': side,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'low_drop_pct': low_drop_pct,  # Open 대비 Low 하락률
                    'high_rise_pct': high_rise_pct,  # Open 대비 High 상승률
                    'pnl': trade.get('pnl', 0)
                })

            except (KeyError, IndexError) as e:
                continue

        oc_gap_df = pd.DataFrame(oc_gaps)

        return trades, oc_gap_df

    def analyze_gap_statistics(self, oc_gap_df: pd.DataFrame) -> dict[str, int | dict[str, float]]:
        """O/H/L 갭 통계 분석

        Args:
            oc_gap_df: O/H/L 갭 데이터프레임

        Returns:
            통계 딕셔너리
        """
        stats: dict[str, int | dict[str, float]] = {
            'total_count': len(oc_gap_df),
            'long_count': len(oc_gap_df[oc_gap_df['side'] == 'Long']),
            'short_count': len(oc_gap_df[oc_gap_df['side'] == 'Short']),
        }

        # Long 통계 (Low 하락, High 상승)
        long_df = oc_gap_df[oc_gap_df['side'] == 'Long']
        if len(long_df) > 0:
            long_stats: dict[str, float] = {
                'low_drop_mean': float(long_df['low_drop_pct'].mean()),
                'low_drop_median': float(long_df['low_drop_pct'].median()),
                'low_drop_std': float(long_df['low_drop_pct'].std()),
                'low_drop_min': float(long_df['low_drop_pct'].min()),
                'low_drop_p25': float(long_df['low_drop_pct'].quantile(0.25)),
                'high_rise_mean': float(long_df['high_rise_pct'].mean()),
                'high_rise_median': float(long_df['high_rise_pct'].median()),
                'high_rise_max': float(long_df['high_rise_pct'].max()),
            }
            stats['long'] = long_stats

        # Short 통계 (High 상승, Low 하락)
        short_df = oc_gap_df[oc_gap_df['side'] == 'Short']
        if len(short_df) > 0:
            short_stats: dict[str, float] = {
                'high_rise_mean': float(short_df['high_rise_pct'].mean()),
                'high_rise_median': float(short_df['high_rise_pct'].median()),
                'high_rise_std': float(short_df['high_rise_pct'].std()),
                'high_rise_max': float(short_df['high_rise_pct'].max()),
                'high_rise_p75': float(short_df['high_rise_pct'].quantile(0.75)),
                'low_drop_mean': float(short_df['low_drop_pct'].mean()),
                'low_drop_median': float(short_df['low_drop_pct'].median()),
                'low_drop_min': float(short_df['low_drop_pct'].min()),
            }
            stats['short'] = short_stats

        return stats

    def recommend_limit_price(self, stats: dict) -> dict:
        """지정가 주문 권장 가격 제안

        Args:
            stats: analyze_gap_statistics() 결과

        Returns:
            권장값 딕셔너리
        """
        recommendations = {}

        # Long 지정가 (Open 대비 낮게)
        if 'long' in stats:
            long_stats = stats['long']
            # Low 평균의 50% (안전 마진)
            long_limit = long_stats['low_drop_mean'] * 0.5
            recommendations['long_limit'] = round(long_limit, 3)
            recommendations['long_low_avg'] = round(long_stats['low_drop_mean'], 3)
            recommendations['long_low_p25'] = round(long_stats['low_drop_p25'], 3)

        # Short 지정가 (Open 대비 높게)
        if 'short' in stats:
            short_stats = stats['short']
            # High 평균의 50% (안전 마진)
            short_limit = short_stats['high_rise_mean'] * 0.5
            recommendations['short_limit'] = round(short_limit, 3)
            recommendations['short_high_avg'] = round(short_stats['high_rise_mean'], 3)
            recommendations['short_high_p75'] = round(short_stats['high_rise_p75'], 3)

        return recommendations

    def print_report(self, stats: dict, recommendations: dict, params: dict):
        """분석 리포트 출력"""
        print("=" * 80)
        print("📊 진입 시점 Open 대비 High/Low 분석 리포트")
        print("=" * 80)

        # 파라미터
        print("\n[백테스트 파라미터]")
        for key, value in params.items():
            print(f"  {key}: {value}")

        # 샘플 수
        print(f"\n[분석 샘플]")
        print(f"  총 진입: {stats['total_count']}회")
        print(f"  Long: {stats['long_count']}회")
        print(f"  Short: {stats['short_count']}회")

        # Long 통계
        if 'long' in stats:
            print(f"\n[Long 포지션 분석] - Open 대비")
            print("-" * 80)
            long_stats = stats['long']
            print(f"Low 하락 (더 싸게 살 기회):")
            print(f"  평균:     {long_stats['low_drop_mean']:>8.3f}% (음수 = Open보다 싸짐)")
            print(f"  중간값:   {long_stats['low_drop_median']:>8.3f}%")
            print(f"  표준편차: {long_stats['low_drop_std']:>8.3f}%")
            print(f"  최대하락: {long_stats['low_drop_min']:>8.3f}% (가장 유리)")
            print(f"  25%:      {long_stats['low_drop_p25']:>8.3f}%")

            print(f"\nHigh 상승 (놓친 기회):")
            print(f"  평균:     {long_stats['high_rise_mean']:>8.3f}%")
            print(f"  중간값:   {long_stats['high_rise_median']:>8.3f}%")
            print(f"  최대상승: {long_stats['high_rise_max']:>8.3f}%")

        # Short 통계
        if 'short' in stats:
            print(f"\n[Short 포지션 분석] - Open 대비")
            print("-" * 80)
            short_stats = stats['short']
            print(f"High 상승 (더 비싸게 팔 기회):")
            print(f"  평균:     {short_stats['high_rise_mean']:>8.3f}% (양수 = Open보다 비싸짐)")
            print(f"  중간값:   {short_stats['high_rise_median']:>8.3f}%")
            print(f"  표준편차: {short_stats['high_rise_std']:>8.3f}%")
            print(f"  최대상승: {short_stats['high_rise_max']:>8.3f}% (가장 유리)")
            print(f"  75%:      {short_stats['high_rise_p75']:>8.3f}%")

            print(f"\nLow 하락 (놓친 기회):")
            print(f"  평균:     {short_stats['low_drop_mean']:>8.3f}%")
            print(f"  중간값:   {short_stats['low_drop_median']:>8.3f}%")
            print(f"  최대하락: {short_stats['low_drop_min']:>8.3f}%")

        # 지정가 권장값
        print("\n" + "=" * 80)
        print("💡 지정가 주문 권장값 (Open 대비)")
        print("=" * 80)

        if 'long_limit' in recommendations:
            print(f"\n[Long 지정가]")
            print(f"  권장가격: Open {recommendations['long_limit']:+.3f}% (평균 Low의 50%)")
            print(f"  Low 평균: Open {recommendations['long_low_avg']:+.3f}%")
            print(f"  Low 25%:  Open {recommendations['long_low_p25']:+.3f}%")
            print(f"\n  해석: 신호 발생 후 Open가보다 {abs(recommendations['long_limit']):.3f}% 낮은 지정가 주문")
            print(f"        → 약 50% 확률로 체결 예상")

        if 'short_limit' in recommendations:
            print(f"\n[Short 지정가]")
            print(f"  권장가격: Open {recommendations['short_limit']:+.3f}% (평균 High의 50%)")
            print(f"  High 평균: Open {recommendations['short_high_avg']:+.3f}%")
            print(f"  High 75%:  Open {recommendations['short_high_p75']:+.3f}%")
            print(f"\n  해석: 신호 발생 후 Open가보다 {recommendations['short_limit']:.3f}% 높은 지정가 주문")
            print(f"        → 약 50% 확률로 체결 예상")

        # 권장 사항
        print("\n" + "=" * 80)
        print("✅ 권장 사항")
        print("=" * 80)

        if 'long' in stats:
            long_avg = abs(stats['long']['low_drop_mean'])
            if long_avg > 0.1:
                print(f"\n📌 Long: Low 평균 하락 {long_avg:.3f}% → 지정가 주문 권장")
                print(f"   지정가를 Open {recommendations['long_limit']:+.3f}%에 설정하면")
                print(f"   평균적으로 Open 대비 {abs(recommendations['long_limit']):.3f}% 저렴하게 진입 가능")
            else:
                print(f"\n📌 Long: Low 평균 하락 {long_avg:.3f}% → 시장가 주문 가능")

        if 'short' in stats:
            short_avg = stats['short']['high_rise_mean']
            if short_avg > 0.1:
                print(f"\n📌 Short: High 평균 상승 {short_avg:.3f}% → 지정가 주문 권장")
                print(f"   지정가를 Open {recommendations['short_limit']:+.3f}%에 설정하면")
                print(f"   평균적으로 Open 대비 {recommendations['short_limit']:.3f}% 비싸게 진입 가능")
            else:
                print(f"\n📌 Short: High 평균 상승 {short_avg:.3f}% → 시장가 주문 가능")

        print("\n✅ 분석 완료!")


def main():
    """메인 함수"""
    print("=" * 80)
    print("🎯 진입 시점 O/C 갭 분석")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n📥 데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})

    try:
        success = dm.load_historical()
        if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
            print("❌ 데이터 없음.")
            return

        df = dm.df_entry_full
        print(f"✅ 데이터 로드 완료: {len(df):,}개 캔들")

    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return

    # 2. 최적 파라미터 (Fine-Tuning 결과)
    optimal_params = DEFAULT_PARAMS.copy()
    optimal_params.update({
        'atr_mult': 1.25,
        'filter_tf': '4h',
        'trail_start_r': 0.4,
        'trail_dist_r': 0.05,
        'entry_validity_hours': 6.0,
    })

    print("\n[사용 파라미터]")
    for key, value in optimal_params.items():
        print(f"  {key}: {value}")

    # 3. O/C 갭 분석
    print("\n🔄 백테스트 실행 중...")
    analyzer = EntryOCGapAnalyzer(df, strategy_type='macd')

    trades, oc_gap_df = analyzer.run_backtest_with_oc_tracking(optimal_params)

    print(f"✅ 백테스트 완료: {len(trades)}개 거래")
    print(f"✅ O/C 갭 추출 완료: {len(oc_gap_df)}개 진입 봉")

    # 4. 통계 분석
    stats = analyzer.analyze_gap_statistics(oc_gap_df)
    recommendations = analyzer.recommend_limit_price(stats)

    # 5. 리포트 출력
    analyzer.print_report(stats, recommendations, optimal_params)

    # 6. CSV 저장
    output_path = Path(__file__).parent.parent / 'oc_gap_analysis.csv'
    oc_gap_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n💾 CSV 저장: {output_path}")


if __name__ == '__main__':
    main()
