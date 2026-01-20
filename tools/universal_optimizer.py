"""
Universal Parameter Optimizer (v2.2 - Fine-Tuning)

목적: 범용성 검증 - 모든 코인에서 잘 작동하는 파라미터 찾기

v2.2 업데이트 (Coarse-to-Fine):
  Step 1: Coarse 탐색 (넓은 범위, 랜덤 샘플링)
    - META_PARAM_RANGES에서 1,000개 랜덤 샘플
    - 빠른 1차 탐색 (~30초)

  Step 2: Fine 탐색 (좁은 범위, 정밀 그리드)
    - Coarse 최고 결과 주변 ±1 간격
    - 세밀한 2차 탐색 (~1분)

  범용성 점수:
    - 평균 50% + 최소값 40% + 안정성 10%
    - TF 보정: 높은 TF일수록 높은 승률 기대

타임프레임 보정:
  진입 TF + 필터 TF 조합으로 기대 승률 계산

  기본 승률 (진입 TF):
  - 1h: 68%, 4h: 72%, 1d: 76%

  TF 간격 보너스 (+2%p/단계):
  - 1h 진입 + 4h 필터 (간격 2) = 68% + 4% = 72% 기대
  - 1h 진입 + 1d 필터 (간격 6) = 68% + 12% = 80% 기대

예시:
  Coarse: 1,000개 중 최고 → atr_mult=1.5, filter_tf='4h' (점수 98.5)
  Fine: [1.25, 1.5, 1.75] × ['2h', '4h', '6h'] = 9개 조합 → 최종 1.25, '4h' (점수 99.2)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import json
import logging
from datetime import datetime

# 프로젝트 루트 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from config.parameters import DEFAULT_PARAMS
from utils.metrics import calculate_backtest_metrics
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


@dataclass
class UniversalResult:
    """범용 최적화 결과"""
    params: dict
    symbol_results: Dict[str, dict]  # 심볼별 결과

    # 통계
    avg_win_rate: float
    min_win_rate: float
    max_win_rate: float
    win_rate_std: float

    avg_sharpe: float
    avg_mdd: float
    avg_pnl: float
    total_trades: int

    # 범용성 점수
    universality_score: float

    # 포트폴리오 모드 (선택)
    portfolio_result: Optional[dict] = None

    def summary(self) -> str:
        """결과 요약"""
        base = (
            f"범용성 점수: {self.universality_score:.2f}\n"
            f"평균 승률: {self.avg_win_rate:.2f}%\n"
            f"최소 승률: {self.min_win_rate:.2f}% (중요!)\n"
            f"최대 승률: {self.max_win_rate:.2f}%\n"
            f"표준편차: {self.win_rate_std:.2f}%\n"
            f"평균 MDD: {self.avg_mdd:.2f}%"
        )

        # 포트폴리오 결과 추가
        if self.portfolio_result:
            p = self.portfolio_result
            base += (
                f"\n\n[포트폴리오 모드 - 동시 매매 검증]\n"
                f"실행된 거래: {p['total_trades']:,}개\n"
                f"건너뛴 신호: {p['skipped_signals']:,}개\n"
                f"신호 실행률: {p['execution_rate']:.1f}%\n"
                f"평균 동시 포지션: {p['avg_concurrent_positions']:.1f}개\n"
                f"최대 동시 포지션: {p['max_concurrent_positions']}개\n"
                f"실제 승률: {p['win_rate']:.1f}% (개별 평가 대비 {p['win_rate'] - self.avg_win_rate:+.1f}%p)\n"
                f"실제 MDD: {p['mdd']:.2f}% (개별 평가 대비 {p['mdd'] - self.avg_mdd:+.2f}%p)"
            )

        return base


class UniversalOptimizer:
    """범용성 검증 최적화"""

    def __init__(
        self,
        exchange: str = 'bybit',
        symbols: Optional[List[str]] = None,
        timeframe: str = '1h',
        mode: str = 'quick',
        portfolio_mode: bool = False,
        portfolio_config: Optional[dict] = None
    ):
        self.exchange = exchange
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        self.timeframe = timeframe
        self.mode = mode
        self.portfolio_mode = portfolio_mode
        self.portfolio_config = portfolio_config

        logger.info("=" * 60)
        logger.info("Universal Optimizer 초기화")
        logger.info(f"  목표: 모든 코인에서 안정적으로 작동하는 범용 파라미터")
        logger.info(f"  Exchange: {exchange}")
        logger.info(f"  Symbols: {len(self.symbols)}개")
        logger.info(f"  Timeframe: {timeframe}")
        logger.info(f"  Mode: {mode}")
        if portfolio_mode:
            logger.info(f"  포트폴리오 모드: ON (동시 매매 검증)")
            if portfolio_config:
                logger.info(f"    초기 자본: ${portfolio_config.get('initial_capital', 10000):,.0f}")
                logger.info(f"    최대 포지션: {portfolio_config.get('max_positions', 5)}개")
                logger.info(f"    거래당 자본: ${portfolio_config.get('capital_per_trade', 2000):,.0f}")
        logger.info("=" * 60)

        # 데이터 로드
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self._load_all_data()

    def _load_all_data(self):
        """모든 심볼 데이터 로드"""
        logger.info("데이터 로드 시작...")

        for symbol in self.symbols:
            try:
                dm = BotDataManager(
                    exchange_name=self.exchange,
                    symbol=symbol,
                    strategy_params={'entry_tf': self.timeframe}
                )

                dm.load_historical()
                df = dm.df_entry_full

                if df is None:
                    logger.warning(f"  ⚠️ {symbol}: 데이터 없음")
                    continue

                df_copy = df.copy()

                if len(df_copy) < 1000:
                    logger.warning(f"  ⚠️ {symbol}: 데이터 부족 ({len(df_copy)}개)")
                    continue

                self.data_cache[symbol] = df_copy
                logger.info(f"  ✅ {symbol}: {len(df_copy):,}개 캔들")

            except Exception as e:
                logger.error(f"  ❌ {symbol}: {e}")

        logger.info(f"✅ 로드 완료: {len(self.data_cache)}/{len(self.symbols)}개")

    def _run_single_backtest(self, symbol: str, params: dict) -> Optional[dict]:
        """단일 심볼 백테스트"""
        df = self.data_cache.get(symbol)
        if df is None:
            return None

        try:
            strategy = AlphaX7Core()

            result = strategy.run_backtest(
                df_entry=df,
                df_pattern=df,
                df_filter=df,
                params=params
            )

            if not result or 'trades' not in result:
                return None

            trades = result['trades']
            if len(trades) < 5:
                return None

            # 메트릭 계산
            metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

            return {
                'win_rate': metrics['win_rate'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'mdd': metrics['mdd'],
                'total_pnl': metrics['total_pnl'],
                'total_trades': metrics['total_trades']
            }

        except Exception as e:
            return None

    def _get_tf_hierarchy_value(self, tf: str) -> int:
        """타임프레임 계층 값 반환

        Args:
            tf: 타임프레임 ('1h', '4h', '1d' 등)

        Returns:
            계층 값 (높을수록 긴 타임프레임)
        """
        hierarchy = {
            '15m': 1,
            '30m': 2,
            '1h': 3,
            '2h': 4,
            '4h': 5,
            '6h': 6,
            '8h': 7,
            '12h': 8,
            '1d': 9
        }
        return hierarchy.get(tf, 5)  # 기본값: 4h

    def _get_tf_baseline_winrate(self, entry_tf: str, filter_tf: str) -> float:
        """타임프레임 조합별 기대 승률 계산

        원칙:
        1. 필터 TF가 진입 TF보다 높아야 함 (계층 검증)
        2. TF 간격이 클수록 더 강한 추세 필터 → 더 높은 승률 기대

        Args:
            entry_tf: 진입 타임프레임 ('1h', '4h' 등)
            filter_tf: 필터 타임프레임 ('4h', '12h', '1d' 등)

        Returns:
            기대 승률 (%) - 이 값보다 높으면 좋은 성능
        """
        entry_val = self._get_tf_hierarchy_value(entry_tf)
        filter_val = self._get_tf_hierarchy_value(filter_tf)

        # TF 간격 (필터가 진입보다 얼마나 높은지)
        tf_gap = filter_val - entry_val

        # 기본 승률 (진입 TF 기준)
        base_winrate = {
            '15m': 62.0,
            '30m': 65.0,
            '1h': 68.0,
            '2h': 70.0,
            '4h': 72.0,
            '6h': 73.0,
            '8h': 74.0,
            '12h': 75.0,
            '1d': 76.0
        }.get(entry_tf, 68.0)

        # TF 간격에 따른 보너스 (간격 1단계당 +2%p)
        # 예: 1h 진입 + 4h 필터 (간격 2) = 68 + 4 = 72%
        # 예: 1h 진입 + 1d 필터 (간격 6) = 68 + 12 = 80%
        gap_bonus = max(0, tf_gap) * 2.0

        expected_wr = base_winrate + gap_bonus

        # 상한선: 85% (비현실적 기대 방지)
        return min(expected_wr, 85.0)

    def _calculate_universality_score(self, symbol_results: Dict[str, dict], entry_tf: str, filter_tf: str) -> tuple:
        """범용성 점수 계산 (타임프레임 보정 적용)

        v2.1 업데이트:
        - 진입 TF + 필터 TF 조합별 기대 승률 대비 정규화
        - TF 간격이 클수록 더 높은 승률 기대

        Args:
            symbol_results: 심볼별 백테스트 결과
            entry_tf: 진입 타임프레임
            filter_tf: 필터 타임프레임

        Returns:
            (범용성 점수, 평균 승률, 최소 승률, 최대 승률, 표준편차)
        """
        win_rates = [r['win_rate'] for r in symbol_results.values()]

        # 원시 통계
        raw_avg_wr = np.mean(win_rates)
        raw_min_wr = np.min(win_rates)
        raw_max_wr = np.max(win_rates)
        win_rate_std = np.std(win_rates)

        # 타임프레임 조합 기대 승률
        expected_wr = self._get_tf_baseline_winrate(entry_tf, filter_tf)

        # 정규화된 승률 (기대 대비 성능)
        # 100 = 기대치 정확히 달성, >100 = 기대 초과, <100 = 기대 미달
        normalized_avg = (raw_avg_wr / expected_wr) * 100
        normalized_min = (raw_min_wr / expected_wr) * 100

        # 범용성 점수 = 정규화된 평균 50% + 정규화된 최소값 40% + 안정성 10%
        # 핵심 개선:
        # 1. 낮은 TF(1h)에서 75% 승률 = 높은 점수 (기대 68% 대비 +10%)
        # 2. 높은 TF(1d)에서 75% 승률 = 낮은 점수 (기대 80% 대비 -6%)
        # → TF를 올렸는데 승률이 안 올라가면 벌점!
        universality_score = (
            normalized_avg * 0.5 +
            normalized_min * 0.4 +
            (100 - win_rate_std) * 0.1
        )

        return universality_score, raw_avg_wr, raw_min_wr, raw_max_wr, win_rate_std

    def _evaluate_params(self, params: dict) -> Optional[UniversalResult]:
        """파라미터 평가 (포트폴리오 모드 지원)"""
        symbol_results = {}

        for symbol in self.data_cache.keys():
            result = self._run_single_backtest(symbol, params)
            if result:
                symbol_results[symbol] = result

        if not symbol_results:
            return None

        # 범용성 점수 계산 (타임프레임 보정 적용)
        entry_tf = self.timeframe  # 초기화 시 설정한 진입 TF
        filter_tf = params.get('filter_tf', '4h')
        score, avg_wr, min_wr, max_wr, std_wr = self._calculate_universality_score(symbol_results, entry_tf, filter_tf)

        # 기타 평균
        avg_sharpe = float(np.mean([r['sharpe_ratio'] for r in symbol_results.values()]))
        avg_mdd = float(np.mean([r['mdd'] for r in symbol_results.values()]))
        avg_pnl = float(np.mean([r['total_pnl'] for r in symbol_results.values()]))
        total_trades = sum([r['total_trades'] for r in symbol_results.values()])

        # 포트폴리오 모드 평가 (선택)
        portfolio_result_dict: Optional[dict] = None
        if self.portfolio_mode:
            try:
                from tools.portfolio_backtest import PortfolioBacktestEngine, PortfolioConfig

                # 설정 생성
                if self.portfolio_config:
                    config = PortfolioConfig(**self.portfolio_config)
                else:
                    config = PortfolioConfig()  # 기본값 사용

                # 엔진 생성 및 실행
                engine = PortfolioBacktestEngine(self.data_cache, config)
                portfolio_result = engine.run_backtest(params)

                # dict로 변환 (타입 안전성)
                if portfolio_result is not None:
                    portfolio_result_dict = {
                        'total_trades': portfolio_result.total_trades,
                        'skipped_signals': portfolio_result.skipped_signals,
                        'execution_rate': portfolio_result.execution_rate,
                        'avg_concurrent_positions': portfolio_result.avg_concurrent_positions,
                        'max_concurrent_positions': portfolio_result.max_concurrent_positions,
                        'win_rate': portfolio_result.win_rate,
                        'profit_factor': portfolio_result.profit_factor,
                        'sharpe_ratio': portfolio_result.sharpe_ratio,
                        'mdd': portfolio_result.mdd,
                        'total_pnl': portfolio_result.total_pnl,
                        'final_capital': portfolio_result.final_capital,
                        'symbol_stats': portfolio_result.symbol_stats,
                        'skipped_by_time': portfolio_result.skipped_by_time
                    }

            except Exception as e:
                logger.warning(f"포트폴리오 모드 평가 실패: {e}")
                portfolio_result_dict = None

        return UniversalResult(
            params=params,
            symbol_results=symbol_results,
            avg_win_rate=avg_wr,
            min_win_rate=min_wr,
            max_win_rate=max_wr,
            win_rate_std=std_wr,
            avg_sharpe=avg_sharpe,
            avg_mdd=avg_mdd,
            avg_pnl=avg_pnl,
            total_trades=total_trades,
            universality_score=score,
            portfolio_result=portfolio_result_dict
        )

    def _generate_fine_ranges(
        self,
        coarse_best_params: dict,
        meta_ranges: dict
    ) -> dict:
        """Coarse 최고 파라미터 주변 ±1 간격으로 Fine 범위 생성

        Args:
            coarse_best_params: Coarse 단계 최고 파라미터
            meta_ranges: 전체 메타 범위

        Returns:
            Fine 범위 딕셔너리 (각 파라미터당 최대 3개 값)
        """
        fine_ranges = {}

        # 수치형 파라미터 (±1 인덱스)
        for param in ['atr_mult', 'trail_start_r', 'trail_dist_r', 'entry_validity_hours']:
            coarse_val = coarse_best_params[param]
            all_values = meta_ranges[param]

            try:
                idx = all_values.index(coarse_val)
            except ValueError:
                # Coarse 값이 메타 범위에 없으면 그냥 해당 값만
                fine_ranges[param] = [coarse_val]
                continue

            # ±1 인덱스 (경계 처리)
            start_idx = max(0, idx - 1)
            end_idx = min(len(all_values) - 1, idx + 1)

            fine_ranges[param] = all_values[start_idx:end_idx + 1]

        # 카테고리형 파라미터 (filter_tf: ±1 계층)
        coarse_tf = coarse_best_params['filter_tf']
        tf_hierarchy = ['2h', '4h', '6h', '12h', '1d']

        try:
            tf_idx = tf_hierarchy.index(coarse_tf)
        except ValueError:
            fine_ranges['filter_tf'] = [coarse_tf]
        else:
            start_idx = max(0, tf_idx - 1)
            end_idx = min(len(tf_hierarchy) - 1, tf_idx + 1)
            fine_ranges['filter_tf'] = tf_hierarchy[start_idx:end_idx + 1]

        return fine_ranges

    def optimize(self) -> Optional[UniversalResult]:
        """최적화 실행 (v2.2 - Coarse-to-Fine)

        Step 1: Coarse (넓은 범위, 랜덤 샘플링 1,000개)
        Step 2: Fine (좁은 범위, 정밀 그리드 Coarse 최고 ±1)
        """
        logger.info("=" * 60)
        logger.info("범용성 최적화 시작 (v2.2 - Coarse-to-Fine)")
        logger.info(f"  평가 기준: 정규화된 평균 50% + 정규화된 최소값 40% + 안정성 10%")
        logger.info(f"  타임프레임 보정: 높은 TF일수록 높은 승률 기대")
        logger.info("=" * 60)

        # ─────────────────────────────────────────────────────────
        # Stage 1: Coarse (넓은 범위 랜덤 샘플링)
        # ─────────────────────────────────────────────────────────
        logger.info("🔍 Stage 1: Coarse 탐색 (랜덤 샘플링 1,000개)")
        logger.info("-" * 60)

        # ❌ DEPRECATED: Meta 최적화 사용 안 함 (Fine-Tuning이 최고 성능)
        # 재활성화 필요 시: dev_future/optimization_modes/README.md 참조
        logger.warning("⚠️ Meta 범위는 현재 사용 안 함. 대신 FINE_TUNING_RANGES 사용을 권장합니다.")
        logger.warning("재활성화: from dev_future.optimization_modes.meta_ranges import load_meta_param_ranges")

        # 폴백: FINE_TUNING_RANGES 사용
        from config.parameters import FINE_TUNING_RANGES
        import random

        meta_ranges = FINE_TUNING_RANGES  # 폴백

        # 랜덤 샘플 1,000개 생성
        coarse_samples = []
        for _ in range(1000):
            params = DEFAULT_PARAMS.copy()
            params.update({
                'atr_mult': random.choice(meta_ranges['atr_mult']),
                'filter_tf': random.choice(meta_ranges['filter_tf']),
                'trail_start_r': random.choice(meta_ranges['trail_start_r']),
                'trail_dist_r': random.choice(meta_ranges['trail_dist_r']),
                'entry_validity_hours': random.choice(meta_ranges['entry_validity_hours'])
            })
            coarse_samples.append(params)

        # Coarse 최적화
        coarse_best: Optional[UniversalResult] = None
        coarse_best_score = -1

        for idx, params in enumerate(coarse_samples, 1):
            # 진행 상황 (100개마다)
            if idx % 100 == 0 or idx == 1:
                logger.info(f"  [{idx}/1000] 테스트 중... (최고: {coarse_best_score:.2f})")

            # 평가
            result = self._evaluate_params(params)
            if result and result.universality_score > coarse_best_score:
                coarse_best_score = result.universality_score
                coarse_best = result

        if coarse_best is None:
            logger.warning("Coarse 단계 실패: 유효한 결과 없음")
            return None

        logger.info(f"✅ Coarse 완료! 최고 점수: {coarse_best_score:.2f}")
        logger.info(f"   최고 파라미터: atr={coarse_best.params['atr_mult']}, "
                   f"filter_tf={coarse_best.params['filter_tf']}, "
                   f"trail_start={coarse_best.params['trail_start_r']}, "
                   f"trail_dist={coarse_best.params['trail_dist_r']}, "
                   f"entry_validity={coarse_best.params['entry_validity_hours']}")

        # ─────────────────────────────────────────────────────────
        # Stage 2: Fine (Coarse 최고 주변 ±1 간격)
        # ─────────────────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("🎯 Stage 2: Fine 탐색 (Coarse 최고 ±1 간격)")
        logger.info("-" * 60)

        # Fine 범위 생성 (Coarse 최고 ±1)
        fine_ranges = self._generate_fine_ranges(coarse_best.params, meta_ranges)

        from itertools import product
        fine_combinations = list(product(
            fine_ranges['atr_mult'],
            fine_ranges['filter_tf'],
            fine_ranges['trail_start_r'],
            fine_ranges['trail_dist_r'],
            fine_ranges['entry_validity_hours']
        ))

        logger.info(f"  Fine 조합: {len(fine_combinations):,}개")

        # Fine 최적화
        fine_best: Optional[UniversalResult] = None
        fine_best_score = coarse_best_score  # Coarse보다 나빠지면 안 됨

        for idx, combo in enumerate(fine_combinations, 1):
            atr_mult, filter_tf, trail_start_r, trail_dist_r, entry_validity = combo

            params = DEFAULT_PARAMS.copy()
            params.update({
                'atr_mult': atr_mult,
                'filter_tf': filter_tf,
                'trail_start_r': trail_start_r,
                'trail_dist_r': trail_dist_r,
                'entry_validity_hours': entry_validity
            })

            # 진행 상황
            if idx % 5 == 0 or idx == 1:
                logger.info(f"  [{idx}/{len(fine_combinations)}] 테스트 중... (최고: {fine_best_score:.2f})")

            # 평가
            result = self._evaluate_params(params)
            if result and result.universality_score > fine_best_score:
                fine_best_score = result.universality_score
                fine_best = result

                # TF 기대 승률 계산
                expected_wr = self._get_tf_baseline_winrate(self.timeframe, filter_tf)

                # TF 간격 계산
                entry_val = self._get_tf_hierarchy_value(self.timeframe)
                filter_val = self._get_tf_hierarchy_value(filter_tf)
                tf_gap = filter_val - entry_val

                logger.info(f"    ✨ 신기록!")
                logger.info(f"       범용성: {result.universality_score:.2f}")
                logger.info(f"       평균: {result.avg_win_rate:.1f}%, 최소: {result.min_win_rate:.1f}%, 표준편차: {result.win_rate_std:.1f}%")
                logger.info(f"       TF 조합: {self.timeframe} → {filter_tf} (간격 {tf_gap}, 기대 {expected_wr:.0f}% 대비 {result.avg_win_rate - expected_wr:+.1f}%p)")

        # Fine 결과가 없으면 Coarse 결과 사용
        if fine_best is None:
            fine_best = coarse_best
            logger.info(f"⚠️ Fine 개선 없음, Coarse 결과 사용 (점수: {coarse_best_score:.2f})")

        logger.info("=" * 60)
        logger.info("최적화 완료!")
        logger.info(fine_best.summary())
        logger.info("=" * 60)

        return fine_best

    def save_preset(self, result: UniversalResult, filename: Optional[str] = None):
        """프리셋 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"universal_{self.exchange}_{self.timeframe}_{timestamp}.json"

        preset_path = ROOT / 'presets' / filename
        preset_path.parent.mkdir(parents=True, exist_ok=True)

        preset_data = {
            "meta_info": {
                "type": "universal_multi_symbol",
                "exchange": self.exchange,
                "timeframe": self.timeframe,
                "symbols": list(result.symbol_results.keys()),
                "optimization_mode": self.mode,
                "created_at": datetime.now().isoformat()
            },
            "best_params": result.params,
            "universality_metrics": {
                "universality_score": result.universality_score,
                "avg_win_rate": result.avg_win_rate,
                "min_win_rate": result.min_win_rate,
                "max_win_rate": result.max_win_rate,
                "win_rate_std": result.win_rate_std,
                "avg_sharpe_ratio": result.avg_sharpe,
                "avg_mdd": result.avg_mdd,
                "avg_pnl": result.avg_pnl,
                "total_trades": result.total_trades
            },
            "symbol_results": result.symbol_results
        }

        with open(preset_path, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 프리셋 저장: {preset_path}")
        return preset_path


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Universal Parameter Optimizer')
    parser.add_argument('--exchange', default='bybit')
    parser.add_argument('--symbols', default='BTCUSDT,ETHUSDT,BNBUSDT')
    parser.add_argument('--timeframe', default='1h')
    parser.add_argument('--mode', default='quick', choices=['quick', 'standard', 'deep'])
    parser.add_argument('--output', help='출력 파일명')

    args = parser.parse_args()

    # 심볼 파싱
    symbols = [s.strip() for s in args.symbols.split(',')]

    # 최적화
    optimizer = UniversalOptimizer(
        exchange=args.exchange,
        symbols=symbols,
        timeframe=args.timeframe,
        mode=args.mode
    )

    result = optimizer.optimize()

    if result:
        # 프리셋 저장
        preset_path = optimizer.save_preset(result, args.output)

        print("\n" + "=" * 60)
        print("✅ 범용 최적화 완료!")
        print("=" * 60)
        print(result.summary())
        print(f"\n📁 프리셋: {preset_path}")
        print("=" * 60)

        print("\n📊 심볼별 승률:")
        for symbol, metrics in sorted(result.symbol_results.items(), key=lambda x: x[1]['win_rate'], reverse=True):
            print(f"  {symbol:12s}: {metrics['win_rate']:.1f}%")
    else:
        print("❌ 최적화 실패")


if __name__ == '__main__':
    main()
