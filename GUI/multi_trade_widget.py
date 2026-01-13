"""
MultiTradeWidget - 멀티 매매 제어 위젯 (v2.0 단순화)

핵심 개념: N개 감시 → 1개 선택 → 싱글처럼 매매 → 청산 후 반복
"""

import logging
logger = logging.getLogger(__name__)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QFrame
)
from PyQt5.QtCore import pyqtSignal, QTimer
from locales.lang_manager import t


class MultiTradeWidget(QWidget):
    """멀티 매매 제어 위젯 (단순화 v2.0)"""
    
    start_signal = pyqtSignal(dict)  # config dict
    stop_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # === Row 1: 설정 ===
        settings_layout = QGridLayout()
        settings_layout.setSpacing(8)
        
        # 거래소
        settings_layout.addWidget(QLabel(t("multi.exchange", "거래소:")), 0, 0)
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['bybit', 'binance', 'okx', 'bitget'])
        self.exchange_combo.setStyleSheet("background: #2b2b2b; color: white; min-width: 80px; padding: 3px;")
        settings_layout.addWidget(self.exchange_combo, 0, 1)
        
        # 감시 대상 수
        settings_layout.addWidget(QLabel(t("multi.watch_count", "감시:")), 0, 2)
        self.watch_spin = QSpinBox()
        self.watch_spin.setRange(10, 100)
        self.watch_spin.setValue(50)
        self.watch_spin.setSuffix("개")
        self.watch_spin.setStyleSheet("background: #2b2b2b; color: white; padding: 3px;")
        settings_layout.addWidget(self.watch_spin, 0, 3)
        
        # 동시 매매 수
        settings_layout.addWidget(QLabel(t("multi.max_positions", "동시:")), 0, 4)
        self.max_pos_spin = QSpinBox()
        self.max_pos_spin.setRange(1, 5)
        self.max_pos_spin.setValue(1)
        self.max_pos_spin.setSuffix("개")
        self.max_pos_spin.setStyleSheet("background: #2b2b2b; color: white; padding: 3px;")
        settings_layout.addWidget(self.max_pos_spin, 0, 5)
        
        # 레버리지
        settings_layout.addWidget(QLabel(t("multi.leverage", "레버리지:")), 1, 0)
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 50)
        self.leverage_spin.setValue(10)
        self.leverage_spin.setSuffix("x")
        self.leverage_spin.setStyleSheet("background: #2b2b2b; color: white; padding: 3px;")
        settings_layout.addWidget(self.leverage_spin, 1, 1)
        
        # 시드
        settings_layout.addWidget(QLabel(t("multi.seed", "시드:")), 1, 2)
        self.seed_spin = QDoubleSpinBox()
        self.seed_spin.setRange(10, 10000)
        self.seed_spin.setValue(100)
        self.seed_spin.setPrefix("$")
        self.seed_spin.setStyleSheet("background: #2b2b2b; color: white; padding: 3px;")
        settings_layout.addWidget(self.seed_spin, 1, 3)
        
        # 자본 모드
        settings_layout.addWidget(QLabel(t("multi.capital_mode", "모드:")), 1, 4)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            t("multi.compound", "📈 복리"),
            t("multi.fixed", "📊 고정")
        ])
        self.mode_combo.setStyleSheet("background: #2b2b2b; color: white; min-width: 80px; padding: 3px;")
        settings_layout.addWidget(self.mode_combo, 1, 5)
        
        layout.addLayout(settings_layout)
        
        # === Row 2: 현황 표시 ===
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background: #1a202c;
                border: 1px solid #2d3748;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setSpacing(4)
        
        # 현황 헤더
        status_header = QLabel(t("multi.status", "📊 현황"))
        status_header.setStyleSheet("color: #00d4aa; font-weight: bold; font-size: 13px;")
        status_layout.addWidget(status_header)
        
        # 감시 중
        self.watching_label = QLabel(t("multi.watching", "├─ 감시 중: 0개"))
        self.watching_label.setStyleSheet("color: #a0aec0; font-size: 12px;")
        status_layout.addWidget(self.watching_label)
        
        # 시그널 대기
        self.pending_label = QLabel(t("multi.pending", "├─ 시그널 대기: 없음"))
        self.pending_label.setStyleSheet("color: #ffd93d; font-size: 12px;")
        status_layout.addWidget(self.pending_label)
        
        # 현재 매매
        self.position_label = QLabel(t("multi.current_position", "└─ 현재 매매: 없음"))
        self.position_label.setStyleSheet("color: #00d26a; font-size: 12px; font-weight: bold;")
        status_layout.addWidget(self.position_label)
        
        layout.addWidget(status_frame)
        
        # === Row 3: 버튼 ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # 시작 버튼
        self.start_btn = QPushButton(t("multi.start", "▶ 시작"))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d26a, stop:1 #00a854);
                color: white; font-weight: bold;
                padding: 10px 25px; border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover { background: #00a854; }
        """)
        self.start_btn.clicked.connect(self._toggle_trading)
        btn_layout.addWidget(self.start_btn)
        
        layout.addLayout(btn_layout)
        
        # === 상태 업데이트 타이머 ===
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status_display)
    
    def _toggle_trading(self):
        """시작/중지 토글"""
        if self.is_running:
            self._stop_trading()
        else:
            self._start_trading()
    
    def _start_trading(self):
        """멀티 매매 시작"""
        self.is_running = True
        
        # 설정 수집
        config = {
            'exchange': self.exchange_combo.currentText().lower(),
            'watch_count': self.watch_spin.value(),
            'max_positions': self.max_pos_spin.value(),
            'leverage': self.leverage_spin.value(),
            'seed': self.seed_spin.value(),
            'capital_mode': 'compound' if self.mode_combo.currentIndex() == 0 else 'fixed'
        }
        
        # UI 업데이트
        self.start_btn.setText(t("multi.stop", "⏹ 정지"))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #ff4757;
                color: white; font-weight: bold;
                padding: 10px 25px; border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover { background: #ff6b6b; }
        """)
        
        # 상태 타이머 시작
        self.status_timer.start(1000)
        
        # 시그널 발생
        self.start_signal.emit(config)
        logger.info(f"[Multi] 시작: {config}")
    
    def _stop_trading(self):
        """멀티 매매 중지"""
        self.is_running = False
        
        # UI 업데이트
        self.start_btn.setText(t("multi.start", "▶ 시작"))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d26a, stop:1 #00a854);
                color: white; font-weight: bold;
                padding: 10px 25px; border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover { background: #00a854; }
        """)
        
        # 상태 타이머 중지
        self.status_timer.stop()
        
        # 상태 초기화
        self.watching_label.setText(t("multi.watching", "├─ 감시 중: 0개"))
        self.pending_label.setText(t("multi.pending", "├─ 시그널 대기: 없음"))
        self.position_label.setText(t("multi.current_position", "└─ 현재 매매: 없음"))
        
        # 시그널 발생
        self.stop_signal.emit()
        logger.info("[Multi] 중지")
    
    def _update_status_display(self):
        """현황 표시 업데이트 (외부에서 호출 가능)"""
        # 이 메서드는 TradingDashboard에서 MultiTrader 상태를 받아 호출
    
    def update_status(self, watching: int = 0, pending: list = None, position: dict = None):
        """외부에서 상태 업데이트"""
        # 감시 중
        self.watching_label.setText(f"├─ 감시 중: {watching}개")
        
        # 시그널 대기
        if pending and len(pending) > 0:
            symbols = ", ".join([p.get('symbol', '') for p in pending[:3]])
            self.pending_label.setText(f"├─ 시그널 대기: {len(pending)}개 ({symbols})")
            self.pending_label.setStyleSheet("color: #ffd93d; font-size: 12px;")
        else:
            self.pending_label.setText("├─ 시그널 대기: 없음")
            self.pending_label.setStyleSheet("color: #a0aec0; font-size: 12px;")
        
        # 현재 포지션
        if position:
            symbol = position.get('symbol', '')
            direction = position.get('direction', '')
            pnl = position.get('pnl', 0)
            pnl_str = f"+{pnl:.2f}%" if pnl >= 0 else f"{pnl:.2f}%"
            pnl_color = "#00d26a" if pnl >= 0 else "#ff4757"
            self.position_label.setText(f"└─ 현재 매매: {symbol} {direction} {pnl_str}")
            self.position_label.setStyleSheet(f"color: {pnl_color}; font-size: 12px; font-weight: bold;")
        else:
            self.position_label.setText("└─ 현재 매매: 없음")
            self.position_label.setStyleSheet("color: #a0aec0; font-size: 12px;")
    
    def get_config(self) -> dict:
        """현재 설정 반환"""
        return {
            'exchange': self.exchange_combo.currentText().lower(),
            'watch_count': self.watch_spin.value(),
            'max_positions': self.max_pos_spin.value(),
            'leverage': self.leverage_spin.value(),
            'seed': self.seed_spin.value(),
            'capital_mode': 'compound' if self.mode_combo.currentIndex() == 0 else 'fixed'
        }

    # [NEW] 전문 검증 시스템(v2.2) 호환성용 메서드
    def _on_start(self):
        """멀티 매매 시작 (레거시/검증용)"""
        self._start_trading()

    def _on_stop(self):
        """멀티 매매 중지 (레거시/검증용)"""
        self._stop_trading()
