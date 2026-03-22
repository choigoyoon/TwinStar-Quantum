"""
SingleOptimizationWidget 이벤트 핸들러 Mixin

이벤트 처리 관련 메서드를 분리한 Mixin 클래스

v7.26 (2026-01-19): Phase 3 리팩토링 - 코드 복잡도 개선
"""

from PyQt6.QtWidgets import QMessageBox
from typing import TYPE_CHECKING, List, Dict, Any

from utils.logger import get_module_logger

if TYPE_CHECKING:
    from .single import SingleOptimizationWidget

logger = get_module_logger(__name__)


class SingleOptimizationEventHandlerMixin:
    """
    SingleOptimizationWidget 이벤트 핸들러 Mixin

    모든 UI 이벤트 핸들러 메서드를 제공합니다.
    """

    # Type hints for commonly used attributes
    worker: Any
    results: List[Dict[str, Any]]
    result_table: Any
    progress_bar: Any
    status_label: Any
    run_btn: Any
    stop_btn: Any
    best_params_selected: Any  # PyQt6 signal

    def _update_result_table(self, results: List[Dict[str, Any]]) -> None:
        """결과 테이블 업데이트 (single.py에서 구현)"""
        raise NotImplementedError("Must be implemented in SingleOptimizationWidget")

    def _on_run_optimization(self):
        """최적화 실행 (v7.26: 파라미터 적용 완료)"""
        # 실제 구현은 single.py에 유지
        # 이 Mixin은 시그니처만 정의
        pass

    def _on_stop_optimization(self):
        """최적화 중지"""
        logger.info("최적화 중지 요청")

        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.quit()
            self.worker.wait(3000)

        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText("❌ 최적화가 중지되었습니다.")
            self.status_label.setVisible(True)

    def _on_progress_update(self, completed: int, total: int):
        """진행 상황 업데이트 (v7.26: Track 2 & 3 완료)"""
        # 진행률 계산
        if total > 0:
            progress = int((completed / total) * 100)
        else:
            progress = 0

        # 진행 바 업데이트 (100% 중복 방지)
        if hasattr(self, 'progress_bar') and self.progress_bar:
            current_value = self.progress_bar.value()
            if progress != 100 or current_value != 100:
                self.progress_bar.setValue(progress)

        # 상태 라벨 업데이트
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(f"🔄 진행 상황: {completed}/{total} ({progress}%)")
            self.status_label.setVisible(True)

    def _on_optimization_finished(self, results: List[Dict[str, Any]]):
        """최적화 완료 처리 (v7.26: Track 2 & 3 완료)"""
        logger.info(f"최적화 완료: {len(results)}개 결과")

        # 결과 저장
        self.results = results

        # UI 상태 복원
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 진행 바 100% 표시 (완료 시 단 한 번만)
        if hasattr(self, 'progress_bar') and self.progress_bar:
            if self.progress_bar.value() != 100:
                self.progress_bar.setValue(100)

        # 상태 라벨 업데이트
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(f"✅ 최적화 완료: {len(results)}개 결과")
            self.status_label.setVisible(True)

        # 결과 테이블 업데이트
        self._update_result_table(results)

        # 완료 메시지
        QMessageBox.information(
            self,  # type: ignore
            "완료",
            f"최적화가 완료되었습니다.\n\n"
            f"총 {len(results)}개 파라미터 조합을 테스트했습니다."
        )

    def _on_optimization_error(self, error: str):
        """최적화 에러 처리"""
        logger.error(f"최적화 에러: {error}")

        # UI 상태 복원
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        # 에러 메시지 표시
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(f"❌ 에러: {error[:100]}")
            self.status_label.setVisible(True)

        QMessageBox.critical(
            self,  # type: ignore
            "오류",
            f"최적화 중 오류가 발생했습니다.\n\n{error}"
        )

    def _on_save_checked_presets(self):
        """체크된 프리셋 저장 (v7.26: 파라미터 적용 완료)"""
        # 실제 구현은 single.py에 유지
        pass

    def _on_apply_params(self):
        """선택한 파라미터 적용 (v7.26: Phase 1 구현 완료)"""
        selected_row = self.result_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "경고", "파라미터를 선택해주세요.")  # type: ignore
            return

        # 선택한 결과에서 파라미터 추출
        if selected_row >= len(self.results):
            QMessageBox.warning(self, "경고", "유효하지 않은 선택입니다.")  # type: ignore
            return

        result = self.results[selected_row]
        params = result.get('params', {})

        if not params:
            QMessageBox.warning(self, "경고", "파라미터 정보가 없습니다.")  # type: ignore
            return

        # 시그널 발신
        self.best_params_selected.emit(params)  # type: ignore

        logger.info(f"✅ 파라미터 적용: {params}")

        # 주요 파라미터 표시
        param_str = "\n".join([
            f"ATR 배수: {params.get('atr_mult', 'N/A')}",
            f"필터 TF: {params.get('filter_tf', 'N/A')}",
            f"트레일 시작: {params.get('trail_start_r', 'N/A')}",
            f"트레일 간격: {params.get('trail_dist_r', 'N/A')}",
            f"진입 유효시간: {params.get('entry_validity_hours', 'N/A')}h"
        ])

        QMessageBox.information(
            self,  # type: ignore
            "완료",
            f"파라미터가 적용되었습니다.\n\n{param_str}"
        )

    def _on_strategy_changed(self, index: int):
        """전략 변경 시 처리 (v7.26: Phase 1 구현 완료)"""
        strategy_type = 'macd' if index == 0 else 'adx'

        logger.info(f"✅ 전략 변경: {strategy_type}")

        # 전략 정보 표시
        strategy_info = {
            'macd': {
                'name': 'MACD',
                'params': 'macd_fast, macd_slow, macd_signal',
                'desc': '방향 + 강도 감지, 빠른 신호'
            },
            'adx': {
                'name': 'ADX-DI',
                'params': 'adx_period, adx_threshold, di_threshold',
                'desc': '추세 강도 감지, 느린 신호'
            }
        }

        info = strategy_info.get(strategy_type, {})
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(
                f"📊 전략: {info.get('name', strategy_type.upper())} "
                f"({info.get('desc', '')})"
            )

    def _on_mode_changed(self, index: int):
        """최적화 모드 변경 처리 (v7.26: Meta 모드 지원)"""
        # 실제 구현은 single.py에 유지
        pass

    def _on_sample_size_changed(self, value: int):
        """Meta Sample Size 변경 처리 (v7.21)"""
        # 실제 구현은 single.py에 유지
        pass


__all__ = ['SingleOptimizationEventHandlerMixin']
