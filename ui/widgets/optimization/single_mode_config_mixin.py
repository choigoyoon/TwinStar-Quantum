"""
SingleOptimizationWidget 모드 설정 Mixin

최적화 모드별 UI 설정 메서드를 분리한 Mixin 클래스

v7.26.8 (2026-01-19): Phase 4-5 - 모드 설정 Mixin 분리
"""

from PyQt6.QtWidgets import QVBoxLayout, QSlider, QLabel, QSpinBox
from typing import Any

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


class SingleOptimizationModeConfigMixin:
    """
    SingleOptimizationWidget 모드 설정 Mixin

    Fine-Tuning 및 Meta 모드 선택 시 UI 설정 메서드를 제공합니다.
    """

    # Type hints for attributes that will be provided by SingleOptimizationWidget
    meta_settings_layout: QVBoxLayout
    sample_size_slider: QSlider
    estimated_combo_label: QLabel
    estimated_time_label: QLabel
    recommended_workers_label: QLabel
    max_workers_spin: QSpinBox

    def _on_fine_tuning_mode_selected(self):
        """
        Fine-Tuning 모드 선택 시 UI 업데이트 (v7.25)

        Phase 1 영향도 분석 결과 (Baseline Sharpe 19.82) 주변을 촘촘하게 탐색.
        """
        from config.parameters import FINE_TUNING_RANGES

        # 1. Meta Sample Size 슬라이더 숨기기
        for i in range(self.meta_settings_layout.count()):
            item = self.meta_settings_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.hide()

        # 2. 예상 정보 업데이트
        total_combos = (
            len(FINE_TUNING_RANGES['filter_tf']) *
            len(FINE_TUNING_RANGES['trail_start_r']) *
            len(FINE_TUNING_RANGES['trail_dist_r'])
        )
        estimated_seconds = total_combos * 0.37  # 평균 0.37초/조합 (8워커 기준)
        time_minutes = estimated_seconds / 60

        self.estimated_combo_label.setText(f"예상 조합 수: {total_combos}개")
        self.estimated_time_label.setText(f"예상 시간: ~{time_minutes:.1f}분")
        self.recommended_workers_label.setText("권장 워커: 8개 (코어 100% 사용)")

        # 3. 워커 수 자동 설정 (최대 성능)
        import multiprocessing
        self.max_workers_spin.setValue(max(1, multiprocessing.cpu_count() - 1))

        # 4. Phase 1 Baseline 정보 표시
        baseline_info = (
            "[CHART] Phase 1 Baseline (Sharpe 19.82):\n"
            "- filter_tf='2h', trail_start_r=0.4, trail_dist_r=0.02\n"
            "- 640개 조합으로 최적값 주변 정밀 탐색"
        )
        logger.info(f"Fine-Tuning 모드 선택:\n{baseline_info}")

    def _on_meta_mode_selected(self):
        """
        메타 최적화 모드 선택 시 UI 업데이트 (v7.20 → v7.21)

        메타 최적화는 파라미터 범위를 자동으로 탐색하므로
        수동 범위 입력 필요 없음.

        v7.21: Sample Size 슬라이더 표시 추가
        """
        # 1. Sample Size 슬라이더 표시
        for i in range(self.meta_settings_layout.count()):
            item = self.meta_settings_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.show()

        # 2. 예상 정보 업데이트 (초기값: 2000)
        sample_size = self.sample_size_slider.value()
        total_samples = sample_size * 3
        estimated_seconds = total_samples * 0.02

        self.estimated_combo_label.setText(f"예상 조합 수: ~{total_samples:,}개 ({sample_size:,}개 × 3회 반복)")
        if estimated_seconds < 60:
            time_str = f"{estimated_seconds:.0f}초"
        else:
            time_str = f"{estimated_seconds/60:.1f}분"
        self.estimated_time_label.setText(f"예상 시간: {time_str}")
        self.recommended_workers_label.setText("권장 워커: 8개 (코어 100% 사용)")

        # 3. 워커 수 자동 설정 (최대 성능)
        import multiprocessing
        self.max_workers_spin.setValue(max(1, multiprocessing.cpu_count() - 1))

        # 4. 파라미터 위젯은 비활성화 (자동 탐색이므로 수동 입력 불필요)
        # 주의: 파라미터 위젯을 완전히 숨기면 오히려 사용자 혼란 가능
        # 따라서 힌트만 표시 (선택 사항)

        logger.info(f"메타 최적화 모드 선택: 파라미터 범위 자동 탐색 (sample_size={sample_size})")

    def _on_adaptive_mode_selected(self):
        """Adaptive 모드 선택 시 UI 업데이트 (v7.41)"""
        # 1. 예상 정보 업데이트
        total_combos = 360 # core/optimizer.py:generate_adaptive_grid 기준
        estimated_seconds = total_combos * 0.25  # 가변 로직 추가로 약간 증가 가능
        time_minutes = estimated_seconds / 60

        self.estimated_combo_label.setText(f"예상 조합 수: ~{total_combos}개")
        self.estimated_time_label.setText(f"예상 시간: ~{time_minutes:.1f}분")
        self.recommended_workers_label.setText("권장 워커: 8개 이상 (Deep 전용 엔진)")

        logger.info("Adaptive 모드 선택: 샘플링 탐색 (~360개)")

    def _on_deep_mode_selected(self):
        """Deep 모드 선택 시 UI 업데이트 (v7.41)"""
        # 1. 예상 정보 업데이트
        total_combos = 11520 # core/optimizer.py:generate_deep_grid 기준
        # 대략적인 시간 계산 (워커당 처리 속도 고려)
        estimated_seconds = total_combos * 0.1 # 멀티프로세싱 최적화 시
        time_minutes = estimated_seconds / 60

        self.estimated_combo_label.setText(f"예상 조합 수: {total_combos:,}개")
        self.estimated_time_label.setText(f"예상 시간: ~{time_minutes:.0f}분 (Deep)")
        self.recommended_workers_label.setText("권장 워커: 최대 가동 (전수 조사)")

        logger.info(f"Deep 모드 선택: 전수 조사 ({total_combos:,} 조합)")


__all__ = ['SingleOptimizationModeConfigMixin']
