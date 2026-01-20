"""파라미터 영향도 분석 테스트

영향도 기반 최적화 검증:
1. 디폴트 기준점 생성
2. 각 파라미터 영향도 측정
3. 중요도 순위 파악
4. 최적값 자동 찾기

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.constants import EXCHANGE_INFO
from config.parameters import DEFAULT_PARAMS
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.metrics import calculate_backtest_metrics


class SensitivityAnalyzer:
    """파라미터 영향도 분석기"""

    def __init__(self, df: pd.DataFrame, strategy_type: str = 'macd'):
        self.df = df
        self.strategy_type = strategy_type
        self.baseline_score = 0.0
        self.baseline_params = DEFAULT_PARAMS.copy()

    def run_backtest(self, params: dict) -> dict:
        """백테스트 실행

        Args:
            params: 테스트할 파라미터

        Returns:
            백테스트 메트릭
        """
        # AlphaX7Core 인스턴스 생성
        strategy = AlphaX7Core(use_mtf=True, strategy_type=self.strategy_type)

        # run_backtest() 메서드 호출 (df_pattern, df_entry 필요)
        trades = strategy.run_backtest(
            df_pattern=self.df,
            df_entry=self.df,
            **params
        )

        # trades가 튜플인 경우 첫 번째 요소만 사용
        if isinstance(trades, tuple):
            trades = trades[0]

        # 메트릭 계산
        metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)
        return metrics

    def get_baseline(self) -> Tuple[float, dict]:
        """기준점 생성 (디폴트 파라미터)

        Returns:
            (Sharpe Ratio, 전체 메트릭)
        """
        print("=" * 60)
        print("📌 1단계: 기준점 생성 (Baseline)")
        print("=" * 60)

        result = self.run_backtest(self.baseline_params)
        sharpe = result.get('sharpe_ratio', 0.0)

        print(f"\n디폴트 파라미터:")
        for key, value in self.baseline_params.items():
            print(f"  {key}: {value}")

        print(f"\n기준 성과:")
        print(f"  거래수: {result.get('total_trades', 0)}")
        print(f"  승률: {result.get('win_rate', 0):.1f}%")
        print(f"  Sharpe: {sharpe:.2f}")
        print(f"  MDD: {result.get('mdd', 0):.1f}%")
        print(f"  총 PnL: {result.get('total_pnl', 0):.1f}%")

        self.baseline_score = sharpe
        return sharpe, result

    def analyze_param(self, param_name: str, param_range: list) -> Dict[str, Any]:
        """단일 파라미터 영향도 분석

        Args:
            param_name: 파라미터 이름
            param_range: 테스트할 값 범위

        Returns:
            {
                'sensitivity': 영향도 (최대-최소),
                'best_value': 최적값,
                'best_score': 최고 점수,
                'results': [(값, 점수), ...]
            }
        """
        print(f"\n분석 중: {param_name}...", end=" ")

        results = []
        for value in param_range:
            # 다른 파라미터는 디폴트, 이것만 변경
            test_params = self.baseline_params.copy()
            test_params[param_name] = value

            # 백테스트 실행
            result = self.run_backtest(test_params)
            score = result.get('sharpe_ratio', 0.0)
            results.append((value, score))

        # 영향도 계산
        scores = [s for _, s in results]
        sensitivity = max(scores) - min(scores)

        # 최적값 찾기
        best_idx = np.argmax(scores)
        best_value = results[best_idx][0]
        best_score = results[best_idx][1]

        print(f"완료! (영향도: {sensitivity:+.2f}, 최적: {best_value})")

        return {
            'sensitivity': sensitivity,
            'best_value': best_value,
            'best_score': best_score,
            'results': results
        }

    def analyze_all(self) -> Dict[str, Dict]:
        """전체 파라미터 영향도 분석

        Returns:
            {
                'param_name': {
                    'sensitivity': float,
                    'best_value': any,
                    'best_score': float,
                    'rank': int
                }
            }
        """
        # 1. 기준점 생성
        baseline_sharpe, baseline_result = self.get_baseline()

        # 2. 파라미터 범위 정의
        param_ranges = self._get_param_ranges()

        # 3. 각 파라미터 분석
        print("\n" + "=" * 60)
        print("🔍 2단계: 영향도 분석 (각 파라미터)")
        print("=" * 60)

        analysis_results = {}
        for param_name, param_range in param_ranges.items():
            result = self.analyze_param(param_name, param_range)
            analysis_results[param_name] = result

        # 4. 영향도 순위 매기기
        ranked = sorted(
            analysis_results.items(),
            key=lambda x: x[1]['sensitivity'],
            reverse=True
        )

        for rank, (param_name, data) in enumerate(ranked, 1):
            analysis_results[param_name]['rank'] = rank

        return analysis_results

    def _get_param_ranges(self) -> Dict[str, List]:
        """전략별 파라미터 범위 반환"""
        if self.strategy_type == 'macd':
            return {
                'macd_fast': [4, 6, 8, 10, 12],
                'macd_slow': [16, 18, 20, 22, 26],
                'macd_signal': [5, 7, 9, 11],
                'atr_mult': [0.5, 1.0, 1.25, 1.5, 2.0],
                'trail_start_r': [0.4, 0.8, 1.2, 1.5, 2.0],
                'trail_dist_r': [0.02, 0.05, 0.1, 0.15, 0.2],
                'filter_tf': ['2h', '4h', '6h', '12h', '1d'],
                'entry_validity_hours': [6, 12, 24, 48, 72],
            }
        else:  # adx
            return {
                'adx_period': [7, 10, 14, 18, 21],
                'adx_threshold': [10, 15, 20, 25, 30],
                'atr_mult': [0.5, 1.0, 1.25, 1.5, 2.0],
                'trail_start_r': [0.4, 0.8, 1.2, 1.5, 2.0],
                'trail_dist_r': [0.02, 0.05, 0.1, 0.15, 0.2],
                'filter_tf': ['2h', '4h', '6h', '12h', '1d'],
                'entry_validity_hours': [6, 12, 24, 48, 72],
            }

    def print_report(self, results: Dict[str, Dict]):
        """리포트 출력

        Args:
            results: analyze_all() 결과
        """
        print("\n" + "=" * 60)
        print("📊 3단계: 영향도 순위 및 결과")
        print("=" * 60)

        # 순위별 정렬
        ranked = sorted(
            results.items(),
            key=lambda x: x[1]['rank']
        )

        print(f"\n{'순위':<4} {'파라미터':<20} {'영향도':>10} {'최적값':>15} {'최고 Sharpe':>15}")
        print("-" * 70)

        for param_name, data in ranked:
            rank = data['rank']
            sensitivity = data['sensitivity']
            best_value = data['best_value']
            best_score = data['best_score']

            print(f"{rank:<4} {param_name:<20} {sensitivity:>+10.2f} {str(best_value):>15} {best_score:>15.2f}")

        # Top 3 강조
        print("\n" + "=" * 60)
        print("🏆 가장 영향력 있는 파라미터 Top 3")
        print("=" * 60)

        top3 = ranked[:3]
        for i, (param_name, data) in enumerate(top3, 1):
            print(f"{i}. **{param_name}**: 영향도 {data['sensitivity']:+.2f}, 최적값 `{data['best_value']}`")

        # 최적 조합 제안
        print("\n" + "=" * 60)
        print("🎯 권장 최적 파라미터")
        print("=" * 60)
        print("```python")
        print("OPTIMAL_PARAMS = {")
        for param_name, data in sorted(results.items()):
            print(f"    '{param_name}': {repr(data['best_value'])},")
        print("}")
        print("```")

        # 예상 개선치
        max_improvement = sum(data['sensitivity'] for _, data in top3)
        print(f"\n💡 예상 개선: Sharpe {self.baseline_score:.2f} → {self.baseline_score + max_improvement:.2f} ({max_improvement:+.2f})")


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🧪 파라미터 영향도 분석 테스트")
    print("=" * 60)

    # 1. 데이터 로드
    print("\n📥 데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})

    try:
        success = dm.load_historical()
        if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
            print("❌ 데이터 없음. 먼저 데이터를 다운로드하세요.")
            return

        df = dm.df_entry_full
        print(f"✅ 데이터 로드 완료: {len(df)}개 캔들")

    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. 전략 선택
    strategy_type = 'macd'  # 또는 'adx'
    print(f"\n전략: {strategy_type.upper()}")

    # 3. 영향도 분석 실행
    start_time = datetime.now()

    analyzer = SensitivityAnalyzer(df, strategy_type)
    results = analyzer.analyze_all()

    elapsed = (datetime.now() - start_time).total_seconds()

    # 4. 리포트 출력
    analyzer.print_report(results)

    # 5. 성능 통계
    total_tests = sum(len(analyzer._get_param_ranges()[param]) for param in results.keys())
    print("\n" + "=" * 60)
    print("⏱️ 성능 통계")
    print("=" * 60)
    print(f"총 테스트 횟수: {total_tests}회")
    print(f"소요 시간: {elapsed:.1f}초")
    print(f"평균 속도: {elapsed/total_tests:.3f}초/테스트")

    print("\n✅ 테스트 완료!")


if __name__ == '__main__':
    main()
