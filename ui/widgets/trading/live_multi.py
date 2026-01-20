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
from PyQt6.QtCore import pyqtSignal, QTimer, Qt, QMutex
from PyQt6.QtGui import QFont
from typing import Optional, List, Dict, Any

from utils.logger import get_module_logger

# 디자인 토큰 및 스타일
try:
    from ui.design_system.tokens import Colors, Spacing, Typography, Size
    from ui.widgets.backtest.styles import BacktestStyles
except ImportError:
    # Issue #2 Fix: 중앙화된 Fallback 사용 (v7.27)
    from ui.design_system.fallback_tokens import Colors, Spacing, Typography, Size
    import logging
    logging.warning("[LiveMulti] Using fallback tokens - SSOT import failed")

    # BacktestStyles fallback (스타일 클래스는 별도 처리)
    class _BacktestStylesFallback:
        @staticmethod
        def button_primary() -> str:
            return "background: #3fb950; color: white; padding: 8px 16px; border-radius: 5px;"

        @staticmethod
        def button_danger() -> str:
            return "background: #f85149; color: white; padding: 8px 16px; border-radius: 5px;"

        @staticmethod
        def button_info() -> str:
            return "background: #58a6ff; color: white; padding: 8px 16px; border-radius: 5px;"

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

    BacktestStyles = _BacktestStylesFallback()

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
        self.initial_capital_spin: Optional[QDoubleSpinBox] = None  # Phase 1: 초기 자본 필드
        self.current_balance_label: Optional[QLabel] = None  # Phase 1: 현재 잔액 라벨
        self.mode_combo: Optional[QComboBox] = None

        self.watching_label: Optional[QLabel] = None
        self.pending_label: Optional[QLabel] = None
        self.position_label: Optional[QLabel] = None

        self.start_btn: Optional[QPushButton] = None

        self.pending_table: Optional[QTableWidget] = None

        # 상태 업데이트 타이머
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._request_status_update)

        # Phase 2: 잔액 업데이트 타이머 (1초마다)
        self.balance_timer = QTimer(self)
        self.balance_timer.timeout.connect(self._update_balance_display)

        # Issue #4: 잔액 업데이트 mutex (v7.27)
        self.balance_mutex = QMutex()

        # UI 초기화
        self._init_ui()

    def closeEvent(self, event):
        """위젯 종료 시 리소스 정리 (v7.27 신규)"""
        # 타이머 정리
        if self.status_timer and self.status_timer.isActive():
            self.status_timer.stop()

        if self.balance_timer and self.balance_timer.isActive():
            self.balance_timer.stop()

        # 실행 중이면 중지
        if self.is_running:
            self._stop_trading()

        super().closeEvent(event)

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
        self.exchange_combo.setMinimumWidth(Size.control_min_width)
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

        # Phase 1: 초기 자본 (매매 시작 전에만 수정 가능)
        grid.addWidget(QLabel("초기 자본:"), row, 2)
        self.initial_capital_spin = QDoubleSpinBox()
        self.initial_capital_spin.setRange(10, 100000)
        self.initial_capital_spin.setValue(100)
        self.initial_capital_spin.setPrefix("$")
        self.initial_capital_spin.setSuffix(" (시작 전 수정)")
        self.initial_capital_spin.setStyleSheet(BacktestStyles.spin_box())
        self.initial_capital_spin.setToolTip("매매 시작 전에만 수정 가능합니다")
        grid.addWidget(self.initial_capital_spin, row, 3)

        # 자본 모드
        grid.addWidget(QLabel("자본 모드:"), row, 4)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["📈 복리 (Compound)", "📊 고정 (Fixed)"])
        self.mode_combo.setStyleSheet(BacktestStyles.combo_box())
        self.mode_combo.setMinimumWidth(Size.input_min_width)
        grid.addWidget(self.mode_combo, row, 5)

        row += 1

        # Phase 1: 현재 잔액 (읽기 전용, 실시간 업데이트)
        grid.addWidget(QLabel("현재 잔액:"), row, 2)
        self.current_balance_label = QLabel("$100.00 🔒")
        self.current_balance_label.setStyleSheet(f"""
            color: {Colors.text_primary};
            font-weight: bold;
            font-size: 14px;
            padding: 8px;
            background: {Colors.bg_elevated};
            border-radius: 4px;
        """)
        self.current_balance_label.setToolTip("실시간 업데이트 중 (읽기 전용)")
        self.current_balance_label.setMinimumWidth(200)
        grid.addWidget(self.current_balance_label, row, 3)

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
        self.pending_table.setMaximumHeight(Size.input_min_width)  # 200px (충분한 높이)

        # 헤더 설정
        header = self.pending_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.pending_table)

        return group

    def _create_control_buttons(self) -> QHBoxLayout:
        """제어 버튼 (시작/중지/거래내역)"""
        row = QHBoxLayout()
        row.setSpacing(Spacing.i_space_2)
        row.addStretch()

        # 시작/중지 버튼
        self.start_btn = QPushButton("▶ Start Trading")
        self.start_btn.setStyleSheet(BacktestStyles.button_primary())
        self.start_btn.clicked.connect(self._toggle_trading)
        self.start_btn.setMinimumWidth(Size.input_min_width)  # 200px
        row.addWidget(self.start_btn)

        # 거래내역 버튼 (Phase 7-3 추가)
        history_btn = QPushButton("📜 History")
        try:
            history_btn.setStyleSheet(BacktestStyles.button_info())
        except AttributeError:
            # button_info() 메서드가 없을 경우 기본 스타일 사용
            history_btn.setStyleSheet(BacktestStyles.combo_box())
        history_btn.setMinimumWidth(Size.button_min_width)  # 80px
        history_btn.clicked.connect(self._show_history)
        row.addWidget(history_btn)

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

        # Phase 2: 초기 자본 필드 잠금 (매매 중 수정 방지)
        if self.initial_capital_spin:
            self.initial_capital_spin.setEnabled(False)
            self.initial_capital_spin.setSuffix(" (매매 중)")

        # Phase 2: 잔액 업데이트 타이머 시작 (1초마다)
        if self.balance_timer:
            self.balance_timer.start(1000)

        # Phase 2: 초기 잔액 표시 (Issue #4: mutex 보호)
        initial = self.initial_capital_spin.value() if self.initial_capital_spin else 100.0
        self.balance_mutex.lock()
        try:
            self._on_balance_updated(initial)
        finally:
            self.balance_mutex.unlock()

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

        # Phase 2: 초기 자본 필드 잠금 해제
        if self.initial_capital_spin:
            self.initial_capital_spin.setEnabled(True)
            self.initial_capital_spin.setSuffix(" (시작 전 수정)")

        # Phase 2: 잔액 업데이트 타이머 중지
        if self.balance_timer:
            self.balance_timer.stop()

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
            'initial_capital': self.initial_capital_spin.value() if self.initial_capital_spin else 100.0,
            'capital_mode': 'compound' if (self.mode_combo and self.mode_combo.currentIndex() == 0) else 'fixed'
        }

    def apply_config(self, config: dict):
        """설정 적용 (백테스트 → 실시간 복사용)

        Args:
            config: {'exchange': ..., 'leverage': ..., 'initial_capital': ...}
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

        # Phase 3: initial_capital 또는 하위 호환 seed
        if self.initial_capital_spin:
            capital = config.get('initial_capital', config.get('seed', 100.0))
            self.initial_capital_spin.setValue(capital)

        if self.mode_combo and 'capital_mode' in config:
            idx = 0 if config['capital_mode'] == 'compound' else 1
            self.mode_combo.setCurrentIndex(idx)

        logger.info(f"[LiveMulti] 설정 적용: {config}")

    def _show_history(self):
        """거래내역 팝업 표시 (Phase 7-3)"""
        try:
            # GUI.history_widget import
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            from GUI.history_widget import HistoryWidget

            # 팝업 다이얼로그 생성 (최초 1회만)
            if not hasattr(self, '_history_dialog'):
                self._history_dialog = HistoryWidget()
                self._history_dialog.setWindowTitle("📜 거래 내역")
                self._history_dialog.resize(1200, 800)

            # 표시
            self._history_dialog.show()
            self._history_dialog.raise_()
            self._history_dialog.activateWindow()

            logger.info("[LiveMulti] 거래내역 팝업 표시")
        except Exception as e:
            logger.error(f"[LiveMulti] 거래내역 팝업 표시 실패: {e}")
            # 에러 메시지 표시 (선택적)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"거래내역을 로드할 수 없습니다.\n{e}")

    def _update_balance_display(self):
        """잔액 표시 업데이트 (1초마다 호출) - Phase 2, Issue #4

        멀티 심볼 거래의 경우 모든 심볼의 PnL을 합산하여 표시합니다.

        Issue #4 Fix: QMutex로 UI 위젯 동시 접근 방지 (v7.27)
        """
        if not self.is_running or not self.current_balance_label:
            return

        # ✅ Critical section 시작 (UI 위젯 접근 보호)
        self.balance_mutex.lock()
        try:
            # 현재 거래소
            exchange = self.exchange_combo.currentText().lower() if self.exchange_combo else 'bybit'

            # 모든 거래 내역에서 총 손익 계산 (멀티 심볼)
            from storage import trade_storage

            total_pnl_usd = 0.0
            active_symbols = []

            # 모든 스토리지 인스턴스를 순회하며 현재 거래소의 심볼들을 찾음
            for key, storage in trade_storage._storage_instances.items():
                # key 형식: "{exchange}_{symbol}" (예: "bybit_BTCUSDT")
                if key.startswith(f"{exchange}_"):
                    stats = storage.get_stats()
                    symbol_pnl = stats.get('total_pnl_usd', 0)

                    if symbol_pnl != 0:  # 거래 내역이 있는 심볼만
                        total_pnl_usd += symbol_pnl
                        symbol_name = key.split('_', 1)[1]  # 심볼 추출
                        active_symbols.append(f"{symbol_name}({symbol_pnl:+.2f})")

            # 초기 자본
            initial = self.initial_capital_spin.value() if self.initial_capital_spin else 100.0

            # 현재 잔액 계산
            current_balance = initial + total_pnl_usd

            # UI 업데이트
            self._on_balance_updated(current_balance)

            # 디버그 로그 (활성 심볼이 있을 때만)
            if active_symbols:
                logger.debug(f"[LiveMulti] 잔액 업데이트: {len(active_symbols)}개 심볼, 총 PnL ${total_pnl_usd:+.2f}")

        except Exception as e:
            logger.error(f"[LiveMulti] 잔액 업데이트 실패: {e}")
        finally:
            # ✅ Critical section 종료 (항상 unlock)
            self.balance_mutex.unlock()

    def _on_balance_updated(self, new_balance: float):
        """잔액 업데이트 슬롯 - Phase 2, 3

        Args:
            new_balance: 새로운 잔액 ($)
        """
        if not self.current_balance_label or not self.initial_capital_spin:
            return

        initial = self.initial_capital_spin.value()
        pnl = new_balance - initial

        # 모드 확인
        is_compound = self.mode_combo.currentIndex() == 0 if self.mode_combo else True

        # 색상 결정
        if pnl > 0:
            color = Colors.success  # 초록
        elif pnl < 0:
            color = Colors.danger   # 빨강
        else:
            color = Colors.text_primary  # 회색

        # 텍스트 및 툴팁
        if is_compound:
            # 복리: 현재 잔액 표시
            text = f"${new_balance:,.2f} 🔒"
            tooltip = f"다음 거래 크기: ${new_balance:,.2f}\n누적 손익: {pnl:+,.2f}"
        else:
            # 고정: 누적 손익 표시
            text = f"{pnl:+,.2f} 🔒"
            tooltip = f"다음 거래 크기: ${initial:,.2f} (고정)\n현재 잔액: ${new_balance:,.2f}"

        # UI 업데이트
        self.current_balance_label.setText(text)
        self.current_balance_label.setStyleSheet(f"""
            color: {color};
            font-weight: bold;
            font-size: 14px;
            padding: 8px;
            background: {Colors.bg_elevated};
            border-radius: 4px;
        """)
        self.current_balance_label.setToolTip(tooltip)


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
