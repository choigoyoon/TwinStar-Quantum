"""
백테스트 실행 워커 (QThread)

백그라운드에서 백테스트를 실행하는 워커 스레드
"""

from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd
from typing import Dict, Any, Optional, List
from utils.logger import get_module_logger

# SSOT imports
from core.optimizer import OptimizationResult
from utils.metrics import (
    calculate_mdd,
    calculate_win_rate,
    calculate_sharpe_ratio,
    calculate_profit_factor,
    calculate_stability,
    calculate_cagr,
    assign_grade_by_preset
)
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
        self.result_stats: Optional[OptimizationResult] = None

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
            self.progress.emit(80)

            # [Phase 1] 방향(Direction) 추가 필터링 (일치성 강화)
            direction = self.direction
            if direction != 'Both':
                self.trades_detail = [t for t in self.trades_detail if t['type'] == direction]
            
            self.progress.emit(85)

            # [Phase 1] 최소 거래 횟수 검증 (최적화 엔진과 동일 기준)
            if len(self.trades_detail) < 3:
                raise ValueError(f"거래 횟수 부족으로 통계 산출 불가 (최소 3회, 현재: {len(self.trades_detail)}회)")

            # Step 8: 결과 통계 계산 (SSOT 통합)
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
        """결과 통계 계산 (utils.metrics SSOT 통합)"""
        if not self.trades_detail:
            # 빈 결과 처리
            self.result_stats = OptimizationResult(
                params=self.strategy_params,
                trades=0,
                win_rate=0,
                total_return=0,
                simple_return=0,
                compound_return=0,
                max_drawdown=0,
                sharpe_ratio=0,
                profit_factor=0,
                avg_trades_per_day=0,
                stability="⚠️",
                grade="F",
                passes_filter=False
            )
            return

        trades = self.trades_detail
        leverage = self.leverage

        # 1. PnL 리스트 및 레버리지 적용 (메트릭 계산 전 수행)
        # 최적화 엔진과 동일하게 레버리지가 적용된 개별 PnL을 기반으로 계산함
        # [FIX] 단일 거래 PnL 클램핑 (±50%) - 최적화 엔진과 동일한 로직
        MAX_SINGLE_PNL = 50.0  # 단일 거래 최대 수익률 상한
        MIN_SINGLE_PNL = -50.0  # 단일 거래 최대 손실률 하한

        leveraged_trades = []
        for t in trades:
            raw_pnl = t.get('pnl', 0) * leverage
            # PnL 클램핑 적용 (오버플로우 방지)
            clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, raw_pnl))
            leveraged_trades.append({**t, 'pnl': clamped_pnl})

        pnls = [t['pnl'] for t in leveraged_trades]
        
        # Simple Return
        simple_return = sum(pnls)

        # 2. SSOT 메트릭 계산 호출
        win_rate = calculate_win_rate(leveraged_trades)      # Expects List[Dict]
        mdd = calculate_mdd(leveraged_trades)               # Expects List[Dict]
        sharpe = calculate_sharpe_ratio(pnls)               # Expects List[float]
        pf = calculate_profit_factor(leveraged_trades)      # Expects List[Dict]
        stability = calculate_stability(pnls)               # Expects List[float]
        
        # Compound Return (최적화 엔진과 동일한 로직)
        equity = 1.0
        cumulative_equity = [1.0]
        for p in pnls:
            equity *= (1 + p / 100)
            if equity <= 0:
                equity = 0
            cumulative_equity.append(equity)
            if equity == 0:
                break
        compound_return = (equity - 1) * 100
        compound_return = max(-100.0, min(compound_return, 1e10))  # 범위 제한: -100% ~ 1e10%

        # CAGR (연간 환산 수익률)
        # 데이터 기간 계산
        if self.df_15m is not None and len(self.df_15m) > 1:
            start_time = self.df_15m['timestamp'].iloc[0]
            end_time = self.df_15m['timestamp'].iloc[-1]
            if isinstance(start_time, (int, float)):
                duration_days = (end_time - start_time) / (1000 * 60 * 60 * 24)
            else:
                duration_days = (end_time - start_time).total_seconds() / (60 * 60 * 24)
            
            cagr = calculate_cagr(leveraged_trades, 100 + compound_return)
            avg_trades_per_day = len(trades) / duration_days if duration_days > 0 else 0
        else:
            cagr = 0
            avg_trades_per_day = 0

        # 3. 등급 할당 (균형 프리셋 기준)
        grade = assign_grade_by_preset(
            preset_type='balanced',
            metrics={
                'win_rate': win_rate,
                'profit_factor': pf,
                'mdd': mdd,
                'sharpe_ratio': sharpe,
                'compound_return': compound_return
            }
        )

        # 4. 필터 통과 여부 검증 (최적화 엔진 기준)
        # MDD <= 20%, 승률 >= 75%, 최소 거래 >= 10
        passes = (mdd <= 20.0 and win_rate >= 75.0 and len(trades) >= 10)

        # 5. OptimizationResult 객체 생성
        initial_cap = getattr(self.strategy, 'initial_capital', 100.0)
        final_cap = initial_cap * (equity) if equity > 0 else 0.0

        self.result_stats = OptimizationResult(
            params=self.strategy_params,
            trades=len(trades),
            win_rate=win_rate,
            total_return=compound_return,
            simple_return=simple_return,
            compound_return=compound_return,
            max_drawdown=mdd,
            sharpe_ratio=sharpe,
            profit_factor=pf,
            avg_trades_per_day=avg_trades_per_day,
            stability=stability,
            grade=grade,
            avg_pnl=simple_return / len(trades) if trades else 0,
            cagr=cagr,
            passes_filter=passes,
            symbol=getattr(self.strategy, 'symbol', ''),
            timeframe=getattr(self.strategy, 'timeframe', ''),
            final_capital=final_cap
        )

        logger.info(f"📊 [Phase 1 SSOT] 통계: {self.result_stats.trades}건, "
                   f"수수률: {self.result_stats.compound_return:.2f}%, "
                   f"승률: {self.result_stats.win_rate:.1f}%, "
                   f"MDD: {self.result_stats.max_drawdown:.1f}%, "
                   f"PF: {self.result_stats.profit_factor:.2f}, "
                   f"Pass: {self.result_stats.passes_filter}")
