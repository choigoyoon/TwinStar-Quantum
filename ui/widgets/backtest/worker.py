"""
백테스트 실행 워커 (QThread)

백그라운드에서 백테스트를 실행하는 워커 스레드
"""

from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd
from typing import Dict, Any, Optional, List
from utils.logger import get_module_logger

# SSOT imports
try:
    from config.constants import TF_RESAMPLE_MAP
except ImportError:
    TF_RESAMPLE_MAP = {
        '15m': '15T',
        '1h': '1H',
        '4h': '4H',
        '1d': '1D'
    }

try:
    from config.parameters import DEFAULT_PARAMS
except ImportError:
    DEFAULT_PARAMS = {}

logger = get_module_logger(__name__)


class BacktestWorker(QThread):
    """
    백테스트 실행 워커 (QThread)

    백그라운드에서 백테스트를 실행하고 결과를 메인 스레드로 전달합니다.

    Signals:
        progress(int): 진행률 (0-100)
        finished(): 백테스트 완료
        error(str): 에러 발생

    Attributes:
        trades_detail (List[Dict]): 거래 상세 내역
        audit_logs (List[Dict]): 로직 감사 로그
        df_15m (pd.DataFrame): 15분봉 데이터
        result_stats (Dict): 백테스트 결과 통계

    Example:
        worker = BacktestWorker(
            strategy=strategy_instance,
            slippage=0.0005,
            fee=0.0005,
            leverage=1
        )
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.start()
    """

    # Signals
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self,
        strategy: Any,  # AlphaX7Core or similar
        slippage: float,
        fee: float,
        leverage: int,
        strategy_params: Optional[Dict[str, Any]] = None,
        use_pyramiding: bool = False,
        direction: str = 'Both'
    ):
        """
        Args:
            strategy: 전략 인스턴스 (AlphaX7Core 등)
            slippage: 슬리피지 (소수)
            fee: 수수료율 (소수)
            leverage: 레버리지 (정수)
            strategy_params: 전략 파라미터 (기본값: None)
            use_pyramiding: 피라미딩 활성화 (기본값: False)
            direction: 거래 방향 ('Both', 'Long', 'Short')
        """
        super().__init__()

        # 전략 및 설정
        self.strategy = strategy
        self.slippage = slippage
        self.fee = fee
        self.leverage = leverage
        self.strategy_params = strategy_params or {}
        self.use_pyramiding = use_pyramiding
        self.direction = direction

        # 결과 저장
        self.trades_detail: List[Dict[str, Any]] = []
        self.audit_logs: List[Dict[str, Any]] = []
        self.df_15m: Optional[pd.DataFrame] = None
        self.result_stats: Optional[Dict[str, Any]] = None

    def run(self):
        """백테스트 실행 (QThread.run() override)"""
        try:
            logger.info("=== 백테스트 시작 ===")
            self.progress.emit(10)

            # Step 1: 데이터 로드
            self._load_data()
            self.progress.emit(30)

            # Step 2: 파라미터 병합
            params = self._merge_parameters()
            logger.info(f"파라미터: tolerance={params.get('pattern_tolerance')}, "
                       f"validity={params.get('entry_validity_hours')}h")

            # Step 3: 데이터 검증
            if self.df_15m is None or self.df_15m.empty:
                raise ValueError("백테스트 데이터가 없습니다")

            df_entry = self.df_15m.copy()

            # Step 4: 타임스탬프 변환
            df_entry = self._convert_timestamps(df_entry)

            # Step 5: 패턴 데이터 생성 (리샘플링)
            df_pattern = self._create_pattern_data(df_entry, params)
            self.progress.emit(50)

            # Step 6: 지표 추가
            df_pattern = self._add_indicators(df_pattern)

            # Step 7: 백테스트 실행
            self._run_backtest_core(df_pattern, df_entry, params)
            self.progress.emit(90)

            # Step 8: 결과 통계 계산
            self._calculate_stats()

            logger.info(f"=== 백테스트 완료: {len(self.trades_detail)} trades ===")
            self.progress.emit(100)
            self.finished.emit()

        except Exception as e:
            import traceback
            error_msg = f"백테스트 오류: {e}"
            logger.error(error_msg)
            traceback.print_exc()
            self.error.emit(str(e))

    def _load_data(self):
        """데이터 로드"""
        self.df_15m = getattr(self.strategy, 'df_15m', None)
        if self.df_15m is not None:
            logger.info(f"데이터 로드 완료: {len(self.df_15m)} rows")

    def _merge_parameters(self) -> Dict[str, Any]:
        """기본 파라미터와 사용자 파라미터 병합

        Returns:
            병합된 파라미터 딕셔너리
        """
        params = {
            'atr_mult': DEFAULT_PARAMS.get('atr_mult', 1.5),
            'trail_start_r': DEFAULT_PARAMS.get('trail_start_r', 0.8),
            'trail_dist_r': DEFAULT_PARAMS.get('trail_dist_r', 0.5),
            'pattern_tolerance': DEFAULT_PARAMS.get('pattern_tolerance', 0.03),
            'entry_validity_hours': DEFAULT_PARAMS.get('entry_validity_hours', 12.0),
            'pullback_rsi_long': DEFAULT_PARAMS.get('pullback_rsi_long', 40),
            'pullback_rsi_short': DEFAULT_PARAMS.get('pullback_rsi_short', 60),
            'max_adds': DEFAULT_PARAMS.get('max_adds', 1),
            'rsi_period': DEFAULT_PARAMS.get('rsi_period', 14),
            'atr_period': DEFAULT_PARAMS.get('atr_period', 14),
            'trend_interval': DEFAULT_PARAMS.get('trend_interval', '1h'),
            'filter_tf': DEFAULT_PARAMS.get('filter_tf', '4h'),
            'macd_fast': DEFAULT_PARAMS.get('macd_fast', 12),
            'macd_slow': DEFAULT_PARAMS.get('macd_slow', 26),
            'macd_signal': DEFAULT_PARAMS.get('macd_signal', 9),
            'ema_period': DEFAULT_PARAMS.get('ema_period', 200),
        }

        # 사용자 파라미터로 덮어쓰기
        params.update(self.strategy_params)

        return params

    def _convert_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """타임스탬프 컬럼을 datetime으로 변환

        Args:
            df: 입력 데이터프레임

        Returns:
            타임스탬프가 변환된 데이터프레임
        """
        if 'timestamp' not in df.columns:
            return df

        # 이미 datetime 타입이면 반환
        if pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            return df

        # 숫자형 (밀리초 타임스탬프)
        if pd.api.types.is_numeric_dtype(df['timestamp']):
            if df['timestamp'].iloc[0] > 1e12:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            else:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        else:
            # 문자열
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        logger.info(f"타임스탬프 변환 완료: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        return df

    def _create_pattern_data(
        self,
        df_entry: pd.DataFrame,
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """패턴 데이터 생성 (리샘플링)

        Args:
            df_entry: 15분봉 데이터
            params: 파라미터 (trend_interval 포함)

        Returns:
            리샘플링된 패턴 데이터
        """
        trend_tf: str = params.get('trend_interval', '1h') or '1h'  # None 방지
        rule: str = TF_RESAMPLE_MAP.get(trend_tf, '1H')  # 기본값 '1H'

        df_temp = df_entry.copy()

        # 타임스탬프 변환
        if not pd.api.types.is_datetime64_any_dtype(df_temp['timestamp']):
            if pd.api.types.is_numeric_dtype(df_temp['timestamp']):
                df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'], unit='ms')
            else:
                df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'])

        # 리샘플링
        df_temp = df_temp.set_index('timestamp')
        df_pattern = df_temp.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()

        logger.info(f"패턴 데이터 생성 완료: {len(df_pattern)} rows ({trend_tf})")
        return df_pattern

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """지표 추가

        Args:
            df: 입력 데이터프레임

        Returns:
            지표가 추가된 데이터프레임
        """
        try:
            from utils.indicators import IndicatorGenerator
            df = IndicatorGenerator.add_all_indicators(df)
            logger.info("지표 추가 완료")
        except Exception as e:
            logger.warning(f"지표 계산 실패 (계속 진행): {e}")

        return df

    def _run_backtest_core(
        self,
        df_pattern: pd.DataFrame,
        df_entry: pd.DataFrame,
        params: Dict[str, Any]
    ):
        """백테스트 실행 (핵심 로직)

        Args:
            df_pattern: 패턴 데이터
            df_entry: 진입 데이터
            params: 파라미터
        """
        # 슬리피지 + 수수료 합산
        combined_slippage = self.slippage + self.fee

        # 전략의 run_backtest 호출
        result, audit_logs = self.strategy.run_backtest(
            df_pattern=df_pattern,
            df_entry=df_entry,
            slippage=combined_slippage,
            atr_mult=params.get('atr_mult'),
            trail_start_r=params.get('trail_start_r'),
            trail_dist_r=params.get('trail_dist_r'),
            pattern_tolerance=params.get('pattern_tolerance'),
            entry_validity_hours=params.get('entry_validity_hours'),
            pullback_rsi_long=params.get('pullback_rsi_long'),
            pullback_rsi_short=params.get('pullback_rsi_short'),
            max_adds=params.get('max_adds'),
            rsi_period=params.get('rsi_period'),
            atr_period=params.get('atr_period'),
            filter_tf=params.get('filter_tf'),
            enable_pullback=self.use_pyramiding,
            allowed_direction=self.direction,
            macd_fast=params.get('macd_fast'),
            macd_slow=params.get('macd_slow'),
            macd_signal=params.get('macd_signal'),
            ema_period=params.get('ema_period'),
            collect_audit=True
        )

        self.trades_detail = result or []
        self.audit_logs = audit_logs or []

        logger.info(f"백테스트 실행 완료: {len(self.trades_detail)} trades")

    def _calculate_stats(self):
        """결과 통계 계산"""
        if not self.trades_detail:
            self.result_stats = {
                'count': 0,
                'simple_return': 0,
                'compound_return': 0,
                'total_return': 0,
                'win_rate': 0,
                'mdd': 0,
                'leverage': self.leverage,
            }
            return

        result = self.trades_detail
        leverage = self.leverage

        # PnL 리스트 (레버리지 적용)
        pnls = [t.get('pnl', 0) * leverage for t in result]

        # Simple Return
        simple_return = sum(pnls)

        # Compound Return (파산 안전 처리)
        equity = 1.0
        cumulative = [1.0]
        for p in pnls:
            equity *= (1 + p / 100)
            if equity <= 0:  # 파산
                equity = 0
                cumulative.append(0)
                break
            cumulative.append(equity)

        compound_return = (equity - 1) * 100
        compound_return = max(-100.0, min(compound_return, 999999))  # 범위 제한

        # MDD 계산 (파산 안전 처리)
        peak = 1.0
        mdd = 0
        for c in cumulative:
            if c <= 0:  # 파산 시 MDD = 100%
                mdd = 100.0
                break
            if c > peak:
                peak = c
            drawdown = (peak - c) / peak * 100
            if drawdown > mdd:
                mdd = drawdown

        # 승률 (raw_pnl 기준 - 수수료 무관)
        win_count = len([t for t in result if t.get('raw_pnl', t.get('pnl', 0)) > 0])
        win_rate = (win_count / len(result)) * 100 if result else 0

        self.result_stats = {
            'count': len(result),
            'simple_return': simple_return,
            'compound_return': compound_return,
            'total_return': compound_return,
            'win_rate': win_rate,
            'mdd': mdd,
            'leverage': leverage,
        }

        logger.info(f"통계: {self.result_stats['count']}건, "
                   f"수익률: {self.result_stats['compound_return']:.2f}%, "
                   f"승률: {self.result_stats['win_rate']:.1f}%, "
                   f"MDD: {self.result_stats['mdd']:.1f}%")
