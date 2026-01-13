"""
StarU 나우캐스트 설정 위젯
- 기준 TF 선택
- 나우캐스트 TF 체크박스 (1m ~ 1w)

# Logging
import logging
logger = logging.getLogger(__name__)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QCheckBox, QComboBox, QLabel, QPushButton,
    QFrame
)
from PyQt5.QtCore import pyqtSignal


class NowcastWidget(QWidget):
    """나우캐스트 TF 선택 위젯"""
    
    # 시그널
    base_tf_changed = pyqtSignal(str)  # 기준 TF 변경
    nowcast_tf_changed = pyqtSignal(list)  # 선택된 TF 목록 변경
    connect_requested = pyqtSignal()  # 연결 요청
    disconnect_requested = pyqtSignal()  # 연결 해제 요청
    
    # TF 그룹 정의
    TF_GROUPS = {
        '분봉': ['1m', '3m', '5m', '15m', '30m'],
        '시간봉': ['1h', '2h', '4h', '6h', '12h'],
        '일봉+': ['1d', '3d', '1w'],
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tf_checkboxes: dict = {}
        self._is_connected = False
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 메인 그룹박스
        main_group = QGroupBox("🔴 나우캐스트 설정")
        main_layout = QVBoxLayout(main_group)
        
        # ===== 1. 기준 TF 선택 =====
        base_tf_layout = QHBoxLayout()
        
        base_tf_label = QLabel("기준 TF (차트 표시):")
        base_tf_label.setStyleSheet("font-weight: bold;")
        base_tf_layout.addWidget(base_tf_label)
        
        self.base_tf_combo = QComboBox()
        all_tfs = []
        for tfs in self.TF_GROUPS.values():
            all_tfs.extend(tfs)
        self.base_tf_combo.addItems(all_tfs)
        self.base_tf_combo.setCurrentText("15m")  # 15분 기본 (ATR용)
        self.base_tf_combo.currentTextChanged.connect(self._on_base_tf_changed)
        self.base_tf_combo.setMinimumWidth(80)
        base_tf_layout.addWidget(self.base_tf_combo)
        
        base_tf_layout.addStretch()
        
        # 연결 상태
        self.status_label = QLabel("● 대기")
        self.status_label.setStyleSheet("color: #8b949e;")
        base_tf_layout.addWidget(self.status_label)
        
        main_layout.addLayout(base_tf_layout)
        
        # 구분선
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setStyleSheet("background-color: #30363d;")
        main_layout.addWidget(line1)
        
        # ===== 2. 나우캐스트 TF 체크박스 =====
        tf_label = QLabel("나우캐스트 TF 선택:")
        tf_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        main_layout.addWidget(tf_label)
        
        # TF 그룹별 체크박스
        for group_name, tfs in self.TF_GROUPS.items():
            group_layout = QHBoxLayout()
            
            # 그룹 라벨
            group_label = QLabel(f"{group_name}:")
            group_label.setFixedWidth(60)
            group_label.setStyleSheet("color: #8b949e;")
            group_layout.addWidget(group_label)
            
            # 체크박스들
            for tf in tfs:
                cb = QCheckBox(tf)
                cb.setStyleSheet("""
                    QCheckBox {
                        spacing: 5px;
                        padding: 3px 8px;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                        border-radius: 3px;
                        border: 2px solid #30363d;
                        background-color: #21262d;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #238636;
                        border-color: #238636;
                    }
                    QCheckBox::indicator:hover {
                        border-color: #ffd700;
                    }
                """)
                # 1h 기본 체크 (패턴 감지용)
                if tf == "1h":
                    cb.setChecked(True)
                cb.toggled.connect(self._on_tf_toggled)
                self.tf_checkboxes[tf] = cb
                group_layout.addWidget(cb)
            
            group_layout.addStretch()
            main_layout.addLayout(group_layout)
        
        # 구분선
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #30363d;")
        main_layout.addWidget(line2)
        
        # ===== 3. 빠른 선택 버튼 =====
        quick_layout = QHBoxLayout()
        
        btn_style = """
            QPushButton {
                background-color: #2962FF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5c8aff;
            }
        """
        
        self.select_all_btn = QPushButton("전체 선택")
        self.select_all_btn.clicked.connect(self._select_all)
        self.select_all_btn.setStyleSheet(btn_style)
        self.select_all_btn.setMinimumWidth(80)
        quick_layout.addWidget(self.select_all_btn)
        
        self.clear_all_btn = QPushButton("전체 해제")
        self.clear_all_btn.clicked.connect(self._clear_all)
        self.clear_all_btn.setStyleSheet(btn_style.replace("#2962FF", "#ef5350").replace("#5c8aff", "#f06560"))
        self.clear_all_btn.setMinimumWidth(80)
        quick_layout.addWidget(self.clear_all_btn)
        
        self.select_common_btn = QPushButton("주요 TF")
        self.select_common_btn.setToolTip("5m, 15m, 1h, 4h, 1d")
        self.select_common_btn.clicked.connect(self._select_common)
        self.select_common_btn.setStyleSheet(btn_style.replace("#2962FF", "#7c4dff").replace("#5c8aff", "#9c6dff"))
        self.select_common_btn.setMinimumWidth(80)
        quick_layout.addWidget(self.select_common_btn)
        
        quick_layout.addStretch()
        
        # 선택된 TF 개수
        self.selected_count_label = QLabel("선택: 0개")
        self.selected_count_label.setStyleSheet("color: #8b949e;")
        quick_layout.addWidget(self.selected_count_label)
        
        main_layout.addLayout(quick_layout)
        
        # ===== 4. 연결 버튼 =====
        btn_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("🔗 WebSocket 연결")
        self.connect_btn.setObjectName("startBtn")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.connect_btn.setMinimumHeight(35)
        btn_layout.addWidget(self.connect_btn)
        
        main_layout.addLayout(btn_layout)
        
        # ===== 5. 수신 정보 =====
        info_layout = QHBoxLayout()
        
        self.ws_tf_label = QLabel("수신 TF: 1m (자동)")
        self.ws_tf_label.setStyleSheet("color: #58a6ff; font-size: 11px;")
        info_layout.addWidget(self.ws_tf_label)
        
        info_layout.addStretch()
        
        self.info_label = QLabel("ℹ️ 1분봉 수신 → 선택된 TF 실시간 계산")
        self.info_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        info_layout.addWidget(self.info_label)
        
        main_layout.addLayout(info_layout)
        
        layout.addWidget(main_group)
    
    # ===== 이벤트 핸들러 =====
    def _on_base_tf_changed(self, tf: str):
        """기준 TF 변경"""
        self.base_tf_changed.emit(tf)
    
    def _on_tf_toggled(self):
        """TF 체크박스 토글"""
        selected = self.get_selected_timeframes()
        self.selected_count_label.setText(f"선택: {len(selected)}개")
        self.nowcast_tf_changed.emit(selected)
    
    def _on_connect_clicked(self):
        """연결 버튼 클릭"""
        if self._is_connected:
            self.disconnect_requested.emit()
        else:
            self.connect_requested.emit()
    
    def _select_all(self):
        """전체 선택"""
        for cb in self.tf_checkboxes.values():
            cb.setChecked(True)
    
    def _clear_all(self):
        """전체 해제"""
        for cb in self.tf_checkboxes.values():
            cb.setChecked(False)
    
    def _select_common(self):
        """주요 TF 선택 (5m, 15m, 1h, 4h, 1d)"""
        common_tfs = ['5m', '15m', '1h', '4h', '1d']
        for tf, cb in self.tf_checkboxes.items():
            cb.setChecked(tf in common_tfs)
    
    # ===== 외부 인터페이스 =====
    def get_base_timeframe(self) -> str:
        """기준 TF 반환"""
        return self.base_tf_combo.currentText()
    
    def get_selected_timeframes(self) -> list:
        """선택된 나우캐스트 TF 목록 반환"""
        return [tf for tf, cb in self.tf_checkboxes.items() if cb.isChecked()]
    
    def set_selected_timeframes(self, tfs: list):
        """TF 선택 설정"""
        for tf, cb in self.tf_checkboxes.items():
            cb.setChecked(tf in tfs)
    
    def set_connection_status(self, connected: bool, status_text: str = None):
        """연결 상태 업데이트"""
        self._is_connected = connected
        
        if connected:
            self.status_label.setText("● 연결됨")
            self.status_label.setStyleSheet("color: #3fb950;")
            self.connect_btn.setText("⏹ 연결 해제")
            self.connect_btn.setObjectName("emergencyBtn")
        else:
            status = status_text or "대기"
            self.status_label.setText(f"● {status}")
            self.status_label.setStyleSheet("color: #8b949e;")
            self.connect_btn.setText("🔗 WebSocket 연결")
            self.connect_btn.setObjectName("startBtn")
        
        # 스타일 새로고침
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
    
    def set_connecting(self):
        """연결 중 상태"""
        self.status_label.setText("● 연결중...")
        self.status_label.setStyleSheet("color: #ffd700;")
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("연결중...")
    
    def set_enabled_connect_btn(self, enabled: bool):
        """연결 버튼 활성화/비활성화"""
        self.connect_btn.setEnabled(enabled)


# ===== 테스트 =====
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    # 스타일 적용
    try:
        from styles import StarUTheme
        style = StarUTheme.get_stylesheet()
    except ImportError:
        style = """
            QWidget { background-color: #0d1117; color: #f0f6fc; }
            QGroupBox { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-top: 12px; padding: 15px; }
            QGroupBox::title { color: #ffd700; }
            QPushButton { background-color: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 8px 16px; }
            QPushButton:hover { border-color: #ffd700; }
            QPushButton#startBtn { background-color: #238636; border: none; color: white; }
            QPushButton#emergencyBtn { background-color: #da3633; border: none; color: white; }
            QComboBox { background-color: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 8px; }
        """
    
    app = QApplication(sys.argv)
    app.setStyleSheet(style)
    
    widget = NowcastWidget()
    widget.setWindowTitle("나우캐스트 설정 테스트")
    widget.setMinimumWidth(500)
    
    # 시그널 테스트
    widget.base_tf_changed.connect(lambda tf: logger.info(f"기준 TF: {tf}"))
    widget.nowcast_tf_changed.connect(lambda tfs: logger.info(f"선택된 TF: {tfs}"))
    widget.connect_requested.connect(lambda: logger.info("연결 요청"))
    widget.disconnect_requested.connect(lambda: logger.info("연결 해제 요청"))
    
    widget.show()
    sys.exit(app.exec_())
