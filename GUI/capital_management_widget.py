# capital_management_widget.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, 
    QSpinBox, QCheckBox, QGroupBox, QPushButton, QProgressBar,
    QFrame, QGridLayout
)
from PyQt5.QtCore import Qt
from capital_config import get_position_sizer, CapitalConfig

class CapitalManagementWidget(QWidget):
    """자금 관리 설정 및 계산기 위젯"""
    
    def __init__(self):
        super().__init__()
        self.sizer = get_position_sizer()
        self.config = self.sizer.config
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 1. 자금 설정 (Config)
        group_config = QGroupBox("Capital Configuration")
        config_layout = QGridLayout(group_config)
        config_layout.setVerticalSpacing(10)
        
        # Total Capital
        config_layout.addWidget(QLabel("Total Capital (USDT):"), 0, 0)
        self.spin_capital = QDoubleSpinBox()
        self.spin_capital.setRange(0, 10000000)
        self.spin_capital.setValue(self.config.total_capital)
        self.spin_capital.setPrefix("$ ")
        self.spin_capital.valueChanged.connect(self.update_config)
        config_layout.addWidget(self.spin_capital, 0, 1)
        
        # Risk per Trade
        config_layout.addWidget(QLabel("Risk per Trade (%):"), 1, 0)
        self.spin_risk = QDoubleSpinBox()
        self.spin_risk.setRange(0.1, 100.0)
        self.spin_risk.setValue(self.config.risk_per_trade)
        self.spin_risk.setSuffix(" %")
        self.spin_risk.setSingleStep(0.1)
        self.spin_risk.valueChanged.connect(self.update_config)
        config_layout.addWidget(self.spin_risk, 1, 1)
        
        # Max Leverage
        config_layout.addWidget(QLabel("Max Leverage:"), 2, 0)
        self.spin_leverage = QSpinBox()
        self.spin_leverage.setRange(1, 125)
        self.spin_leverage.setValue(self.config.max_leverage)
        self.spin_leverage.setSuffix(" x")
        self.spin_leverage.valueChanged.connect(self.update_config)
        config_layout.addWidget(self.spin_leverage, 2, 1)
        
        # Max Drawdown Limit
        config_layout.addWidget(QLabel("Max Drawdown Limit:"), 3, 0)
        self.spin_mdd = QDoubleSpinBox()
        self.spin_mdd.setRange(1.0, 100.0)
        self.spin_mdd.setValue(self.config.max_drawdown)
        self.spin_mdd.setSuffix(" %")
        self.spin_mdd.valueChanged.connect(self.update_config)
        config_layout.addWidget(self.spin_mdd, 3, 1)
        
        # Compounding
        self.chk_compounding = QCheckBox("Apply Compounding (Use Current Balance)")
        self.chk_compounding.setChecked(self.config.compounding)
        self.chk_compounding.toggled.connect(self.update_config)
        config_layout.addWidget(self.chk_compounding, 4, 0, 1, 2)
        
        layout.addWidget(group_config)
        
        # 2. 포지션 사이즈 계산기 (Calculator)
        group_calc = QGroupBox("Position Size Calculator")
        calc_layout = QVBoxLayout(group_calc)
        
        input_layout = QHBoxLayout()
        
        # Entry
        input_layout.addWidget(QLabel("Entry:"))
        self.spin_entry = QDoubleSpinBox()
        self.spin_entry.setRange(0, 1000000)
        self.spin_entry.setValue(50000)
        self.spin_entry.setDecimals(4)
        input_layout.addWidget(self.spin_entry)
        
        # Stop Loss
        input_layout.addWidget(QLabel("Stop Loss:"))
        self.spin_sl = QDoubleSpinBox()
        self.spin_sl.setRange(0, 1000000)
        self.spin_sl.setValue(49000)
        self.spin_sl.setDecimals(4)
        input_layout.addWidget(self.spin_sl)
        
        # Calculate Button
        btn_calc = QPushButton("Calculate")
        btn_calc.clicked.connect(self.calculate_position)
        btn_calc.setStyleSheet("background-color: #238636; color: white; font-weight: bold;")
        input_layout.addWidget(btn_calc)
        
        calc_layout.addLayout(input_layout)
        
        # Result Display
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet("background-color: #161b22; border-radius: 4px; padding: 10px;")
        res_layout = QGridLayout(self.result_frame)
        
        self.lbl_pos_value = QLabel("-")
        self.lbl_margin = QLabel("-")
        self.lbl_risk_amt = QLabel("-")
        self.lbl_leverage = QLabel("-")
        self.lbl_qty = QLabel("-")
        
        self._add_result_row(res_layout, 0, "Total Position Value:", self.lbl_pos_value)
        self._add_result_row(res_layout, 1, "Required Margin:", self.lbl_margin)
        self._add_result_row(res_layout, 2, "Risk Amount:", self.lbl_risk_amt)
        self._add_result_row(res_layout, 3, "Leverage:", self.lbl_leverage)
        self._add_result_row(res_layout, 4, "Quantity:", self.lbl_qty)
        
        calc_layout.addWidget(self.result_frame)
        layout.addWidget(group_calc)
        
        # 3. 현재 상태 (Status)
        group_status = QGroupBox("Current Status")
        status_layout = QVBoxLayout(group_status)
        
        status_layout.addWidget(QLabel("Current Drawdown:"))
        self.pbar_dd = QProgressBar()
        self.pbar_dd.setRange(0, 100)
        self.pbar_dd.setValue(0)
        self.pbar_dd.setFormat("%p%")
        status_layout.addWidget(self.pbar_dd)
        
        layout.addWidget(group_status)
        layout.addStretch()
        
    def _add_result_row(self, layout, row, label, value_widget):
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8b949e;")
        value_widget.setStyleSheet("color: #c9d1d9; font-weight: bold;")
        value_widget.setAlignment(Qt.AlignRight)
        layout.addWidget(lbl, row, 0)
        layout.addWidget(value_widget, row, 1)
        
    def update_config(self):
        """설정 업데이트"""
        self.config.total_capital = self.spin_capital.value()
        self.config.risk_per_trade = self.spin_risk.value()
        self.config.max_leverage = self.spin_leverage.value()
        self.config.max_drawdown = self.spin_mdd.value()
        self.config.compounding = self.chk_compounding.isChecked()
        
        # 저장
        from capital_config import save_capital_config
        save_capital_config(self.config)
        self.update_status()
        
    def calculate_position(self):
        """포지션 계산"""
        entry = self.spin_entry.value()
        sl = self.spin_sl.value()
        
        result = self.sizer.calculate_position_size(entry, sl)
        
        if result:
            # margin = size / leverage
            pos_size = result.get('position_size', 0)
            leverage = result.get('leverage', 1)
            margin = pos_size / leverage if leverage > 0 else 0
            
            self.lbl_pos_value.setText(f"$ {pos_size:,.2f}")
            self.lbl_margin.setText(f"$ {margin:,.2f}")
            self.lbl_risk_amt.setText(f"$ {result.get('risk_amount', 0):,.2f} ({result.get('risk_percent', 0):.2f}%)")
            self.lbl_leverage.setText(f"{leverage} x")
            self.lbl_qty.setText(f"{result.get('quantity', 0):.4f}")
        else:
            self.lbl_pos_value.setText("Error")
            
    def update_status(self):
        """상태 업데이트 (DD는 현재 모의 데이터)"""
        dd = 0.0 # self.cm.get_drawdown() -> 구현 필요 시 추후 연동
        self.pbar_dd.setValue(int(dd))
        
        # MDD 색상 변경
        if dd >= self.config.max_drawdown:
            self.pbar_dd.setStyleSheet("QProgressBar::chunk { background-color: #da3633; }")
        elif dd >= self.config.max_drawdown * 0.7:
            self.pbar_dd.setStyleSheet("QProgressBar::chunk { background-color: #d29922; }")
        else:
            self.pbar_dd.setStyleSheet("QProgressBar::chunk { background-color: #238636; }")


# 테스트
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = CapitalManagementWidget()
    window.setWindowTitle("Capital Management")
    window.resize(400, 600)
    window.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
    window.show()
    
    sys.exit(app.exec_())
