"""
멀티 심볼 실시간 매매 위젯 (v3.0 - 신규 디자인 시스템)

핵심 개념: N개 감시 → 1개 선택 → 프리셋 확인/생성 → 싱글처럼 매매 → 청산 후 반복

Phase 4.1: 디자인 시스템 마이그레이션
- 토큰 기반 스타일 (ui.design_system.tokens)
- 백테스트 위젯 스타일 재사용 (ui.widgets.backtest.styles)
- VS Code Pyright 에러 0개 유지
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QFont
from typing import Optional, List, Dict, Any

from utils.logger import get_module_logger

# 디자인 토큰 및 스타일
try:
    from ui.design_system.tokens import Colors, Spacing, Typography, Radius
    from ui.widgets.backtest.styles import BacktestStyles
except ImportError:
    # Fallback (하위 호환성)
    class _ColorsFallback:
        success = "#3fb950"
        danger = "#f85149"
        info = "#58a6ff"
        accent_primary = "#00d4ff"
        text_primary = "#f0f6fc"
        text_secondary = "#8b949e"
        text_muted = "#6e7681"
        bg_base = "#0d1117"
        bg_surface = "#161b22"
        bg_elevated = "#1f2937"
        border_default = "#30363d"

    class _SpacingFallback:
        i_space_1 = 4
        i_space_2 = 8
        i_space_3 = 12
        i_space_4 = 16

    class _BacktestStylesFallback:
        @staticmethod
        def button_primary() -> str:
            return "background: #3fb950; color: white; padding: 8px 16px; border-radius: 5px;"

        @staticmethod
        def button_danger() -> str:
            return "background: #f85149; color: white; padding: 8px 16px; border-radius: 5px;"

        @staticmethod
        def combo_box() -> str:
            return "background: #1f2937; color: white; padding: 4px; border: 1px solid #30363d;"

        @staticmethod
        def spin_box() -> str:
            return "background: #1f2937; color: white; padding: 4px; border: 1px solid #30363d;"

        @staticmethod
        def group_box(color: str | None = None) -> str:
            return f"border: 1px solid {color or '#30363d'}; border-radius: 5px; margin-top: 12px;"

        @staticmethod
        def table() -> str:
            return "background: #161b22; color: white; border: none;"

    Colors = _ColorsFallback()  # type: ignore
    Spacing = _SpacingFallback()  # type: ignore
    BacktestStyles = _BacktestStylesFallback()  # type: ignore

logger = get_module_logger(__name__)


class LiveMultiWidget(QWidget):
    """
    멀티 심볼 실시간 매매 위젯 (신규 디자인 v3.0)

    N개 감시 → 1개 선택 → 싱글처럼 매매 → 청산 후 반복

    Signals:
        start_signal(dict): 매매 시작 (config)
        stop_signal(): 매매 중지

    Example:
        widget = LiveMultiWidget()
        widget.start_signal.connect(on_start)
        widget.stop_signal.connect(on_stop)
    """

    start_signal = pyqtSignal(dict)
    stop_signal = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 상태
        self.is_running = False
        self.trader: Optional[Any] = None  # MultiTrader 인스턴스

        # UI 컴포넌트
        self.exchange_combo: Optional[QComboBox] = None
        self.watch_spin: Optional[QSpinBox] = None
        self.max_pos_spin: Optional[QSpinBox] = None
        self.leverage_spin: Optional[QSpinBox] = None
        self.seed_spin: Optional[QDoubleSpinBox] = None
        self.mode_combo: Optional[QComboBox] = None

        self.watching_label: Optional[QLabel] = None
        self.pending_label: Optional[QLabel] = None
        self.position_label: Optional[QLabel] = None

        self.start_btn: Optional[QPushButton] = None

        self.pending_table: Optional[QTableWidget] = None

        # 상태 업데이트 타이머
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._request_status_update)

        # UI 초기화
        self._init_ui()

    def _init_ui(self):
        """UI 초기화 (토큰 기반 디자인)"""
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.i_space_3)  # 12px
        layout.setContentsMargins(
            Spacing.i_space_4,  # 16px
            Spacing.i_space_3,  # 12px
            Spacing.i_space_4,  # 16px
            Spacing.i_space_3   # 12px
        )

        # 설정 그룹
        layout.addWidget(self._create_settings_group())

        # 상태 표시 그룹
        layout.addWidget(self._create_status_group())

        # 시그널 대기 테이블
        layout.addWidget(self._create_pending_table())

        # 제어 버튼
        layout.addLayout(self._create_control_buttons())

    def _create_settings_group(self) -> QGroupBox:
        """설정 그룹 (거래소, 감시 수, 레버리지 등)"""
        group = QGroupBox("⚙️ Multi-Symbol Live Trading Settings")
        group.setStyleSheet(BacktestStyles.group_box(Colors.accent_primary))

        grid = QGridLayout(group)
        grid.setSpacing(Spacing.i_space_2)  # 8px
        grid.setContentsMargins(
            Spacing.i_space_3,
            Spacing.i_space_4,
            Spacing.i_space_3,
            Spacing.i_space_3
        )

        row = 0

        # === Row 0: 거래소, 감시 수, 동시 포지션 ===

        # 거래소
        grid.addWidget(QLabel("거래소:"), row, 0)
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['bybit', 'binance', 'okx', 'bitget'])
        self.exchange_combo.setStyleSheet(BacktestStyles.combo_box())
        self.exchange_combo.setMinimumWidth(120)
        grid.addWidget(self.exchange_combo, row, 1)

        # 감시 대상 수
        grid.addWidget(QLabel("감시 심볼:"), row, 2)
        self.watch_spin = QSpinBox()
        self.watch_spin.setRange(10, 100)
        self.watch_spin.setValue(50)
        self.watch_spin.setSuffix("개")
        self.watch_spin.setStyleSheet(BacktestStyles.spin_box())
        grid.addWidget(self.watch_spin, row, 3)

        # 동시 매매 수
        grid.addWidget(QLabel("동시 포지션:"), row, 4)
        self.max_pos_spin = QSpinBox()
        self.max_pos_spin.setRange(1, 5)
        self.max_pos_spin.setValue(1)
        self.max_pos_spin.setSuffix("개")
        self.max_pos_spin.setStyleSheet(BacktestStyles.spin_box())
        grid.addWidget(self.max_pos_spin, row, 5)

        row += 1

        # === Row 1: 레버리지, 시드, 자본 모드 ===

        # 레버리지
        grid.addWidget(QLabel("레버리지:"), row, 0)
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 50)
        self.leverage_spin.setValue(10)
        self.leverage_spin.setSuffix("x")
        self.leverage_spin.setStyleSheet(BacktestStyles.spin_box())
        grid.addWidget(self.leverage_spin, row, 1)

        # 시드
        grid.addWidget(QLabel("시드 자본:"), row, 2)
        self.seed_spin = QDoubleSpinBox()
        self.seed_spin.setRange(10, 10000)
        self.seed_spin.setValue(100)
        self.seed_spin.setPrefix("$")
        self.seed_spin.setStyleSheet(BacktestStyles.spin_box())
        grid.addWidget(self.seed_spin, row, 3)

        # 자본 모드
        grid.addWidget(QLabel("자본 모드:"), row, 4)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["📈 복리 (Compound)", "📊 고정 (Fixed)"])
        self.mode_combo.setStyleSheet(BacktestStyles.combo_box())
        self.mode_combo.setMinimumWidth(150)
        grid.addWidget(self.mode_combo, row, 5)

        # 컬럼 stretch
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(5, 1)

        return group

    def _create_status_group(self) -> QGroupBox:
        """상태 표시 그룹 (감시 중, 시그널 대기, 현재 매매)"""
        group = QGroupBox("📊 Current Status")
        group.setStyleSheet(BacktestStyles.group_box(Colors.success))

        layout = QVBoxLayout(group)
        layout.setSpacing(Spacing.i_space_1)  # 4px
        layout.setContentsMargins(
            Spacing.i_space_3,
            Spacing.i_space_4,
            Spacing.i_space_3,
            Spacing.i_space_2
        )

        # 감시 중
        self.watching_label = QLabel("├─ 감시 중: 0개")
        self.watching_label.setStyleSheet(f"color: {Colors.text_secondary}; font-size: {Typography.text_sm};")
        layout.addWidget(self.watching_label)

        # 시그널 대기
        self.pending_label = QLabel("├─ 시그널 대기: 없음")
        self.pending_label.setStyleSheet(f"color: {Colors.info}; font-size: {Typography.text_sm};")
        layout.addWidget(self.pending_label)

        # 현재 매매
        self.position_label = QLabel("└─ 현재 매매: 없음")
        self.position_label.setStyleSheet(f"color: {Colors.text_muted}; font-size: {Typography.text_sm}; font-weight: {Typography.font_bold};")
        layout.addWidget(self.position_label)

        return group

    def _create_pending_table(self) -> QGroupBox:
        """시그널 대기 목록 테이블"""
        group = QGroupBox("🔔 Pending Signals")
        group.setStyleSheet(BacktestStyles.group_box(Colors.info))

        layout = QVBoxLayout(group)
        layout.setSpacing(Spacing.i_space_2)
        layout.setContentsMargins(
            Spacing.i_space_3,
            Spacing.i_space_4,
            Spacing.i_space_3,
            Spacing.i_space_2
        )

        # 테이블
        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(4)
        self.pending_table.setHorizontalHeaderLabels(["Symbol", "Direction", "Strength", "Price"])
        self.pending_table.setStyleSheet(BacktestStyles.table())
        self.pending_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pending_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.pending_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pending_table.setMaximumHeight(150)

        # 헤더 설정
        header = self.pending_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.pending_table)

        return group

    def _create_control_buttons(self) -> QHBoxLayout:
        """제어 버튼 (시작/중지)"""
        row = QHBoxLayout()
        row.setSpacing(Spacing.i_space_2)
        row.addStretch()

        # 시작/중지 버튼
        self.start_btn = QPushButton("▶ Start Trading")
        self.start_btn.setStyleSheet(BacktestStyles.button_primary())
        self.start_btn.clicked.connect(self._toggle_trading)
        self.start_btn.setMinimumWidth(150)
        row.addWidget(self.start_btn)

        row.addStretch()
        return row

    def _toggle_trading(self):
        """매매 시작/중지 토글"""
        if self.is_running:
            self._stop_trading()
        else:
            self._start_trading()

    def _start_trading(self):
        """멀티 매매 시작"""
        if not self.start_btn:
            return

        self.is_running = True

        # 설정 수집
        config = self.get_config()

        # UI 업데이트
        self.start_btn.setText("⏹ Stop Trading")
        self.start_btn.setStyleSheet(BacktestStyles.button_danger())

        # 상태 타이머 시작 (1초마다)
        self.status_timer.start(1000)

        # 시그널 발생
        self.start_signal.emit(config)
        logger.info(f"[LiveMulti] 시작: {config}")

    def _stop_trading(self):
        """멀티 매매 중지"""
        if not self.start_btn:
            return

        self.is_running = False

        # UI 복원
        self.start_btn.setText("▶ Start Trading")
        self.start_btn.setStyleSheet(BacktestStyles.button_primary())

        # 상태 타이머 중지
        self.status_timer.stop()

        # 상태 초기화
        self._reset_status_display()

        # 시그널 발생
        self.stop_signal.emit()
        logger.info("[LiveMulti] 중지")

    def _reset_status_display(self):
        """상태 표시 초기화"""
        if self.watching_label:
            self.watching_label.setText("├─ 감시 중: 0개")
            self.watching_label.setStyleSheet(f"color: {Colors.text_secondary}; font-size: {Typography.text_sm};")

        if self.pending_label:
            self.pending_label.setText("├─ 시그널 대기: 없음")
            self.pending_label.setStyleSheet(f"color: {Colors.text_muted}; font-size: {Typography.text_sm};")

        if self.position_label:
            self.position_label.setText("└─ 현재 매매: 없음")
            self.position_label.setStyleSheet(f"color: {Colors.text_muted}; font-size: {Typography.text_sm};")

        if self.pending_table:
            self.pending_table.setRowCount(0)

    def _request_status_update(self):
        """상태 업데이트 요청 (타이머에서 호출)"""
        # Phase 4.2: 타이머 방식은 deprecated (콜백 방식으로 대체)
        # 하위 호환성을 위해 유지
        if self.trader:
            try:
                stats = self.trader.get_stats()
                self.update_status(
                    watching=stats.get('watching', 0),
                    pending=stats.get('pending', []),
                    position=stats.get('active', None)
                )
            except Exception as e:
                logger.error(f"[LiveMulti] 상태 업데이트 에러: {e}")

    def _on_trader_status_update(self, stats: dict):
        """MultiTrader 콜백 핸들러 (Phase 4.2)

        Args:
            stats: {'watching': int, 'pending': list, 'active': dict|None}
        """
        # GUI 스레드에서 안전하게 업데이트
        try:
            self.update_status(
                watching=stats.get('watching', 0),
                pending=stats.get('pending', []),
                position=stats.get('active', None)
            )
        except Exception as e:
            logger.error(f"[LiveMulti] 콜백 상태 업데이트 에러: {e}")

    def connect_trader(self, trader: Any):
        """MultiTrader 인스턴스 연결

        Args:
            trader: core.multi_trader.MultiTrader 인스턴스
        """
        self.trader = trader

        # Phase 4.2: 콜백 방식 상태 업데이트 설정
        trader.set_status_callback(self._on_trader_status_update)

        logger.info("[LiveMulti] MultiTrader 연결됨 (콜백 설정 완료)")

    def update_status(
        self,
        watching: int = 0,
        pending: Optional[List[Dict[str, Any]]] = None,
        position: Optional[Dict[str, Any]] = None
    ):
        """상태 업데이트 (외부 호출 가능)

        Args:
            watching: 감시 중인 심볼 수
            pending: 시그널 대기 목록 [{'symbol': ..., 'direction': ..., 'strength': ..., 'price': ...}, ...]
            position: 현재 포지션 {'symbol': ..., 'direction': ..., 'pnl': ...}
        """
        # 감시 중
        if self.watching_label:
            self.watching_label.setText(f"├─ 감시 중: {watching}개")
            self.watching_label.setStyleSheet(f"color: {Colors.text_secondary}; font-size: {Typography.text_sm};")

        # 시그널 대기
        if pending and len(pending) > 0:
            if self.pending_label:
                symbols = ", ".join([p.get('symbol', '')[:6] for p in pending[:3]])
                self.pending_label.setText(f"├─ 시그널 대기: {len(pending)}개 ({symbols}...)")
                self.pending_label.setStyleSheet(f"color: {Colors.info}; font-size: {Typography.text_sm};")

            # 테이블 업데이트
            self._update_pending_table(pending)
        else:
            if self.pending_label:
                self.pending_label.setText("├─ 시그널 대기: 없음")
                self.pending_label.setStyleSheet(f"color: {Colors.text_muted}; font-size: {Typography.text_sm};")

            if self.pending_table:
                self.pending_table.setRowCount(0)

        # 현재 포지션
        if position:
            symbol = position.get('symbol', '')
            direction = position.get('direction', '')
            pnl = position.get('pnl', 0.0)

            pnl_str = f"+{pnl:.2f}%" if pnl >= 0 else f"{pnl:.2f}%"
            pnl_color = Colors.success if pnl >= 0 else Colors.danger

            if self.position_label:
                self.position_label.setText(f"└─ 현재 매매: {symbol} {direction} {pnl_str}")
                self.position_label.setStyleSheet(f"color: {pnl_color}; font-size: {Typography.text_sm}; font-weight: {Typography.font_bold};")
        else:
            if self.position_label:
                self.position_label.setText("└─ 현재 매매: 없음")
                self.position_label.setStyleSheet(f"color: {Colors.text_muted}; font-size: {Typography.text_sm};")

    def _update_pending_table(self, pending: List[Dict[str, Any]]):
        """시그널 대기 목록 테이블 업데이트"""
        if not self.pending_table:
            return

        self.pending_table.setRowCount(len(pending))

        for row, signal in enumerate(pending):
            # Symbol
            symbol_item = QTableWidgetItem(signal.get('symbol', ''))
            symbol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pending_table.setItem(row, 0, symbol_item)

            # Direction
            direction = signal.get('direction', '')
            direction_item = QTableWidgetItem(direction)
            direction_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 방향별 색상
            if direction == 'Long':
                direction_item.setForeground(Colors.success)  # type: ignore
            elif direction == 'Short':
                direction_item.setForeground(Colors.danger)  # type: ignore

            self.pending_table.setItem(row, 1, direction_item)

            # Strength
            strength = signal.get('strength', 0.0)
            strength_item = QTableWidgetItem(f"{strength:.2f}")
            strength_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pending_table.setItem(row, 2, strength_item)

            # Price
            price = signal.get('price', 0.0)
            price_item = QTableWidgetItem(f"${price:.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.pending_table.setItem(row, 3, price_item)

    def get_config(self) -> dict:
        """현재 설정 반환"""
        return {
            'exchange': self.exchange_combo.currentText().lower() if self.exchange_combo else 'bybit',
            'watch_count': self.watch_spin.value() if self.watch_spin else 50,
            'max_positions': self.max_pos_spin.value() if self.max_pos_spin else 1,
            'leverage': self.leverage_spin.value() if self.leverage_spin else 10,
            'seed': self.seed_spin.value() if self.seed_spin else 100.0,
            'capital_mode': 'compound' if (self.mode_combo and self.mode_combo.currentIndex() == 0) else 'fixed'
        }

    def apply_config(self, config: dict):
        """설정 적용 (백테스트 → 실시간 복사용)

        Args:
            config: {'exchange': ..., 'leverage': ..., 'seed': ...}
        """
        if self.exchange_combo and 'exchange' in config:
            idx = self.exchange_combo.findText(config['exchange'])
            if idx >= 0:
                self.exchange_combo.setCurrentIndex(idx)

        if self.watch_spin and 'watch_count' in config:
            self.watch_spin.setValue(config['watch_count'])

        if self.max_pos_spin and 'max_positions' in config:
            self.max_pos_spin.setValue(config['max_positions'])

        if self.leverage_spin and 'leverage' in config:
            self.leverage_spin.setValue(config['leverage'])

        if self.seed_spin and 'seed' in config:
            self.seed_spin.setValue(config['seed'])

        if self.mode_combo and 'capital_mode' in config:
            idx = 0 if config['capital_mode'] == 'compound' else 1
            self.mode_combo.setCurrentIndex(idx)

        logger.info(f"[LiveMulti] 설정 적용: {config}")


# 개발/테스트용 실행
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테마 적용
    try:
        from ui.design_system.theme import ThemeGenerator
        app.setStyleSheet(ThemeGenerator.generate())
    except ImportError:
        pass

    widget = LiveMultiWidget()
    widget.resize(900, 700)
    widget.show()

    # 테스트 상태 업데이트
    def test_update():
        widget.update_status(
            watching=50,
            pending=[
                {'symbol': 'BTCUSDT', 'direction': 'Long', 'strength': 15.5, 'price': 45000.0},
                {'symbol': 'ETHUSDT', 'direction': 'Short', 'strength': 12.3, 'price': 2500.0},
                {'symbol': 'SOLUSDT', 'direction': 'Long', 'strength': 8.7, 'price': 110.0},
            ],
            position={'symbol': 'BTCUSDT', 'direction': 'Long', 'pnl': 2.5}
        )

    QTimer.singleShot(1000, test_update)

    sys.exit(app.exec())
