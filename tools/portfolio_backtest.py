"""
Portfolio Backtest Engine (v1.0)

목적: 동시 매매 시 신호 충돌 및 자본 제약 검증

핵심 기능:
1. 시간순 신호 병합 (모든 심볼)
2. 자본 제약 (최대 동시 포지션 수)
3. 신호 건너뛰기 추적 (skipped_signals)
4. 우선순위 전략 (Sharpe Ratio 기반)

예시:
  자본: $10,000, 최대 포지션: 3개
  신호: BTC(10:00), ETH(10:00), SOL(10:05)
  → BTC, ETH 진입 (자본 사용 66%)
  → SOL 진입 시도 → 자본 부족 → 건너뛰기

Author: Claude Sonnet 4.5
Version: 1.0.0
Date: 2026-01-20
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

# 프로젝트 루트 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.strategy_core import AlphaX7Core
from utils.metrics import calculate_backtest_metrics
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


@dataclass
class PortfolioConfig:
    """포트폴리오 백테스트 설정"""
    initial_capital: float = 10000.0        # 초기 자본 ($)
    max_positions: int = 5                   # 최대 동시 포지션 수
    capital_per_trade: float = 2000.0       # 거래당 자본 ($)
    priority_metric: str = 'sharpe_ratio'   # 우선순위 지표 ('sharpe_ratio', 'win_rate')


@dataclass
class PortfolioResult:
    """포트폴리오 백테스트 결과"""
    total_trades: int                        # 실행된 총 거래 수
    skipped_signals: int                     # 건너뛴 신호 수
    execution_rate: float                    # 신호 실행률 (%)
    avg_concurrent_positions: float          # 평균 동시 포지션 수
    max_concurrent_positions: int            # 최대 동시 포지션 수

    # 메트릭 (실행된 거래만)
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    mdd: float
    total_pnl: float
    final_capital: float

    # 심볼별 통계
    symbol_stats: Dict[str, dict] = field(default_factory=dict)

    # 시간대별 통계
    skipped_by_time: List[dict] = field(default_factory=list)


class PortfolioBacktestEngine:
    """포트폴리오 백테스트 엔진

    동작:
    1. 모든 심볼의 신호를 시간순으로 병합
    2. 각 신호 시점에서 자본 제약 확인
    3. 자본 부족 시 신호 건너뛰기
    4. 실행된 거래만 집계하여 메트릭 계산
    """

    def __init__(
        self,
        data_cache: Dict[str, pd.DataFrame],
        config: PortfolioConfig
    ):
        """초기화

        Args:
            data_cache: 심볼별 데이터프레임 딕셔너리
            config: 포트폴리오 설정
        """
        self.data_cache = data_cache
        self.config = config

        # 심볼별 우선순위 (초기값: 동일)
        self.symbol_priority: Dict[str, float] = {
            symbol: 1.0 for symbol in data_cache.keys()
        }

    def set_symbol_priorities(self, priorities: Dict[str, float]):
        """심볼 우선순위 설정

        Args:
            priorities: 심볼별 우선순위 점수 (높을수록 우선)
                        예: {'BTCUSDT': 2.5, 'ETHUSDT': 2.0, ...}
        """
        self.symbol_priority = priorities

    def run_backtest(self, params: dict) -> Optional[PortfolioResult]:
        """포트폴리오 백테스트 실행

        Args:
            params: 전략 파라미터

        Returns:
            포트폴리오 백테스트 결과 (실패 시 None)
        """
        logger.info("=" * 60)
        logger.info("포트폴리오 백테스트 시작")
        logger.info(f"  초기 자본: ${self.config.initial_capital:,.0f}")
        logger.info(f"  최대 포지션: {self.config.max_positions}개")
        logger.info(f"  거래당 자본: ${self.config.capital_per_trade:,.0f}")
        logger.info("=" * 60)

        # 1. 심볼별 개별 백테스트 (신호 생성)
        all_signals = self._generate_all_signals(params)

        if not all_signals:
            logger.warning("신호 생성 실패")
            return None

        logger.info(f"총 신호 수: {len(all_signals):,}개 (모든 심볼)")

        # 2. 시간순 정렬
        all_signals.sort(key=lambda x: x['timestamp'])

        # 3. 포트폴리오 시뮬레이션 (자본 제약)
        executed_trades, skipped_signals = self._simulate_portfolio(all_signals, params)

        logger.info(f"실행된 거래: {len(executed_trades):,}개")
        logger.info(f"건너뛴 신호: {len(skipped_signals):,}개")
        logger.info(f"신호 실행률: {len(executed_trades) / len(all_signals) * 100:.1f}%")

        # 4. 메트릭 계산 (실행된 거래만)
        if len(executed_trades) < 5:
            logger.warning("실행된 거래 부족 (< 5개)")
            return None

        metrics = calculate_backtest_metrics(
            trades=executed_trades,
            leverage=params.get('leverage', 1),
            capital=self.config.initial_capital
        )

        # 5. 동시 포지션 통계
        concurrent_stats = self._calculate_concurrent_stats(executed_trades)

        # 6. 심볼별 통계
        symbol_stats = self._calculate_symbol_stats(executed_trades)

        result = PortfolioResult(
            total_trades=len(executed_trades),
            skipped_signals=len(skipped_signals),
            execution_rate=len(executed_trades) / len(all_signals) * 100,
            avg_concurrent_positions=concurrent_stats['avg'],
            max_concurrent_positions=concurrent_stats['max'],
            win_rate=metrics['win_rate'],
            profit_factor=metrics['profit_factor'],
            sharpe_ratio=metrics['sharpe_ratio'],
            mdd=metrics['mdd'],
            total_pnl=metrics['total_pnl'],
            final_capital=metrics['final_capital'],
            symbol_stats=symbol_stats,
            skipped_by_time=skipped_signals
        )

        logger.info("=" * 60)
        logger.info("포트폴리오 백테스트 완료")
        logger.info(f"  승률: {result.win_rate:.1f}%")
        logger.info(f"  MDD: {result.mdd:.2f}%")
        logger.info(f"  Sharpe: {result.sharpe_ratio:.2f}")
        logger.info(f"  평균 동시 포지션: {result.avg_concurrent_positions:.1f}개")
        logger.info("=" * 60)

        return result

    def _generate_all_signals(self, params: dict) -> List[dict]:
        """모든 심볼의 신호 생성

        Args:
            params: 전략 파라미터

        Returns:
            신호 리스트 [{'symbol': 'BTCUSDT', 'timestamp': ..., 'side': 'Long', ...}]
        """
        all_signals = []

        for symbol, df in self.data_cache.items():
            try:
                # 전략 실행 (결과는 거래 리스트)
                strategy = AlphaX7Core(strategy_type='macd')
                trades = strategy.run_backtest(
                    df_pattern=df,
                    df_entry=df,
                    atr_mult=params.get('atr_mult'),
                    trail_start_r=params.get('trail_start_r'),
                    trail_dist_r=params.get('trail_dist_r'),
                    pattern_tolerance=params.get('pattern_tolerance'),
                    entry_validity_hours=params.get('entry_validity_hours'),
                    filter_tf=params.get('filter_tf'),
                    rsi_period=params.get('rsi_period'),
                    atr_period=params.get('atr_period'),
                    macd_fast=params.get('macd_fast'),
                    macd_slow=params.get('macd_slow'),
                    macd_signal=params.get('macd_signal'),
                    ema_period=params.get('ema_period')
                )

                # run_backtest()는 거래 리스트를 반환
                if not trades or not isinstance(trades, list):
                    logger.warning(f"  {symbol}: 거래 없음")
                    continue

                # 거래 → 신호 변환 (진입 시점만)
                for trade in trades:
                    all_signals.append({
                        'symbol': symbol,
                        'timestamp': trade['entry_time'],  # 진입 시간
                        'side': trade['type'],              # Long/Short (주의: 'type' 키)
                        'entry_price': trade['entry'],      # 진입가
                        'stop_loss': trade.get('sl', 0),    # SL (없을 수 있음)
                        'take_profit': trade.get('tp', 0),  # TP (없을 수 있음)
                        'priority': self.symbol_priority.get(symbol, 1.0),
                        # 백테스트 결과 (참고용)
                        'exit_price': trade['exit'],
                        'exit_time': trade['exit_time'],
                        'pnl': trade['pnl']
                    })

                logger.info(f"  {symbol}: {len(trades)}개 거래")

            except Exception as e:
                logger.error(f"  {symbol}: 신호 생성 실패 - {e}", exc_info=True)

        return all_signals

    def _simulate_portfolio(
        self,
        all_signals: List[dict],
        params: dict
    ) -> Tuple[List[dict], List[dict]]:
        """포트폴리오 시뮬레이션 (자본 제약 + 실제 포지션 생명주기)

        핵심 개선:
        - 진입 신호의 exit_time을 사용하여 실제 청산 시점 추적
        - 시간 순서대로 진입/청산 이벤트 처리
        - 청산 시점에 자본 반환 및 포지션 해제

        Args:
            all_signals: 시간순 정렬된 신호 리스트 (원본 백테스트의 완료된 거래)
            params: 전략 파라미터

        Returns:
            (실행된 거래, 건너뛴 신호)
        """
        executed_trades = []
        skipped_signals = []

        # 현재 포지션 추적 {symbol: {'entry_time': ..., 'exit_time': ..., ...}}
        open_positions: Dict[str, dict] = {}

        capital_used = 0.0

        # 이벤트 큐 생성: 진입 이벤트 + 청산 이벤트
        events = []
        for signal in all_signals:
            # 진입 이벤트
            events.append({
                'type': 'entry',
                'timestamp': signal['timestamp'],
                'symbol': signal['symbol'],
                'signal': signal
            })
            # 청산 이벤트 (원본 거래의 실제 청산 시간 사용)
            events.append({
                'type': 'exit',
                'timestamp': signal['exit_time'],
                'symbol': signal['symbol'],
                'signal': signal
            })

        # 시간순 정렬
        events.sort(key=lambda x: x['timestamp'])

        for event in events:
            if event['type'] == 'entry':
                symbol = event['symbol']
                timestamp = event['timestamp']
                signal = event['signal']

                # 이미 포지션 있으면 건너뛰기
                if symbol in open_positions:
                    skipped_signals.append({
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'reason': 'already_in_position'
                    })
                    continue

                # 최대 포지션 수 체크
                if len(open_positions) >= self.config.max_positions:
                    skipped_signals.append({
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'reason': 'max_positions_reached'
                    })
                    continue

                # 자본 부족 체크
                if capital_used + self.config.capital_per_trade > self.config.initial_capital:
                    skipped_signals.append({
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'reason': 'insufficient_capital'
                    })
                    continue

                # 진입 성공 - 포지션 기록 (청산 대기)
                open_positions[symbol] = {
                    'entry_time': timestamp,
                    'exit_time': signal['exit_time'],
                    'entry_price': signal['entry_price'],
                    'exit_price': signal['exit_price'],
                    'side': signal['side'],
                    'pnl': signal['pnl']
                }
                capital_used += self.config.capital_per_trade

            elif event['type'] == 'exit':
                symbol = event['symbol']
                timestamp = event['timestamp']

                # 포지션이 실제로 열려있는지 확인 (진입이 거부되었으면 청산도 없음)
                if symbol not in open_positions:
                    continue

                position = open_positions[symbol]

                # 거래 완료 기록
                executed_trades.append({
                    'symbol': symbol,
                    'entry_time': position['entry_time'],
                    'exit_time': timestamp,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': position['exit_price'],
                    'pnl': position['pnl']
                })

                # 포지션 닫기 및 자본 반환
                del open_positions[symbol]
                capital_used -= self.config.capital_per_trade

        return executed_trades, skipped_signals

    def _calculate_concurrent_stats(self, trades: List[dict]) -> dict:
        """동시 포지션 통계 계산

        Args:
            trades: 실행된 거래 리스트

        Returns:
            {'avg': 평균 동시 포지션, 'max': 최대 동시 포지션}
        """
        # 타임스탬프별 동시 포지션 수 계산
        time_positions = {}

        for trade in trades:
            entry = trade['entry_time']
            exit_t = trade['exit_time']

            # entry ~ exit 사이 모든 시점에 포지션 +1
            current = entry
            while current <= exit_t:
                if current not in time_positions:
                    time_positions[current] = 0
                time_positions[current] += 1
                current += pd.Timedelta(hours=1)

        if not time_positions:
            return {'avg': 0, 'max': 0}

        counts = list(time_positions.values())
        return {
            'avg': np.mean(counts),
            'max': max(counts)
        }

    def _calculate_symbol_stats(self, trades: List[dict]) -> Dict[str, dict]:
        """심볼별 통계 계산

        Args:
            trades: 실행된 거래 리스트

        Returns:
            심볼별 통계 딕셔너리
        """
        symbol_trades: Dict[str, List[dict]] = {}

        for trade in trades:
            symbol = trade['symbol']
            if symbol not in symbol_trades:
                symbol_trades[symbol] = []
            symbol_trades[symbol].append(trade)

        stats = {}
        for symbol, trades_list in symbol_trades.items():
            pnls = [t['pnl'] for t in trades_list]
            wins = [p for p in pnls if p > 0]

            stats[symbol] = {
                'total_trades': len(trades_list),
                'win_rate': len(wins) / len(trades_list) * 100 if trades_list else 0,
                'avg_pnl': np.mean(pnls) if pnls else 0,
                'total_pnl': sum(pnls)
            }

        return stats


def main():
    """테스트 실행"""
    from core.data_manager import BotDataManager
    from config.parameters import DEFAULT_PARAMS

    # 1. 데이터 로드 (3개 심볼)
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    data_cache = {}

    print("=" * 60)
    print("데이터 로드 중...")

    for symbol in symbols:
        try:
            dm = BotDataManager('bybit', symbol, {'entry_tf': '1h'})
            dm.load_historical()
            df = dm.df_entry_full

            if df is not None and len(df) >= 1000:
                data_cache[symbol] = df.copy()
                print(f"  ✅ {symbol}: {len(df):,}개 캔들")
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")

    if len(data_cache) < 2:
        print("❌ 데이터 부족")
        return

    # 2. 포트폴리오 백테스트 실행
    config = PortfolioConfig(
        initial_capital=10000.0,
        max_positions=3,
        capital_per_trade=3000.0
    )

    engine = PortfolioBacktestEngine(data_cache, config)
    result = engine.run_backtest(DEFAULT_PARAMS)

    # 3. 결과 출력
    if result:
        print("\n" + "=" * 60)
        print("📊 포트폴리오 백테스트 결과")
        print("=" * 60)
        print(f"실행된 거래:     {result.total_trades:,}개")
        print(f"건너뛴 신호:     {result.skipped_signals:,}개")
        print(f"신호 실행률:     {result.execution_rate:.1f}%")
        print(f"평균 동시 포지션: {result.avg_concurrent_positions:.1f}개")
        print(f"최대 동시 포지션: {result.max_concurrent_positions}개")
        print("-" * 60)
        print(f"승률:            {result.win_rate:.1f}%")
        print(f"MDD:             {result.mdd:.2f}%")
        print(f"Sharpe Ratio:    {result.sharpe_ratio:.2f}")
        print(f"총 수익:         {result.total_pnl:.2f}%")
        print(f"최종 자본:       ${result.final_capital:,.2f}")
        print("=" * 60)

        print("\n📈 심볼별 통계:")
        for symbol, stats in sorted(result.symbol_stats.items()):
            print(f"  {symbol:12s}: {stats['total_trades']:3d}회, "
                  f"승률 {stats['win_rate']:.1f}%, "
                  f"수익 {stats['total_pnl']:.2f}%")
    else:
        print("❌ 백테스트 실패")


if __name__ == '__main__':
    main()
