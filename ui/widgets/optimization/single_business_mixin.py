"""
SingleOptimizationWidget 비즈니스 로직 Mixin

최적화 실행 및 프리셋 저장 관련 비즈니스 로직을 분리한 Mixin 클래스

v7.26.8 (2026-01-19): Phase 4-3 - 비즈니스 로직 Mixin 분리
"""

from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QComboBox, QSpinBox,
    QPushButton, QLabel, QProgressBar, QSlider
)
from typing import Dict, Any, Optional, cast

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


class SingleOptimizationBusinessMixin:
    """
    SingleOptimizationWidget 비즈니스 로직 Mixin

    최적화 실행, 프리셋 저장, Meta 범위 저장 등 비즈니스 로직 메서드를 제공합니다.
    """

    # Type hints for attributes that will be provided by SingleOptimizationWidget
    exchange_combo: QComboBox
    symbol_combo: QComboBox
    timeframe_combo: QComboBox
    strategy_combo: QComboBox
    mode_combo: QComboBox
    sample_size_slider: QSlider
    max_workers_spin: QSpinBox
    run_btn: QPushButton
    stop_btn: QPushButton
    status_label: QLabel
    progress_bar: QProgressBar
    worker: Optional[Any]  # OptimizationWorker
    meta_worker: Optional[Any]  # MetaOptimizationWorker

    # Type hints for methods that will be provided by other classes
    def _on_progress_update(self, completed: int, total: int) -> None: ...
    def _on_optimization_finished(self, results: list) -> None: ...
    def _on_optimization_error(self, error_msg: str) -> None: ...
    def _on_meta_progress(self, event: str, *args) -> None: ...
    def _on_meta_iteration_started(self, iteration: int, sample_size: int) -> None: ...
    def _on_meta_iteration_finished(self, iteration: int, result_count: int, best_score: float) -> None: ...
    def _on_meta_backtest_progress(self, iteration: int, completed: int, total: int) -> None: ...
    def _on_meta_finished(self, result: Dict[str, Any]) -> None: ...
    def _on_meta_error(self, error_msg: str) -> None: ...

    def _run_fine_tuning(self, exchange: str, symbol: str, timeframe: str, max_workers: int):
        """
        Fine-Tuning 최적화 실행 (v7.25)

        Phase 1 영향도 분석 결과를 기반으로 640개 조합 정밀 탐색.
        Baseline: filter_tf='2h', trail_start_r=0.4, trail_dist_r=0.02 (Sharpe 19.82)

        Args:
            exchange: 거래소명
            symbol: 심볼명
            timeframe: 타임프레임
            max_workers: 병렬 워커 수
        """
        from config.parameters import FINE_TUNING_RANGES
        from core.data_manager import BotDataManager
        from core.optimization_logic import OptimizationEngine
        from .worker import OptimizationWorker

        logger.info(f"🎯 Fine-Tuning 시작: {exchange} {symbol} {timeframe} (640개 조합)")

        # 1. 데이터 로드
        try:
            dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})
            df_full = dm.get_full_history(with_indicators=False)

            if df_full is None or df_full.empty:
                QMessageBox.warning(cast(QWidget, self), "오류", "데이터가 비어있습니다.\nParquet 파일을 확인하세요.")
                return

            logger.info(f"데이터 로드 완료: {len(df_full):,}개 캔들")
        except Exception as e:
            QMessageBox.critical(cast(QWidget, self), "오류", f"데이터 로드 중 에러:\n{str(e)}")
            logger.error(f"데이터 로드 실패: {e}")
            return

        # 2. Fine-Tuning 파라미터 그리드 생성
        engine = OptimizationEngine()
        grid_options = {
            'filter_tf': FINE_TUNING_RANGES['filter_tf'],
            'trail_start_r': FINE_TUNING_RANGES['trail_start_r'],
            'trail_dist_r': FINE_TUNING_RANGES['trail_dist_r']
        }
        grid = engine.generate_grid_from_options(grid_options)

        logger.info(f"Fine-Tuning 그리드 생성: {len(grid):,}개 조합")

        # 3. 전략 타입
        strategy_index = self.strategy_combo.currentIndex()
        strategy_type = 'macd' if strategy_index == 0 else 'adx'

        # 4. Worker 생성 및 시그널 연결
        self.worker = OptimizationWorker(
            engine=engine,
            df=df_full,
            param_grid=grid,
            max_workers=max_workers,
            symbol=symbol,
            timeframe=timeframe,
            capital_mode='compound',
            strategy_type=strategy_type
        )

        self.worker.progress.connect(self._on_progress_update)
        self.worker.finished.connect(self._on_optimization_finished)
        self.worker.error.connect(self._on_optimization_error)

        # 5. UI 상태 변경 및 시작
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(grid))
        self.status_label.setVisible(True)
        self.status_label.setText(f"🎯 Fine-Tuning: 0/{len(grid):,} 완료")

        self.worker.start()
        logger.info("OptimizationWorker 시작 (Fine-Tuning)")

    # ❌ DEPRECATED (v7.28): Meta 최적화 - Fine-Tuning이 최고 성능으로 대체
    # 재활성화 필요 시: dev_future/optimization_modes/README.md 참조
    #
    # def _run_meta_optimization(self, exchange: str, symbol: str, timeframe: str):
    #     """메타 최적화 실행 (DEPRECATED)"""
    #     pass
    #
    # def _save_meta_ranges(self, result: Dict[str, Any]):
    #     """메타 범위 저장 (DEPRECATED)"""
    #     pass

    def _save_as_preset(self, result) -> bool:
        """최고 성능 결과를 프리셋으로 저장 (v7.26: 딕셔너리 구조 지원)

        Args:
            result: 결과 딕셔너리 또는 OptimizationResult 객체 (최고 성능)

        Returns:
            bool: 저장 성공 여부
        """
        try:
            from utils.preset_storage import PresetStorage
            from .single import MODE_MAP

            # v7.26: presets/coarse_fine 경로 사용 (CLI 스크립트와 통일)
            storage = PresetStorage(base_path='presets/coarse_fine')

            # UI에서 설정값 추출
            exchange = self.exchange_combo.currentText().lower()
            symbol = self.symbol_combo.currentText()
            tf = self.timeframe_combo.currentText()
            strategy = 'macd' if self.strategy_combo.currentIndex() == 0 else 'adx'

            # 모드 추출 (v7.25 MODE_MAP 기반)
            mode_index = self.mode_combo.currentIndex()
            mode = MODE_MAP.get(mode_index, 'fine')

            # v7.26: 딕셔너리와 객체 모두 지원
            if isinstance(result, dict):
                # Worker에서 반환한 딕셔너리 구조
                params = result.get('params', {})
                metrics = {
                    'win_rate': result.get('win_rate', 0.0),
                    'mdd': result.get('mdd', 0.0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0.0),
                    'profit_factor': result.get('pf', 0.0),
                    'total_trades': result.get('total_trades', 0),
                    'total_pnl': result.get('simple_return', 0.0),
                    'compound_return': result.get('compound_return', 0.0),
                    'avg_pnl': result.get('avg_pnl', 0.0),
                    'safe_leverage': result.get('safe_leverage', 0.0),
                    'avg_trades_per_day': 0.0,
                    'grade': result.get('grade', 'F')
                }
            else:
                # 레거시: OptimizationResult 객체
                params = {
                    'atr_mult': getattr(result, 'atr_mult', 1.5),
                    'filter_tf': getattr(result, 'filter_tf', '4h'),
                    'trail_start_r': getattr(result, 'trail_start_r', 1.0),
                    'trail_dist_r': getattr(result, 'trail_dist_r', 0.03),
                    'entry_validity_hours': getattr(result, 'entry_validity_hours', 6.0),
                    'leverage': getattr(result, 'leverage', 1),
                    'macd_fast': 6,
                    'macd_slow': 18,
                    'macd_signal': 7
                }

                total_trades = getattr(result, 'trade_count', 0)
                total_pnl = getattr(result, 'total_pnl', 0.0)

                metrics = {
                    'win_rate': getattr(result, 'win_rate', 0.0),
                    'mdd': getattr(result, 'max_drawdown', 0.0),
                    'sharpe_ratio': getattr(result, 'sharpe_ratio', 0.0),
                    'profit_factor': getattr(result, 'profit_factor', 0.0),
                    'total_trades': total_trades,
                    'total_pnl': total_pnl,
                    'compound_return': getattr(result, 'compound_return', total_pnl),
                    'avg_pnl': (total_pnl / total_trades if total_trades > 0 else 0.0),
                    'avg_trades_per_day': 0.0,
                    'grade': self._calculate_grade(getattr(result, 'sharpe_ratio', 0.0))
                }

            # 프리셋 저장
            success = storage.save_preset(
                symbol=symbol,
                tf=tf,
                params=params,
                optimization_result=metrics,
                mode=mode,
                strategy_type=strategy,
                exchange=exchange
            )

            if success:
                logger.info(f"✅ 프리셋 저장 완료: {exchange} {symbol} {tf} ({mode})")
                logger.info(f"   Sharpe: {metrics['sharpe_ratio']:.2f}, 승률: {metrics['win_rate']:.2f}%")
                return True
            else:
                logger.error(f"❌ 프리셋 저장 실패: {exchange} {symbol} {tf}")
                return False

        except Exception as e:
            logger.error(f"프리셋 저장 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _calculate_grade(self, sharpe: float) -> str:
        """Sharpe Ratio 기반 등급 계산

        Args:
            sharpe: Sharpe Ratio 값

        Returns:
            str: 등급 ('S', 'A', 'B', 'C', 'D', 'F')
        """
        if sharpe >= 25:
            return 'S'
        elif sharpe >= 20:
            return 'A'
        elif sharpe >= 15:
            return 'B'
        elif sharpe >= 10:
            return 'C'
        elif sharpe >= 5:
            return 'D'
        else:
            return 'F'


__all__ = ['SingleOptimizationBusinessMixin']
