"""
SingleOptimizationWidget 이벤트 핸들러 Mixin

일반 이벤트 핸들러 (최적화 진행, 결과 처리, UI 상태 변경)를 분리한 Mixin 클래스

v7.26.7 (2026-01-19): Phase 4 작업 2 - 이벤트 핸들러 Mixin 분리
"""

from PyQt6.QtWidgets import (
    QMessageBox, QProgressBar, QPushButton, QLabel,
    QTableWidget, QCheckBox, QComboBox, QWidget
)
from typing import Dict, Any, List, cast
from pathlib import Path

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


class SingleOptimizationEventsMixin:
    """
    SingleOptimizationWidget 이벤트 핸들러 Mixin

    일반 이벤트 핸들러 메서드를 제공합니다.
    (Meta 최적화 관련 핸들러는 single_meta_handler.py 참조)
    """

    # Type hints for attributes that will be provided by SingleOptimizationWidget
    progress_bar: QProgressBar
    run_btn: QPushButton
    stop_btn: QPushButton
    status_label: QLabel
    result_table: QTableWidget
    results: List[Dict[str, Any]]
    auto_save_checkbox: QCheckBox
    exchange_combo: QComboBox
    symbol_combo: QComboBox
    timeframe_combo: QComboBox
    strategy_combo: QComboBox
    mode_combo: QComboBox
    sample_size_value_label: QLabel
    sample_size_coverage_label: QLabel
    param_widgets: Dict[str, Any]

    # Type hints for methods that will be provided by SingleOptimizationWidget
    def _update_result_table(self, results: list) -> None: ...
    def _is_2d_grid(self, results: list) -> bool: ...
    def _show_2d_grid_heatmap(self, results: list) -> None: ...
    def _save_preset(self, result: Dict[str, Any]) -> None: ...
    def _show_heatmap(self, results: list) -> None: ...
    def _toggle_strategy_widgets(self, strategy_index: int) -> None: ...
    def _toggle_meta_slider(self, mode_index: int) -> None: ...

    def _on_progress_update(self, completed: int, total: int) -> None:
        """진행 상황 업데이트

        MEDIUM #7: 프로그레스 바 시각화 개선 (v7.27)
        """
        if total > 0:
            progress = int((completed / total) * 100)
            self.progress_bar.setValue(progress)
            # MEDIUM #7: "완료/전체 (백분율)" 형식으로 표시
            self.progress_bar.setFormat(f"{completed}/{total} ({progress}%)")
            logger.debug(f"진행: {completed}/{total} ({progress}%)")

    def _on_optimization_finished(self, results: list):
        """최적화 완료"""
        logger.info(f"최적화 완료: {len(results)}개 결과")

        # UI 상태 복원
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 결과 저장
        self.results = results

        # 결과 테이블 업데이트
        self._update_result_table(results)

        # ✅ Phase 4: 2D 그리드 자동 히트맵 표시
        if self._is_2d_grid(results):
            self._show_heatmap(results)
            logger.info("✅ 2D 그리드 감지, 히트맵 자동 표시")

        # ✅ Phase 4: 최적 결과 자동 저장
        auto_save_message = ""
        if self.auto_save_checkbox.isChecked() and results:
            try:
                # 최고 결과 (첫 번째 결과 = Sharpe 최고)
                best_result = results[0]

                # 프리셋 저장
                from utils.preset_storage import PresetStorage
                storage = PresetStorage()

                # 심볼/타임프레임 추출
                symbol = self.symbol_combo.currentText().replace('/', '')
                tf = self.timeframe_combo.currentText()
                exchange = self.exchange_combo.currentText().lower()

                # MODE_MAP은 single.py에 정의되어 있으므로 가져오기
                from .single import MODE_MAP
                strategy_type = 'macd' if self.strategy_combo.currentIndex() == 0 else 'adx'

                # 파라미터 및 메트릭 추출
                if isinstance(best_result, dict):
                    params = best_result.get('params', {})
                    optimization_result = {
                        'win_rate': best_result.get('win_rate', 0.0),
                        'mdd': best_result.get('mdd', 0.0),
                        'sharpe_ratio': best_result.get('sharpe_ratio', 0.0),
                        'profit_factor': best_result.get('profit_factor', 0.0),
                        'total_trades': best_result.get('total_trades', 0),
                        'total_pnl': best_result.get('simple_return', 0.0),
                    }
                else:
                    params = getattr(best_result, 'params', {})
                    optimization_result = {
                        'win_rate': getattr(best_result, 'win_rate', 0.0),
                        'mdd': getattr(best_result, 'max_drawdown', 0.0),
                        'sharpe_ratio': getattr(best_result, 'sharpe_ratio', 0.0),
                        'profit_factor': getattr(best_result, 'profit_factor', 0.0),
                        'total_trades': getattr(best_result, 'trade_count', 0),
                        'total_pnl': getattr(best_result, 'total_pnl', 0.0),
                    }

                # 저장
                mode = MODE_MAP.get(self.mode_combo.currentIndex(), 'quick')
                filepath = storage.save_preset(
                    symbol=symbol,
                    tf=tf,
                    params=params,
                    optimization_result=optimization_result,
                    mode=mode,
                    strategy_type=strategy_type,
                    exchange=exchange
                )

                logger.info(f"✅ 최적 프리셋 자동 저장 완료: {filepath}")
                # filepath 타입에 따라 파일명 추출
                if isinstance(filepath, Path):
                    filename = filepath.name
                elif isinstance(filepath, str):
                    filename = Path(filepath).name
                else:
                    filename = str(filepath)
                auto_save_message = f"\n\n✅ 최적 결과가 자동 저장되었습니다!\n파일: {filename}"

            except Exception as e:
                logger.error(f"❌ 자동 저장 실패: {e}")
                auto_save_message = f"\n\n⚠️ 자동 저장 실패: {str(e)}"

        # ✅ 프리셋 저장 안내
        QMessageBox.information(
            cast(QWidget, self),
            "완료",
            f"최적화 완료!\n"
            f"총 {len(results)}개 결과 (MDD ≤ 20%만 표시)\n\n"
            f"💾 저장할 결과를 체크한 후 '프리셋 저장' 버튼을 클릭하세요."
            f"{auto_save_message}"
        )

    def _on_optimization_error(self, error_msg: str):
        """최적화 에러"""
        logger.error(f"최적화 에러: {error_msg}")

        # UI 상태 복원
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        QMessageBox.critical(
            cast(QWidget, self),
            "오류",
            f"최적화 중 오류 발생:\n{error_msg}"
        )

    def _on_save_checked_presets(self):
        """체크된 항목만 프리셋으로 저장"""
        if not self.results:
            QMessageBox.warning(cast(QWidget, self), "경고", "저장할 결과가 없습니다.")
            return

        # 체크된 행 찾기
        checked_rows = []
        for row in range(self.result_table.rowCount()):
            checkbox_widget = self.result_table.cellWidget(row, 0)
            if checkbox_widget and hasattr(checkbox_widget, 'layout'):
                layout = checkbox_widget.layout()
                if layout and layout.count() > 0:
                    item = layout.itemAt(0)
                    if item is not None:
                        checkbox = item.widget()
                        if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                            checked_rows.append(row)

        if not checked_rows:
            QMessageBox.warning(cast(QWidget, self), "경고", "체크된 항목이 없습니다.")
            return

        # 저장 실행
        from utils.preset_storage import PresetStorage
        storage = PresetStorage()
        saved_count = 0

        for row in checked_rows:
            try:
                result = self.results[row]

                # 파라미터 추출
                if isinstance(result, dict):
                    params = result.get('params', {})
                    optimization_result = {
                        'win_rate': result.get('win_rate', 0.0),
                        'mdd': result.get('mdd', 0.0),
                        'sharpe_ratio': result.get('sharpe_ratio', 0.0),
                        'profit_factor': result.get('profit_factor', 0.0),
                        'total_trades': result.get('total_trades', 0),
                        'total_pnl': result.get('simple_return', 0.0),
                    }
                else:
                    params = getattr(result, 'params', {})
                    optimization_result = {
                        'win_rate': getattr(result, 'win_rate', 0.0),
                        'mdd': getattr(result, 'max_drawdown', 0.0),
                        'sharpe_ratio': getattr(result, 'sharpe_ratio', 0.0),
                        'profit_factor': getattr(result, 'profit_factor', 0.0),
                        'total_trades': getattr(result, 'trade_count', 0),
                        'total_pnl': getattr(result, 'total_pnl', 0.0),
                    }

                # 저장
                symbol = self.symbol_combo.currentText().replace('/', '')
                tf = self.timeframe_combo.currentText()
                exchange = self.exchange_combo.currentText().lower()
                strategy_type = 'macd' if self.strategy_combo.currentIndex() == 0 else 'adx'

                from .single import MODE_MAP
                mode = MODE_MAP.get(self.mode_combo.currentIndex(), 'quick')

                storage.save_preset(
                    symbol=symbol,
                    tf=tf,
                    params=params,
                    optimization_result=optimization_result,
                    mode=mode,
                    strategy_type=strategy_type,
                    exchange=exchange
                )
                saved_count += 1

            except Exception as e:
                logger.error(f"프리셋 저장 실패 (행 {row}): {e}")

        QMessageBox.information(
            cast(QWidget, self),
            "완료",
            f"{saved_count}개 프리셋이 저장되었습니다."
        )

    def _on_apply_params(self):
        """선택한 파라미터를 위젯에 적용"""
        selected = self.result_table.selectedItems()
        if not selected:
            QMessageBox.warning(cast(QWidget, self), "경고", "결과를 선택하세요.")
            return

        row = selected[0].row()
        if row >= len(self.results):
            return

        result = self.results[row]

        # 파라미터 추출
        if isinstance(result, dict):
            params = result.get('params', {})
        else:
            params = getattr(result, 'params', {})

        # 파라미터 위젯에 값 설정
        if hasattr(self, 'param_widgets'):
            for key, widget in self.param_widgets.items():
                if key in params:
                    widget.set_values([params[key]])

        QMessageBox.information(
            cast(QWidget, self),
            "완료",
            "파라미터가 적용되었습니다."
        )

    def _on_strategy_changed(self, index: int):
        """전략 선택 변경 시 MACD/ADX 위젯 표시/숨김"""
        # MACD 위젯: index == 0 (MACD W/M)
        # ADX 위젯: index == 1 (ADX-DI)

        # Strategy-specific widgets visibility
        self._toggle_strategy_widgets(strategy_index=index)

        logger.info(f"전략 변경: {'MACD W/M' if index == 0 else 'ADX-DI'}")

    def _on_mode_changed(self, index: int):
        """모드 선택 변경 시 Meta Sample Size 슬라이더 표시/숨김

        HIGH #4: 실행 중인 워커가 있으면 먼저 신호 연결 해제 (v7.27)
        """
        # Meta 모드: index == 0 (v7.25 기준)
        # Fine-Tuning 모드: index == 1

        # HIGH #4: 워커 실행 중 모드 변경 시 레이스 컨디션 방지 (v7.27)
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            logger.warning("⚠️ 최적화 실행 중 모드 변경 시도 - 워커 신호 연결 해제 중...")

            # 1. 신호 연결 해제 (TypeError는 이미 연결 해제된 경우)
            try:
                self.worker.finished.disconnect()
            except TypeError:
                pass

            try:
                self.worker.error.disconnect()
            except TypeError:
                pass

            try:
                self.worker.progress.disconnect()
            except TypeError:
                pass

            # 2. 워커 중지 요청
            self.worker.quit()
            self.worker.wait(3000)  # 3초 대기

            # 3. 참조 해제
            self.worker = None

            logger.info("✅ 워커 신호 연결 해제 완료")

        self._toggle_meta_slider(mode_index=index)

        from .single import MODE_MAP
        mode = MODE_MAP.get(index, 'unknown')
        logger.info(f"모드 변경: {mode}")

    def _on_sample_size_changed(self, value: int):
        """Meta Sample Size 슬라이더 값 변경"""
        # 값 업데이트
        self.sample_size_value_label.setText(f"{value:,}")

        # 커버율 계산 (26,950개 전체 조합 기준)
        TOTAL_COMBINATIONS = 26950
        coverage = (value / TOTAL_COMBINATIONS) * 100

        # 예상 시간 계산 (조합당 ~0.01초)
        estimated_seconds = value * 0.01
        estimated_minutes = estimated_seconds / 60

        # 정보 업데이트
        info_text = (
            f"예상 조합 수: ~{value * 3:,}개 ({value:,}개 × 3회)\n"
            f"예상 시간: {estimated_minutes:.1f}분\n"
            f"커버율: {coverage:.1f}% / {TOTAL_COMBINATIONS:,}개"
        )
        self.sample_size_coverage_label.setText(info_text)

        logger.debug(f"Meta 샘플 크기 변경: {value} (커버율 {coverage:.1f}%)")


__all__ = ['SingleOptimizationEventsMixin']
