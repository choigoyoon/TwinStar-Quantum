"""
TwinStar Quantum - Modern UI Main Window (v7.26)

통합 메인 윈도우 (신규 디자인 시스템 기반)
- 백테스트 위젯 (Phase 2 완료)
- 최적화 위젯 (Phase 4-6 완료)
- 대시보드 (향후 확장)
"""

import sys
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QSize

# 디자인 시스템
from ui.design_system.tokens import Colors, Typography, Spacing, Size
from ui.design_system.theme import ThemeGenerator

# 위젯
from ui.widgets.backtest.main import BacktestWidget
from ui.widgets.optimization.main import OptimizationWidget

# 레거시 GUI 위젯 (거래내역)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from GUI.history_widget import HistoryWidget

# 유틸리티
from utils.logger import get_module_logger


class ModernMainWindow(QMainWindow):
    """TwinStar Quantum 메인 윈도우 (v7.26)

    특징:
    - 신규 디자인 시스템 (토큰 기반)
    - Phase 2 백테스트 위젯 통합
    - Phase 4-6 최적화 위젯 통합
    - 탭 기반 레이아웃
    """

    def __init__(self):
        super().__init__()
        self._logger = get_module_logger(__name__)
        self._logger.info("Modern Main Window 초기화 시작")

        self._init_ui()
        self._logger.info("Modern Main Window 초기화 완료")

    def _init_ui(self):
        """UI 초기화"""
        # 윈도우 설정
        self.setWindowTitle("TwinStar Quantum (Modern UI v7.26)")
        self.setMinimumSize(QSize(1400, 900))

        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)

        # 메인 레이아웃
        layout = QVBoxLayout(central)
        layout.setSpacing(Spacing.i_space_2)
        layout.setContentsMargins(
            Spacing.i_space_3,
            Spacing.i_space_3,
            Spacing.i_space_3,
            Spacing.i_space_3
        )

        # 헤더
        header = self._create_header()
        layout.addWidget(header)

        # 탭 위젯
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {Colors.border_default};
                border-radius: {Spacing.space_2};
                background: {Colors.bg_surface};
            }}
            QTabBar::tab {{
                background: {Colors.bg_elevated};
                color: {Colors.text_secondary};
                padding: {Spacing.space_2} {Spacing.space_4};
                margin-right: {Spacing.space_1};
                border-top-left-radius: {Spacing.space_1};
                border-top-right-radius: {Spacing.space_1};
                font-size: {Typography.text_base};
            }}
            QTabBar::tab:selected {{
                background: {Colors.bg_surface};
                color: {Colors.text_primary};
                font-weight: {Typography.font_bold};
            }}
            QTabBar::tab:hover {{
                background: {Colors.bg_overlay};
            }}
        """)

        # 탭 추가
        self._add_tabs()
        layout.addWidget(self._tabs)

    def _create_header(self) -> QWidget:
        """헤더 생성"""
        header = QWidget()
        header.setFixedHeight(Size.card_compact)
        header.setStyleSheet(f"""
            QWidget {{
                background: {Colors.bg_elevated};
                border-bottom: 2px solid {Colors.accent_primary};
                border-radius: {Spacing.space_2};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setSpacing(Spacing.i_space_3)
        layout.setContentsMargins(
            Spacing.i_space_4,
            Spacing.i_space_2,
            Spacing.i_space_4,
            Spacing.i_space_2
        )

        # 타이틀
        title = QLabel("🌟 TwinStar Quantum")
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.accent_primary};
                font-size: {Typography.text_2xl};
                font-weight: {Typography.font_bold};
            }}
        """)
        layout.addWidget(title)

        # 버전
        version = QLabel("v7.26 (Modern UI)")
        version.setStyleSheet(f"""
            QLabel {{
                color: {Colors.text_muted};
                font-size: {Typography.text_sm};
            }}
        """)
        layout.addWidget(version)

        layout.addStretch()

        # 정보 버튼
        info_btn = QPushButton("ℹ️ 정보")
        info_btn.setFixedHeight(Size.button_md)
        info_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.bg_base};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Spacing.space_1};
                padding: 0 {Spacing.space_3};
                font-size: {Typography.text_sm};
            }}
            QPushButton:hover {{
                background: {Colors.bg_overlay};
                border-color: {Colors.accent_primary};
            }}
        """)
        info_btn.clicked.connect(self._show_info)
        layout.addWidget(info_btn)

        return header

    def _add_tabs(self):
        """탭 추가"""
        # 1. 백테스트 탭 (Phase 2 완료)
        try:
            self._backtest_widget = BacktestWidget()
            self._tabs.addTab(self._backtest_widget, "📊 백테스트")

            # 백테스트 완료 시그널 연결
            self._backtest_widget.backtest_finished.connect(self._on_backtest_finished)
            self._logger.info("백테스트 탭 추가 및 신호 연결 완료")
        except Exception as e:
            self._logger.error(f"백테스트 탭 추가 실패: {e}")
            error_widget = self._create_error_widget("백테스트 위젯 로드 실패")
            self._tabs.addTab(error_widget, "📊 백테스트")
            self._backtest_widget = None

        # 2. 최적화 탭 (Phase 4-6 완료)
        try:
            optimization_widget = OptimizationWidget()
            self._tabs.addTab(optimization_widget, "🔍 최적화")
            self._logger.info("최적화 탭 추가 완료")
        except Exception as e:
            self._logger.error(f"최적화 탭 추가 실패: {e}")
            error_widget = self._create_error_widget("최적화 위젯 로드 실패")
            self._tabs.addTab(error_widget, "🔍 최적화")

        # 3. 거래내역 탭 (Phase 7-2 추가)
        try:
            self._history_widget = HistoryWidget()
            self._tabs.addTab(self._history_widget, "📜 거래내역")
            self._logger.info("거래내역 탭 추가 완료")
        except Exception as e:
            self._logger.error(f"거래내역 탭 추가 실패: {e}")
            error_widget = self._create_error_widget("거래내역 위젯 로드 실패")
            self._tabs.addTab(error_widget, "📜 거래내역")
            self._history_widget = None

        # 4. 대시보드 탭 (향후 확장)
        placeholder = self._create_placeholder_widget(
            "대시보드",
            "실시간 거래 현황 및 포지션 모니터링\n(향후 Phase 5에서 추가 예정)"
        )
        self._tabs.addTab(placeholder, "📈 대시보드")

        # 5. 설정 탭 (향후 확장)
        placeholder = self._create_placeholder_widget(
            "설정",
            "거래소 API 키 관리 및 시스템 설정\n(향후 Phase 6에서 추가 예정)"
        )
        self._tabs.addTab(placeholder, "⚙️ 설정")

    def _create_error_widget(self, message: str) -> QWidget:
        """에러 위젯 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(f"❌ {message}")
        label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.danger};
                font-size: {Typography.text_lg};
            }}
        """)
        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        return widget

    def _create_placeholder_widget(self, title: str, description: str) -> QWidget:
        """플레이스홀더 위젯 생성"""
        widget = QWidget()
        widget.setStyleSheet(f"background: {Colors.bg_surface};")

        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 타이틀
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.text_primary};
                font-size: {Typography.text_2xl};
                font-weight: {Typography.font_bold};
            }}
        """)
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 설명
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.text_secondary};
                font-size: {Typography.text_base};
            }}
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignCenter)

        return widget

    def _on_backtest_finished(self, trades, df, params):
        """백테스트 완료 시 거래내역 탭에 자동 표시

        Args:
            trades: 거래 내역 리스트 (List[Dict[str, Any]])
            df: 백테스트 데이터프레임 (미사용)
            params: 전략 파라미터 (미사용)
        """
        try:
            if hasattr(self, '_history_widget') and self._history_widget:
                # HistoryWidget에 백테스트 결과 추가
                self._history_widget.add_backtest_results(trades)
                self._logger.info(f"[MainWindow] 백테스트 결과 전달 완료: {len(trades)}개 거래")

                # 거래내역 탭으로 자동 전환
                history_tab_index = self._tabs.indexOf(self._history_widget)
                if history_tab_index >= 0:
                    self._tabs.setCurrentIndex(history_tab_index)
                    self._logger.info(f"[MainWindow] 거래내역 탭으로 전환 (index={history_tab_index})")
        except Exception as e:
            self._logger.error(f"[MainWindow] 백테스트 결과 처리 실패: {e}")

    def _show_info(self):
        """정보 다이얼로그 표시"""
        info_text = """
