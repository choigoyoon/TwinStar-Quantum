"""
tests/helpers/integration_utils.py

Phase A 통합 테스트 유틸리티 함수
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from config.parameters import DEFAULT_PARAMS

logger = logging.getLogger(__name__)


def generate_flash_crash_data(num_candles: int = 1000) -> pd.DataFrame:
    """
    Flash Crash 시뮬레이션 데이터 생성

    Args:
        num_candles: 생성할 캔들 수

    Returns:
        Flash Crash 포함 OHLCV 데이터
    """
    base_price = 50000.0
    timestamps = pd.date_range(start='2024-01-01', periods=num_candles, freq='15min')

    data = []
    for i, ts in enumerate(timestamps):
        # 일반 변동
        close = base_price + np.sin(i / 10) * 1000 + np.random.randn() * 100

        # Flash Crash 시뮬레이션 (캔들 500~520: -30% 급락 후 회복)
        if 500 <= i <= 520:
            crash_factor = -0.3 * (1 - abs(i - 510) / 10)  # 510에서 최대 급락
            close = close * (1 + crash_factor)

        high = close + abs(np.random.randn() * 50)
        low = close - abs(np.random.randn() * 50)
        open_ = (high + low) / 2
        volume = 1000 + np.random.randn() * 100

        data.append({
            'timestamp': ts,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    df = pd.DataFrame(data)
    logger.info(f"Flash Crash 데이터 생성 완료: {len(df)} candles")
    return df


def run_backtest_full(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    params: dict | None = None
) -> dict:
    """
    전체 데이터로 백테스트 실행

    Args:
        exchange: 거래소 이름
        symbol: 심볼
        params: 전략 파라미터 (None이면 DEFAULT_PARAMS 사용)

    Returns:
        백테스트 결과 딕셔너리
    """
    if params is None:
        params = DEFAULT_PARAMS.copy()

    try:
        # 데이터 로드
        manager = BotDataManager(exchange, symbol, cache_dir='data/cache')
        df = manager.get_full_history(with_indicators=True)

        if df is None or df.empty:
            logger.warning(f"데이터 없음: {exchange} {symbol}")
            return {'error': 'No data available'}

        # 백테스트 실행
        strategy = AlphaX7Core()
        # run_backtest는 df_pattern, df_entry 2개의 DataFrame을 받음
        results = strategy.run_backtest(
            df_pattern=df,
            df_entry=df,
            slippage=params.get('slippage', 0.001),
            atr_mult=params.get('atr_mult'),
            rsi_period=params.get('rsi_period'),
            macd_fast=params.get('macd_fast'),
            macd_slow=params.get('macd_slow'),
            macd_signal=params.get('macd_signal'),
            adx_period=params.get('adx_period'),
            adx_threshold=params.get('adx_threshold'),
            filter_tf=params.get('filter_tf')
        )

        logger.info(f"백테스트 완료: {results.get('total_trades', 0)} trades")
        return results

    except Exception as e:
        logger.error(f"백테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


def run_live_simulation(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    params: dict | None = None,
    num_steps: int = 500
) -> dict:
    """
    실시간 시뮬레이션 실행 (메모리 제한 환경)

    Args:
        exchange: 거래소 이름
        symbol: 심볼
        params: 전략 파라미터
        num_steps: 시뮬레이션 스텝 수

    Returns:
        시뮬레이션 결과 딕셔너리
    """
    if params is None:
        params = DEFAULT_PARAMS.copy()

    try:
        # 전체 데이터 로드
        manager = BotDataManager(exchange, symbol, cache_dir='data/cache')
        df_full = manager.get_full_history(with_indicators=False)

        if df_full is None or df_full.empty:
            logger.warning(f"데이터 없음: {exchange} {symbol}")
            return {'error': 'No data available'}

        # 지표 계산 (전체 데이터)
        from utils.indicators import add_all_indicators
        df_full = add_all_indicators(df_full)

        strategy = AlphaX7Core()
        trades = []
        signals = []

        # 실시간 시뮬레이션 (메모리 제한)
        start_idx = len(df_full) - num_steps
        for i in range(start_idx, len(df_full)):
            # 메모리 제한 시뮬레이션 (최근 1000개만)
            manager.df_entry_full = df_full.iloc[max(0, i-999):i+1].copy()

            # Phase A-2: 워밍업 윈도우 적용
            df_recent = manager.get_recent_data(limit=100, warmup_window=100)

            if df_recent is None or len(df_recent) < 50:
                continue

            # 신호 생성 (AlphaX7Core에는 check_signal 메서드가 없음)
            # TODO: 실시간 신호 생성 로직 구현 필요
            # signal = strategy.check_signal(df_recent, params)
            # signals.append(signal)
            pass

        # 메트릭 계산
        from utils.metrics import calculate_backtest_metrics

        # trades가 비어있는 경우 더미 데이터 생성
        if not trades:
            metrics = {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'profit_factor': 0.0,
                'mdd': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,
                'final_capital': 100.0
            }
        else:
            metrics = calculate_backtest_metrics(trades, leverage=params.get('leverage', 1), capital=100.0)

        metrics['total_signals'] = len(signals)
        metrics['signal_types'] = {}
        for sig in signals:
            if sig:
                sig_type = sig.type if hasattr(sig, 'type') else str(sig)
                metrics['signal_types'][sig_type] = metrics['signal_types'].get(sig_type, 0) + 1

        logger.info(f"실시간 시뮬레이션 완료: {len(signals)} signals")
        return metrics

    except Exception as e:
        logger.error(f"실시간 시뮬레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


def compare_metrics(results_bt: dict, results_live: dict, tolerances: dict | None = None) -> dict:
    """
    백테스트와 실시간 시뮬레이션 메트릭 비교

    Args:
        results_bt: 백테스트 결과
        results_live: 실시간 시뮬레이션 결과
        tolerances: 허용 오차 딕셔너리 (기본값: {'win_rate': 0.05, 'sharpe_ratio': 0.25, 'mdd': 0.03})

    Returns:
        비교 결과 딕셔너리
    """
    if tolerances is None:
        tolerances = {
            'win_rate': 0.05,       # 5%
            'sharpe_ratio': 0.25,   # 0.25 (Sharpe 10% 정도)
            'mdd': 0.03             # 3%
        }

    comparison = {
        'metrics': {},
        'passed': True,
        'failures': []
    }

    # 주요 메트릭 비교
    for metric, tolerance in tolerances.items():
        bt_value = results_bt.get(metric, 0.0)
        live_value = results_live.get(metric, 0.0)
        diff = abs(bt_value - live_value)

        passed = diff < tolerance
        comparison['metrics'][metric] = {
            'backtest': bt_value,
            'live': live_value,
            'diff': diff,
            'tolerance': tolerance,
            'passed': passed
        }

        if not passed:
            comparison['passed'] = False
            comparison['failures'].append(f"{metric}: diff={diff:.4f} > tolerance={tolerance:.4f}")

    return comparison


def check_parquet_exists(exchange: str, symbol: str, cache_dir: str = 'data/cache') -> tuple[bool, Path]:
    """
    Parquet 파일 존재 여부 확인

    Args:
        exchange: 거래소 이름
        symbol: 심볼
        cache_dir: 캐시 디렉토리

    Returns:
        (존재 여부, 파일 경로)
    """
    manager = BotDataManager(exchange, symbol, cache_dir=cache_dir)
    file_path = manager.get_entry_file_path()
    exists = file_path.exists()

    if exists:
        df = pd.read_parquet(file_path)
        logger.info(f"Parquet 파일 확인: {file_path.name} ({len(df)} candles)")
    else:
        logger.warning(f"Parquet 파일 없음: {file_path}")

    return exists, file_path
