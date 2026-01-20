"""
SingleOptimizationWidget Meta 최적화 핸들러 Mixin

Meta 최적화 관련 이벤트 핸들러를 분리한 Mixin 클래스

v7.26.7 (2026-01-19): Phase 4 작업 3 - Meta 핸들러 Mixin 분리
"""

from PyQt6.QtWidgets import QMessageBox, QProgressBar, QPushButton, QLabel, QWidget
from typing import Dict, Any, cast

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


class SingleOptimizationMetaHandlerMixin:
    """
    SingleOptimizationWidget Meta 최적화 핸들러 Mixin

    Meta 최적화 관련 이벤트 핸들러 메서드를 제공합니다.
    """

    # Type hints for attributes that will be provided by SingleOptimizationWidget
    progress_bar: QProgressBar
    status_label: QLabel
    run_btn: QPushButton
    stop_btn: QPushButton

    # Type hints for methods that will be provided by SingleOptimizationWidget
    def _save_meta_ranges(self, result: Dict[str, Any]) -> None: ...

    def _on_meta_progress(self, event: str, *args):
        """메타 최적화 진행 상황 콜백"""
        logger.debug(f"  Meta progress: {event} {args}")

    def _on_meta_iteration_started(self, iteration: int, sample_size: int):
        """메타 최적화 반복 시작"""
        logger.info(f"  Iteration {iteration} started: {sample_size} samples")
        self.status_label.setText(f"🔄 Iteration {iteration}/3: {sample_size}개 조합 테스트 중...")

    def _on_meta_backtest_progress(self, iteration: int, completed: int, total: int):
        """백테스트 진행 상황 업데이트"""
        # 전체 진행도 계산 (iteration별 가중치)
        base_progress = (iteration - 1) * 1000
        current_progress = base_progress + completed
        self.progress_bar.setValue(current_progress)

        # 상태 메시지 업데이트
        percentage = (completed / total * 100) if total > 0 else 0
        self.status_label.setText(
            f"🔄 Iteration {iteration}/3: {completed}/{total} 백테스트 완료 ({percentage:.1f}%)"
        )

    def _on_meta_iteration_finished(self, iteration: int, result_count: int, best_score: float):
        """메타 최적화 반복 완료"""
        logger.info(f"  Iteration {iteration} finished: {result_count} results, best score={best_score:.2f}")
        self.status_label.setText(
            f"✅ Iteration {iteration}/3 완료: {result_count}개 결과, 최고 점수={best_score:.2f}"
        )

    def _on_meta_finished(self, result: Dict[str, Any]):
        """메타 최적화 완료"""
        logger.info(f"✅ 메타 최적화 완료: {result['iterations']} iterations")

        # 1. UI 상태 복원
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 상태 메시지 업데이트
        statistics = result.get('statistics', {})
        elapsed = statistics.get('time_elapsed_seconds', 0)
        total_tested = statistics.get('total_combinations_tested', 0)
        self.status_label.setText(
            f"🎉 메타 최적화 완료! {total_tested:,}개 조합 테스트 (소요 시간: {elapsed:.1f}초)"
        )

        # 2. 결과 표시
        extracted_ranges = result.get('extracted_ranges', {})
        statistics = result.get('statistics', {})

        # 메시지 박스로 결과 요약 표시
        message = (
            f"🎉 메타 최적화 완료\n\n"
            f"반복 횟수: {result['iterations']}\n"
            f"총 조합 수: {statistics.get('total_combinations_tested', 0):,}개\n"
            f"소요 시간: {statistics.get('time_elapsed_seconds', 0):.1f}초\n"
            f"수렴 이유: {result['convergence_reason']}\n\n"
            f"추출된 범위:\n"
        )

        # 파라미터별 범위 표시 (Deep 모드 기준)
        for param, ranges in extracted_ranges.items():
            deep_range = ranges.get('deep', [])
            if isinstance(deep_range[0], str):
                message += f"  {param}: {', '.join(deep_range[:3])}\n"
            else:
                message += f"  {param}: [{deep_range[0]:.2f} ~ {deep_range[-1]:.2f}]\n"

        message += "\n추출된 범위를 저장하시겠습니까?"

        reply = QMessageBox.question(
            cast(QWidget, self),
            "메타 최적화 완료",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        # 3. 저장 여부 확인
        # CRITICAL #2: None 안전성 체크 (v7.27)
        if reply is not None and reply == QMessageBox.StandardButton.Yes:
            self._save_meta_ranges(result)

    def _on_meta_error(self, error_msg: str):
        """메타 최적화 에러"""
        logger.error(f"❌ 메타 최적화 에러: {error_msg}")

        # 1. UI 상태 복원
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 2. 에러 메시지 표시
        QMessageBox.critical(
            cast(QWidget, self),
            "메타 최적화 에러",
            f"메타 최적화 중 오류 발생:\n{error_msg}"
        )


__all__ = ['SingleOptimizationMetaHandlerMixin']
