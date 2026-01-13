"""
Multi-Chain System Integrated UI
- 탭 1: Multi Optimizer (553개 심볼 순차 최적화)
- 탭 2: Multi Backtest (통합 시계열 포트폴리오 검증)
- 탭 3: Dual-Track Trader (BTC 고정 + 알트 복리 실매매)
"""

import sys
import os
import threading
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QTextEdit, QDoubleSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.multi_optimizer import MultiOptimizer
from core.multi_backtest import MultiBacktester
from core.dual_track_trader import DualTrackTrader

class LogSignal(QObject):
    """로그 전달용 시그널"""
    new_log = pyqtSignal(str)

class MultiSystemWidget(QWidget):
    """멀티체인 통합 시스템 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_signal = LogSignal()
        self.log_signal.new_log.connect(self._add_log)
        
        # 엔진 인스턴스
        self.optimizer = MultiOptimizer()
        self.backtester = MultiBacktester()
        self.trader = None # 필요 시 생성
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 제목
        title = QLabel("TwinStar Quantum - Multi-Chain System")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00d4ff; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # 탭 위젯
        self.tabs = QTabWidget()
        self.tabs.addTab(self._init_optimizer_tab(), "Multi Optimizer")
        self.tabs.addTab(self._init_backtest_tab(), "Multi Backtest")
        self.tabs.addTab(self._init_trader_tab(), "Dual-Track Trader")
        layout.addWidget(self.tabs)
        
        # 하단 로그 창
        log_group = QGroupBox("시스템 로그")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background: #1e1e1e; color: #dcdcdc; font-family: Consolas;")
        self.log_output.setFixedHeight(150)
        log_layout.addWidget(self.log_output)
        layout.addWidget(log_group)

    def _init_optimizer_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 컨트롤 영역
        ctrl_group = QGroupBox("최적화 설정")
        ctrl_layout = QHBoxLayout(ctrl_group)
        
        self.opt_exch_combo = QComboBox()
        self.opt_exch_combo.addItems(["Bybit", "Binance", "OKX", "Bitget"])
        ctrl_layout.addWidget(QLabel("Exchange:"))
        ctrl_layout.addWidget(self.opt_exch_combo)
        
        self.opt_resume_chk = QCheckBox("Resume Progress")
        self.opt_resume_chk.setChecked(True)
        ctrl_layout.addWidget(self.opt_resume_chk)
        
        self.run_opt_btn = QPushButton("▶ 최적화 시작 (553개 코인)")
        self.run_opt_btn.setStyleSheet("background: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.run_opt_btn.clicked.connect(self._run_multi_optimization)
        ctrl_layout.addWidget(self.run_opt_btn)
        
        self.stop_opt_btn = QPushButton("⏹ 중단")
        self.stop_opt_btn.setEnabled(False)
        self.stop_opt_btn.clicked.connect(self._stop_multi_optimization)
        ctrl_layout.addWidget(self.stop_opt_btn)
        
        layout.addWidget(ctrl_group)
        
        # 상태 표시
        self.opt_progress = QProgressBar()
        layout.addWidget(self.opt_progress)
        
        self.opt_status_label = QLabel("준비 완료")
        layout.addWidget(self.opt_status_label)
        
        # 저장된 프리셋 테이블
        self.preset_table = QTableWidget()
        self.preset_table.setColumnCount(4)
        self.preset_table.setHorizontalHeaderLabels(["심볼", "타임프레임", "승률", "생성일"])
        self.preset_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.preset_table)
        
        return widget

    def _init_backtest_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 설정 영역
        ctrl_group = QGroupBox("통합 백테스트 설정")
        ctrl_layout = QHBoxLayout(ctrl_group)
        
        self.bt_cap_spin = QDoubleSpinBox()
        self.bt_cap_spin.setRange(100, 100000)
        self.bt_cap_spin.setValue(1000)
        self.bt_cap_spin.setPrefix("Alt Cap: $")
        ctrl_layout.addWidget(self.bt_cap_spin)
        
        self.bt_btc_spin = QDoubleSpinBox()
        self.bt_btc_spin.setRange(10, 1000)
        self.bt_btc_spin.setValue(100)
        self.bt_btc_spin.setPrefix("BTC Fixed: $")
        ctrl_layout.addWidget(self.bt_btc_spin)
        
        self.run_bt_btn = QPushButton("📊 통합 시계열 백테스트 실행")
        self.run_bt_btn.setStyleSheet("background: #2196F3; color: white; font-weight: bold; padding: 8px;")
        self.run_bt_btn.clicked.connect(self._run_multi_backtest)
        ctrl_layout.addWidget(self.run_bt_btn)
        
        layout.addWidget(ctrl_group)
        
        # 결과 요약 레이블
        self.bt_result_label = QLabel("결과가 여기에 표시됩니다.")
        self.bt_result_label.setStyleSheet("font-size: 14px; background: #2b2b2b; padding: 10px; border-radius: 5px;")
        self.bt_result_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.bt_result_label)
        
        # 거래 내역 테이블
        self.bt_table = QTableWidget()
        self.bt_table.setColumnCount(6)
        self.bt_table.setHorizontalHeaderLabels(["시간", "심볼", "트랙", "수익률(%)", "수익($)", "잔고($)"])
        self.bt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.bt_table)
        
        return widget

    def _init_trader_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 실매매 컨트롤
        ctrl_group = QGroupBox("Dual-Track Trader 컨트롤")
        ctrl_layout = QHBoxLayout(ctrl_group)
        
        self.start_trader_btn = QPushButton("🚀 DUAL-TRACK TRADING START")
        self.start_trader_btn.setStyleSheet("background: #f44336; color: white; font-size: 16px; font-weight: bold; padding: 15px;")
        self.start_trader_btn.clicked.connect(self._toggle_trading)
        ctrl_layout.addWidget(self.start_trader_btn)
        
        layout.addWidget(ctrl_group)
        
        # 현황판 (Dashboards)
        stats_layout = QHBoxLayout()
        
        # BTC 트랙
        btc_group = QGroupBox("Track A: BTC Fixed")
        btc_layout = QVBoxLayout(btc_group)
        self.btc_status = QLabel("Position: IDLE\nFixed: $100\nTotal PnL: $0.00")
        self.btc_status.setStyleSheet("font-size: 14px; color: #ffeb3b;")
        btc_layout.addWidget(self.btc_status)
        stats_layout.addWidget(btc_group)
        
        # 알트 트랙
        alt_group = QGroupBox("Track B: Alt Compounding")
        alt_layout = QVBoxLayout(alt_group)
        self.alt_status = QLabel("Position: IDLE\nCapital: $1000.00\nReturn: 0.0%")
        self.alt_status.setStyleSheet("font-size: 14px; color: #4caf50;")
        alt_layout.addWidget(self.alt_status)
        stats_layout.addWidget(alt_group)
        
        layout.addLayout(stats_layout)
        
        # 헬스 체크 상태
        health_group = QGroupBox("프리셋 건강 상태 (Health Monitoring)")
        health_layout = QVBoxLayout(health_group)
        self.health_table = QTableWidget()
        self.health_table.setColumnCount(4)
        self.health_table.setHorizontalHeaderLabels(["심볼", "상태", "승률차이", "메시지"])
        self.health_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        health_layout.addWidget(self.health_table)
        layout.addWidget(health_group)
        
        return widget

    # --- 서비스 로직 ---

    def _add_log(self, text: str):
        self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

    def _run_multi_optimization(self):
        exch = self.opt_exch_combo.currentText()
        resume = self.opt_resume_chk.isChecked()
        
        def run_thread():
            self.optimizer.exchange = exch.lower()
            self.log_signal.new_log.emit(f"최적화 시작: {exch}")
            
            def progress_callback(cur, total, task, result):
                self.opt_progress.setMaximum(total)
                self.opt_progress.setValue(cur)
                self.opt_status_label.setText(f"진행 중: {task} ({cur}/{total})")
                if result:
                    self.log_signal.new_log.emit(f"✅ {task} 완료: {result.get('win_rate', 0)*100:.1f}%")
            
            self.optimizer.run(resume=resume, on_progress=progress_callback)
            self.log_signal.new_log.emit("모든 최적화 완료")
            
        self.run_opt_btn.setEnabled(False)
        self.stop_opt_btn.setEnabled(True)
        threading.Thread(target=run_thread, daemon=True).start()

    def _stop_multi_optimization(self):
        self.optimizer.stop()
        self.stop_opt_btn.setEnabled(False)
        self.run_opt_btn.setEnabled(True)
        self.log_signal.new_log.emit("최적화 중단 요청됨")

    def _run_multi_backtest(self):
        alt_cap = self.bt_cap_spin.value()
        btc_fixed = self.bt_btc_spin.value()
        
        def run_thread():
            self.log_signal.new_log.emit("통합 백테스트 엔진 가동...")
            tester = MultiBacktester(initial_alt_capital=alt_cap, btc_fixed_amount=btc_fixed)
            result = tester.execute_all()
            
            if 'error' in result:
                self.log_signal.new_log.emit(f"❌ 에러: {result.get('error', 'Unknown error')}")
                return
                
            s = result.get('summary', {})
            summary_text = (
                f"총 거래: {s.get('total_trades', 0)}회 | 승률: {s.get('win_rate', 0)*100:.1f}% | "
                f"최종 자본: ${s.get('final_alt_capital', 0)+s.get('total_btc_pnl', 0):.2f}\n"
                f"수익률: {s.get('total_return_pct', 0):.1f}% | MDD: {s.get('max_drawdown', 0):.1f}%"
            )
            self.bt_result_label.setText(summary_text)
            self.log_signal.new_log.emit("백테스트 완료")
            
            # 테이블 업데이트 (최근 50개만)
            self._update_bt_table(result.get('history', [])[-50:])
            
        threading.Thread(target=run_thread, daemon=True).start()

    def _update_bt_table(self, history):
        self.bt_table.setRowCount(len(history))
        for i, h in enumerate(history):
            self.bt_table.setItem(i, 0, QTableWidgetItem(str(h.get('time', ''))[11:19]))
            self.bt_table.setItem(i, 1, QTableWidgetItem(h.get('symbol', '')))
            self.bt_table.setItem(i, 2, QTableWidgetItem(h.get('track', '').upper()))
            self.bt_table.setItem(i, 3, QTableWidgetItem(f"{h.get('pnl_pct', 0):+.2f}"))
            self.bt_table.setItem(i, 4, QTableWidgetItem(f"{h.get('pnl_usd', 0):+.2f}"))
            self.bt_table.setItem(i, 5, QTableWidgetItem(f"{h.get('current_alt_cap', 0) + h.get('total_btc_pnl', 0):.2f}"))

    def _toggle_trading(self):
        if self.trader is None:
            # 시작
            self.start_trader_btn.setText("🛑 TRADING STOP")
            self.start_trader_btn.setStyleSheet("background: #607d8b; color: white; font-size: 16px; font-weight: bold; padding: 15px;")
            self.log_signal.new_log.emit("Dual-Track Trader 시작 (Dry-run)!")
            
            # [FIX] 실제 구동을 위한 더미 클라이언트 또는 안전한 초기화
            # 실제 구동을 위해서는 API 키가 있는 Exchange 객체가 필요하므로
            # 여기서는 매니저 객체만 생성하여 상태 관리를 시작함
            try:
                # 실제 구동을 위한 더미 클라이언트 또는 실교환 객체 생성
                # 여기서는 GUI의 기본 설정을 따르거나 빗썸/바이낸스 등 연동 가능
                try:
                    from exchanges.bybit_exchange import BybitExchange
                except ImportError:
                    pass
                client = BybitExchange(symbol='BTCUSDT') # 기본 BTC
                
                self.trader = DualTrackTrader(exchange_client=client) 
                self.trader.start_monitoring(symbols=['BTCUSDT']) 
                self.log_signal.new_log.emit("Dual-Track Trader 가동: BTCUSDT 모니터링 시작")
            except Exception as e:
                self.log_signal.new_log.emit(f"❌ Trader 시작 실패: {e}")
                self.trader = None
        else:
            # 중단
            self.start_trader_btn.setText("🚀 DUAL-TRACK TRADING START")
            self.start_trader_btn.setStyleSheet("background: #f44336; color: white; font-size: 16px; font-weight: bold; padding: 15px;")
            self.trader.stop_all()
            self.trader = None
            self.log_signal.new_log.emit("Dual-Track Trader 중단.")

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MultiSystemWidget()
    window.resize(1000, 800)
    window.show()
    sys.exit(app.exec_())