<h3>TwinStar Quantum v7.26</h3>
<p><b>Modern UI 버전</b></p>

<h4>완료된 Phase:</h4>
<ul>
    <li>✅ Phase 2: 백테스트 위젯 모듈 분리 (2026-01-15)</li>
    <li>✅ Phase 4-6: 최적화 위젯 Mixin 아키텍처 완성 (2026-01-19)</li>
</ul>

<h4>특징:</h4>
<ul>
    <li>토큰 기반 디자인 시스템</li>
    <li>Single Responsibility Principle (SRP) 100% 준수</li>
    <li>타입 안전성 (Pyright Error 0개)</li>
    <li>SSOT 원칙 완벽 준수</li>
</ul>

<h4>향후 Phase:</h4>
<ul>
    <li>Phase 5: 대시보드 위젯 (실시간 거래 모니터링)</li>
    <li>Phase 6: 설정 위젯 (API 키 관리)</li>
</ul>

<p style="color: #00d4ff;">
<b>개발 팀:</b> TwinStar-Quantum<br>
<b>문서:</b> docs/OPTIMIZATION_WIDGETS_IMPROVEMENT_REPORT_20260119.md
</p>
        """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("TwinStar Quantum 정보")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(info_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()


def main():
    """메인 함수"""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테마 적용
    app.setStyleSheet(ThemeGenerator.generate())

    # 메인 윈도우
    window = ModernMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
