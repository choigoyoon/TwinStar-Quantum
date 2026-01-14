"""
Unified Auto-Trading Pipeline UI (Step-by-Step)

# Logging
import logging
logger = logging.getLogger(__name__)
Step 1: Symbol Selection
Step 2: Batch Optimization
Step 3: Backtest Verification
Step 4: Scanner Configuration
Step 5: Live Dashboard
"""
import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget, 
    QPushButton, QListWidget, QComboBox, QGroupBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidgetItem,
    QAbstractItemView, QMessageBox, QSpinBox, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer

# Add project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# from core.exchange_factory import ExchangeFactory  # [REMOVED]

class StepWidget(QWidget):
    """Base class for pipeline steps"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(title)
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50; margin-bottom: 10px;")
        self.layout.addWidget(header)
        
        # Content placeholder
        self.content_layout = QVBoxLayout()
        self.layout.addLayout(self.content_layout)
        
        # Navigation Buttons
        self.nav_layout = QHBoxLayout()
        self.nav_layout.addStretch()
        self.layout.addLayout(self.nav_layout)

    def add_nav_buttons(self, back_cb=None, next_cb=None, next_text="Next >"):
        if back_cb:
            btn_back = QPushButton("< Back")
            btn_back.clicked.connect(back_cb)
            btn_back.setStyleSheet("background: #555; color: white; padding: 8px 20px;")
            self.nav_layout.addWidget(btn_back)
            
        if next_cb:
            btn_next = QPushButton(next_text)
            btn_next.clicked.connect(next_cb)
            btn_next.setStyleSheet("background: #4CAF50; color: white; padding: 8px 20px; font-weight: bold;")
            self.nav_layout.addWidget(btn_next)

class AutoPipelineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_symbols = []
        self._init_ui()
        
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Progress Indicator
        self.step_indicators = QHBoxLayout()
        self.labels = ["1. Symbol", "2. Optimize", "3. Verify", "4. Config", "5. Live"]
        self.label_widgets = []
        
        for i, text in enumerate(self.labels):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #666; font-weight: bold; background: #222; padding: 8px; border-radius: 4px;")
            self.step_indicators.addWidget(lbl)
            self.label_widgets.append(lbl)
            if i < len(self.labels)-1:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: #444;")
                self.step_indicators.addWidget(arrow)
                
        main_layout.addLayout(self.step_indicators)
        
        # Stacked Widget
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # --- Create Steps ---
        self.step1 = self._create_step1()
        self.step2 = self._create_step2()
        self.step3 = self._create_step3()
        self.step4 = self._create_step4()
        self.step5 = self._create_step5()
        
        self.stack.addWidget(self.step1)
        self.stack.addWidget(self.step2)
        self.stack.addWidget(self.step3)
        self.stack.addWidget(self.step4)
        self.stack.addWidget(self.step5)
        
        self._update_indicators(0)

    def _update_indicators(self, index):
        for i, lbl in enumerate(self.label_widgets):
            if i == index:
                lbl.setStyleSheet("color: white; background: #4CAF50; font-weight: bold; padding: 8px; border-radius: 4px;")
            elif i < index:
                lbl.setStyleSheet("color: #aaa; background: #333; padding: 8px; border-radius: 4px;")
            else:
                lbl.setStyleSheet("color: #666; background: #222; padding: 8px; border-radius: 4px;")

    def _go_next(self):
        curr = self.stack.currentIndex()
        if curr < self.stack.count() - 1:
            self.stack.setCurrentIndex(curr + 1)
            self._update_indicators(curr + 1)

    def _go_back(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self.stack.setCurrentIndex(curr - 1)
            self._update_indicators(curr - 1)

    # ==========================
    # STEP 1: Symbol Selection
    # ==========================
    def _create_step1(self):
        step = StepWidget("Step 1: Select Target Symbols")
        
        # Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel("Exchange:"))
        self.ex_combo = QComboBox()
        self.ex_combo.addItems(["bybit", "binance", "okx"])
        self.ex_combo.setStyleSheet("background: #333; color: white;")
        ctrl_layout.addWidget(self.ex_combo)
        
        btn_load = QPushButton("Load Top Volume")
        btn_load.clicked.connect(self._load_symbols)
        btn_load.setStyleSheet("background: #007bff; color: white;")
        ctrl_layout.addWidget(btn_load)
        
        ctrl_layout.addStretch()
        step.content_layout.addLayout(ctrl_layout)
        
        # Checkbox List
        self.symbol_list = QListWidget()
        self.symbol_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.symbol_list.setStyleSheet("background: #1e1e1e; color: white;")
        step.content_layout.addWidget(self.symbol_list)
        
        # Selection info
        self.sel_label = QLabel("Selected: 0")
        step.content_layout.addWidget(self.sel_label)
        
        # Connect
        self.symbol_list.itemChanged.connect(self._update_selection_count)
        
        # Nav
        step.add_nav_buttons(next_cb=self._go_next)
        return step

    def _load_symbols(self):
        # Determine exchange
        ex_name = self.ex_combo.currentText()
        
        try:
            from exchanges.exchange_manager import get_exchange_manager
            em = get_exchange_manager()
            
            # Check connection
            if not em.test_connection(ex_name):
                # Try connect if config exists, else mock/warn
                # For UI purpose, we assume keys are set or we use public API if possible.
                # However, ExchangeManager structure mandates keys.
                # If fail, fallback to Top 10 hardcoded (Safety) with Warning.
                pass

            exchange = em.get_exchange(ex_name)
            if not exchange:
                 QMessageBox.warning(self, "Connection Error", f"Could not connect to {ex_name}. setup keys in settings or using fallback.")
                 # Fallback logic below
                 self._load_fallback_symbols(ex_name)
                 return

            # Fetch Tickers (Real Logic)
            # Assuming exchange.exchange is the ccxt instance
            if hasattr(exchange, 'exchange'):
                self.sel_label.setText("Fetching market data...")
                QApplication.processEvents()
                
                tickers = exchange.exchange.fetch_tickers()
                # Filter USDT
                usdt_pairs = [
                    (s, t['quoteVolume']) 
                    for s, t in tickers.items() 
                    if 'USDT' in s and t['quoteVolume'] is not None
                ]
                # Sort by Volume
                usdt_pairs.sort(key=lambda x: x[1], reverse=True)
                
                top_50 = [p[0] for p in usdt_pairs[:50]]
                
                self.symbol_list.clear()
                for sym in top_50:
                    symbol_clean = sym.replace('/', '') # Unified format
                    # Special handling for Bybit usually BTCUSDT vs BTC/USDT:USDT
                    # Just use clean text for display.
                    
                    item = QListWidgetItem(symbol_clean)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    # Check top 5 by default
                    if top_50.index(sym) < 5:
                         item.setCheckState(Qt.CheckState.Checked)
                    else:
                         item.setCheckState(Qt.CheckState.Unchecked)
                    self.symbol_list.addItem(item)
                    
                self._update_selection_count()
                QMessageBox.information(self, "Success", f"Loaded top {len(top_50)} volume symbols from {ex_name}")
                return

        except Exception as e:
            logger.info(f"Error loading symbols: {e}")
            self._load_fallback_symbols(ex_name)

    def _load_fallback_symbols(self, ex_name):
        self.symbol_list.clear()
        # Add Top Coins (Fallback)
        top_coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "BNBUSDT", "TRXUSDT", "LINKUSDT", "MATICUSDT"]
        for sym in top_coins:
            item = QListWidgetItem(sym)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked) 
            self.symbol_list.addItem(item)
        self._update_selection_count()

    def _update_selection_count(self):
        count = 0
        self.selected_symbols = []
        for i in range(self.symbol_list.count()):
            item = self.symbol_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                count += 1
                self.selected_symbols.append(item.text())
        self.sel_label.setText(f"Selected: {count}")

    # ==========================
    # STEP 2: Batch Optimization
    # ==========================
    def _create_step2(self):
        step = StepWidget("Step 2: Batch Optimization")
        
        # Mode Selection
        from PyQt6.QtWidgets import QFormLayout, QSpinBox
        
        config_group = QGroupBox("Configuration")
        form_layout = QFormLayout(config_group)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Quick (Default Params)", "Standard (Grid Search)"])
        self.mode_combo.setCurrentIndex(1) # Default to Standard
        self.mode_combo.setStyleSheet("background: #333; color: white; padding: 5px;")
        form_layout.addRow("Optimization Mode:", self.mode_combo)
        
        # Strict Filters
        self.opt_min_wr = QSpinBox()
        self.opt_min_wr.setRange(0, 100)
        self.opt_min_wr.setValue(70) # Strict Default
        self.opt_min_wr.setSuffix("%")
        self.opt_min_wr.setStyleSheet("background: #333; color: white;")
        form_layout.addRow("Min Win Rate:", self.opt_min_wr)
        
        self.opt_max_mdd = QSpinBox()
        self.opt_max_mdd.setRange(1, 100)
        self.opt_max_mdd.setValue(20) # Strict Default
        self.opt_max_mdd.setSuffix("%")
        self.opt_max_mdd.setStyleSheet("background: #333; color: white;")
        form_layout.addRow("Max MDD:", self.opt_max_mdd)
        
        self.opt_min_trades = QSpinBox()
        self.opt_min_trades.setRange(1, 1000)
        self.opt_min_trades.setValue(30) # Strict Default
        self.opt_min_trades.setStyleSheet("background: #333; color: white;")
        form_layout.addRow("Min Trades:", self.opt_min_trades)
        
        step.content_layout.addWidget(config_group)
        
        # Info
        self.target_label = QLabel("Waiting for selection...")
        self.target_label.setStyleSheet("color: #aaa; margin: 10px 0;")
        step.content_layout.addWidget(self.target_label)
        
        # Progress
        self.batch_progress = QProgressBar()
        self.batch_progress.setStyleSheet("""
            QProgressBar { border: 1px solid #444; border-radius: 5px; text-align: center; height: 25px; color: white; }
            QProgressBar::chunk { background: #4CAF50; }
        """)
        step.content_layout.addWidget(self.batch_progress)
        
        self.status_log = QLabel("Ready")
        self.status_log.setStyleSheet("color: #00d4ff; font-weight: bold;")
        step.content_layout.addWidget(self.status_log)
        
        # Control Buttons
        btn_layout = QHBoxLayout()
        self.btn_start_opt = QPushButton("Start Optimization")
        self.btn_start_opt.clicked.connect(self._start_optimization)
        self.btn_start_opt.setStyleSheet("background: #2196F3; color: white; font-weight: bold; padding: 10px;")
        btn_layout.addWidget(self.btn_start_opt)
        step.content_layout.addLayout(btn_layout)
        
        step.add_nav_buttons(back_cb=self._go_back, next_cb=self._go_next)
        return step

    def _start_optimization(self):
        if not self.selected_symbols:
            QMessageBox.warning(self, "Warning", "No symbols selected in Step 1")
            return
            
        # Get Config
        min_wr = self.opt_min_wr.value()
        max_mdd = self.opt_max_mdd.value()
        min_trades = self.opt_min_trades.value()
        
        self.target_label.setText(f"Target: {len(self.selected_symbols)} symbols (WR>={min_wr}%, MDD<={max_mdd}%)")
        self.batch_progress.setValue(0)
        self.batch_progress.setMaximum(len(self.selected_symbols))
        self.btn_start_opt.setEnabled(False)
        self.status_log.setText("Initializing Batch Optimizer...")
        
        # Run in Thread
        from PyQt6.QtCore import QThread, pyqtSignal
        
        class OptimizerThread(QThread):
            progress_updated = pyqtSignal(int, int, str)
            status_updated = pyqtSignal(str)
            finished_signal = pyqtSignal(dict)
            
            def __init__(self, symbols, wr, mdd, trades):
                super().__init__()
                self.symbols = symbols
                self.wr = wr
                self.mdd = mdd
                self.trades = trades
                
            def run(self):
                try:
                    from core.batch_optimizer import BatchOptimizer
                    optimizer = BatchOptimizer(
                        exchange='bybit', # Default
                        min_win_rate=float(self.wr),
                        max_mdd=float(self.mdd),
                        min_trades=int(self.trades)
                    )
                    # Inject selected symbols
                    optimizer.symbols = self.symbols
                    
                    optimizer.set_callbacks(
                        status_cb=lambda msg: self.status_updated.emit(msg),
                        progress_cb=lambda c, t, s: self.progress_updated.emit(c, t, s)
                    )
                    
                    summary = optimizer.run()
                    self.finished_signal.emit(summary)
                except Exception as e:
                    self.status_updated.emit(f"Error: {e}")
                    import traceback
                    traceback.print_exc()

        self.opt_thread = OptimizerThread(self.selected_symbols, min_wr, max_mdd, min_trades)
        self.opt_thread.progress_updated.connect(self._on_opt_progress)
        self.opt_thread.status_updated.connect(self._on_opt_status)
        self.opt_thread.finished_signal.connect(self._on_opt_finished)
        self.opt_thread.start()
        
    def _on_opt_progress(self, current, total, symbol):
        self.batch_progress.setMaximum(total)
        self.batch_progress.setValue(current)
        
    def _on_opt_status(self, msg):
        self.status_log.setText(msg)
        
    def _on_opt_finished(self, summary):
        self.btn_start_opt.setEnabled(True)
        msg = f"Completed!\nSuccess: {summary['success']}\nFailed: {summary['failed']}"
        QMessageBox.information(self, "Optimization Done", msg)
        self.status_log.setText("Optimization Complete")
        # Auto advance if success > 0
        if summary['success'] > 0:
            self._go_next()

    # ==========================
    # STEP 3: Unified Backtest
    # ==========================
    def _create_step3(self):
        step = StepWidget("Step 3: Unified Backtest (Timestamp-based)")
        
        info_label = QLabel("Simulates trading across ALL verified presets with a Single Position Rule.\nSorts signals by timestamp to emulate real deployment.")
        info_label.setStyleSheet("color: #aaa; margin-bottom: 10px;")
        step.content_layout.addWidget(info_label)
        
        # Result Summary
        stats_group = QGroupBox("Portfolio Performance")
        sl = QGridLayout()
        
        # Labels
        self.ub_trades_lbl = QLabel("0")
        self.ub_wr_lbl = QLabel("0.0%")
        self.ub_pnl_lbl = QLabel("0.0%")
        self.ub_mdd_lbl = QLabel("0.0%")
        self.ub_pf_lbl = QLabel("0.00")
        
        # Style
        for l in [self.ub_trades_lbl, self.ub_wr_lbl, self.ub_pnl_lbl, self.ub_mdd_lbl, self.ub_pf_lbl]:
             l.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        
        sl.addWidget(QLabel("Total Trades:"), 0, 0)
        sl.addWidget(self.ub_trades_lbl, 0, 1)
        sl.addWidget(QLabel("Win Rate:"), 0, 2)
        sl.addWidget(self.ub_wr_lbl, 0, 3)
        sl.addWidget(QLabel("Total PnL:"), 1, 0)
        sl.addWidget(self.ub_pnl_lbl, 1, 1)
        sl.addWidget(QLabel("Max MDD:"), 1, 2)
        sl.addWidget(self.ub_mdd_lbl, 1, 3)
        sl.addWidget(QLabel("Profit Factor:"), 2, 0)
        sl.addWidget(self.ub_pf_lbl, 2, 1)
        
        stats_group.setLayout(sl)
        step.content_layout.addWidget(stats_group)
        
        # Progress
        self.ub_progress = QProgressBar()
        self.ub_progress.setStyleSheet("""
            QProgressBar { border: 1px solid #444; border-radius: 5px; text-align: center; height: 25px; color: white; }
            QProgressBar::chunk { background: #9C27B0; }
        """)
        step.content_layout.addWidget(self.ub_progress)
        
        self.ub_status = QLabel("Ready to Simulate")
        self.ub_status.setStyleSheet("color: #00d4ff;")
        step.content_layout.addWidget(self.ub_status)

        # Action Button
        btn_run = QPushButton("Run Unified Simulation")
        btn_run.clicked.connect(self._run_unified_backtest)
        btn_run.setStyleSheet("background: #9C27B0; color: white; font-weight: bold; padding: 12px;")
        step.content_layout.addWidget(btn_run)

        step.add_nav_buttons(back_cb=self._go_back, next_cb=self._go_next)
        return step

    def _run_unified_backtest(self):
        self.btn_start_opt.setEnabled(False) # Reuse logic if button exposed
        self.ub_status.setText("Initializing Unified Backtest...")
        self.ub_progress.setValue(0)
        
        from PyQt6.QtCore import QThread, pyqtSignal
        
        class UBThread(QThread):
            progress = pyqtSignal(int, int, str)
            finished = pyqtSignal(object) # UnifiedResult
            error = pyqtSignal(str)
            
            def run(self):
                try:
                    from core.unified_backtest import UnifiedBacktest
                    ub = UnifiedBacktest(max_positions=1)
                    res = ub.run(progress_callback=lambda c, t, s: self.progress.emit(c, t, s))
                    self.finished.emit(res)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.error.emit(str(e))

        self.ub_thread = UBThread()
        self.ub_thread.progress.connect(self._on_ub_progress)
        self.ub_thread.finished.connect(self._on_ub_finished)
        self.ub_thread.error.connect(self._on_ub_error)
        self.ub_thread.start()
        
    def _on_ub_progress(self, current, total, status):
        self.ub_progress.setMaximum(total)
        self.ub_progress.setValue(current)
        self.ub_status.setText(status)
        
    def _on_ub_error(self, err):
        QMessageBox.critical(self, "Backtest Error", err)
        self.ub_status.setText("Error occurred.")
        
    def _on_ub_finished(self, result):
        if not result:
            self.ub_status.setText("No trades generated or no presets found.")
            return
            
        # Update UI
        self.ub_trades_lbl.setText(str(result.total_trades))
        self.ub_wr_lbl.setText(f"{result.win_rate:.1f}%")
        self.ub_pnl_lbl.setText(f"{result.total_pnl_percent:.1f}%")
        self.ub_mdd_lbl.setText(f"{result.max_drawdown:.1f}%")
        self.ub_pf_lbl.setText(f"{result.profit_factor:.2f}")
        
        self.ub_status.setText("Simulation Complete.")
        QMessageBox.information(self, "Result", f"Win Rate: {result.win_rate:.1f}%\nTotal PnL: {result.total_pnl_percent:.1f}%")

    # ==========================
    # STEP 4: Scanner Config
    # ==========================
    def _create_step4(self):
        step = StepWidget("Step 4: Scanner Configuration")
        
        # Grid Layout for Settings
        from PyQt6.QtWidgets import QGridLayout, QDoubleSpinBox, QRadioButton, QTextEdit
        
        g_layout = QGridLayout()
        
        # Entry Amount
        g_layout.addWidget(QLabel("Entry Amount ($):"), 0, 0)
        self.entry_amt = QDoubleSpinBox()
        self.entry_amt.setRange(10, 10000)
        self.entry_amt.setValue(100)
        self.entry_amt.setStyleSheet("background: #333; color: white;")
        g_layout.addWidget(self.entry_amt, 0, 1)
        
        # Leverage
        g_layout.addWidget(QLabel("Leverage (x):"), 1, 0)
        self.leverage = QSpinBox()
        self.leverage.setRange(1, 50)
        self.leverage.setValue(3)
        self.leverage.setStyleSheet("background: #333; color: white;")
        g_layout.addWidget(self.leverage, 1, 1)
        
        # Max Positions
        g_layout.addWidget(QLabel("Max Positions:"), 2, 0)
        self.max_pos = QSpinBox()
        self.max_pos.setRange(1, 20)
        self.max_pos.setValue(1)
        self.max_pos.setStyleSheet("background: #333; color: white;")
        g_layout.addWidget(self.max_pos, 2, 1)
        
        step.content_layout.addLayout(g_layout)
        
        # Priority
        p_group = QGroupBox("Priority Logic")
        p_layout = QHBoxLayout(p_group)
        self.p_wr = QRadioButton("Win Rate (Highest First)")
        self.p_wr.setChecked(True)
        self.p_score = QRadioButton("Signal Score (Highest First)")
        p_layout.addWidget(self.p_wr)
        p_layout.addWidget(self.p_score)
        step.content_layout.addWidget(p_group)
        
        # Blacklist
        b_group = QGroupBox("Blacklist (Comma separated)")
        b_layout = QVBoxLayout(b_group)
        self.blacklist_edit = QTextEdit()
        self.blacklist_edit.setPlaceholderText("e.g. BTCUSDT, ETHUSDT")
        self.blacklist_edit.setMaximumHeight(60)
        self.blacklist_edit.setStyleSheet("background: #333; color: white;")
        b_layout.addWidget(self.blacklist_edit)
        step.content_layout.addWidget(b_group)
        
        # Start Button
        btn_start = QPushButton("🚀 Start Auto-Scanner")
        btn_start.clicked.connect(self._start_scanner)
        btn_start.setStyleSheet("background: #e91e63; color: white; font-weight: bold; padding: 12px; font-size: 14px;")
        step.content_layout.addWidget(btn_start)
        
        step.add_nav_buttons(back_cb=self._go_back)
        return step

    def _start_scanner(self):
        # Configure Scanner
        config = {
            'entry_amount': self.entry_amt.value(),
            'leverage': self.leverage.value(),
            'max_positions': self.max_pos.value(),
            'priority': 'win_rate' if self.p_wr.isChecked() else 'score',
            'blacklist': [x.strip() for x in self.blacklist_edit.toPlainText().split(',') if x.strip()],
            'interval': 1.5
        }
        
        # Init Scanner if needed
        if not hasattr(self, 'scanner'):
            try:
                from core.auto_scanner import AutoScanner
                self.scanner = AutoScanner(config)
                self.scanner.log_signal.connect(self._append_log)
                self.scanner.position_opened.connect(self._update_active_table)
            except ImportError:
                QMessageBox.critical(self, "Error", "AutoScanner module not found")
                return

        self.scanner.set_config(config)
        self.scanner.load_verified_symbols()
        self.scanner.start()
        
        self.dashboard_status.setText("RUNNING")
        self.dashboard_status.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 16px;")
        
        self._go_next()

    # ==========================
    # STEP 5: Live Dashboard
    # ==========================
    def _create_step5(self):
        step = StepWidget("Step 5: Live Auto-Trading Dashboard")
        
        # Status Header
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("System Status:"))
        self.dashboard_status = QLabel("STOPPED")
        self.dashboard_status.setStyleSheet("color: #FF5252; font-weight: bold; font-size: 16px;")
        h_layout.addWidget(self.dashboard_status)
        h_layout.addStretch()
        
        btn_stop = QPushButton("STOP SCANNER")
        btn_stop.clicked.connect(self._stop_scanner)
        btn_stop.setStyleSheet("background: #F44336; color: white; font-weight: bold;")
        h_layout.addWidget(btn_stop)
        
        step.content_layout.addLayout(h_layout)
        
        # Metrics Grid with Progress Bars
        m_group = QGroupBox("Pipeline Metrics")
        m_layout = QGridLayout(m_group)
        
        # Stage 1 Progress Bar
        self.metric_targets = QLabel("0")
        self.metric_targets.setStyleSheet("color: white; font-weight: bold; font-size: 14px; min-width: 30px;")
        self.stage1_progress = QProgressBar()
        self.stage1_progress.setRange(0, 50)
        self.stage1_progress.setValue(0)
        self.stage1_progress.setFormat("%v / 50")
        self.stage1_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #4a5568;
                border-radius: 5px;
                background: #2d3748;
                height: 20px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4aa, stop:1 #00b894);
                border-radius: 4px;
            }
        """)
        
        # Stage 2 Progress Bar
        self.metric_stage2 = QLabel("0")
        self.metric_stage2.setStyleSheet("color: white; font-weight: bold; font-size: 14px; min-width: 30px;")
        self.stage2_progress = QProgressBar()
        self.stage2_progress.setRange(0, 10)
        self.stage2_progress.setValue(0)
        self.stage2_progress.setFormat("%v / 10")
        self.stage2_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #4a5568;
                border-radius: 5px;
                background: #2d3748;
                height: 20px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ffd93d, stop:1 #f39c12);
                border-radius: 4px;
            }
        """)
        
        # Active Positions Progress Bar
        self.metric_active = QLabel("0")
        self.metric_active.setStyleSheet("color: white; font-weight: bold; font-size: 14px; min-width: 30px;")
        self.position_progress = QProgressBar()
        self.position_progress.setRange(0, 5)
        self.position_progress.setValue(0)
        self.position_progress.setFormat("%v / 5")
        self.position_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #4a5568;
                border-radius: 5px;
                background: #2d3748;
                height: 20px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff6b6b, stop:1 #ee5a24);
                border-radius: 4px;
            }
        """)
        
        # Layout with Progress Bars
        m_layout.addWidget(QLabel("Stage 1 Targets (4H):"), 0, 0)
        m_layout.addWidget(self.stage1_progress, 0, 1)
        m_layout.addWidget(self.metric_targets, 0, 2)
        
        m_layout.addWidget(QLabel("Stage 2 Monitors (15m):"), 1, 0)
        m_layout.addWidget(self.stage2_progress, 1, 1)
        m_layout.addWidget(self.metric_stage2, 1, 2)
        
        m_layout.addWidget(QLabel("Active Positions:"), 2, 0)
        m_layout.addWidget(self.position_progress, 2, 1)
        m_layout.addWidget(self.metric_active, 2, 2)
        
        step.content_layout.addWidget(m_group)
        

        
        # Active Positions
        step.content_layout.addWidget(QLabel("Active Positions Table"))
        self.pos_table = QTableWidget()
        self.pos_table.setColumnCount(4)
        self.pos_table.setHorizontalHeaderLabels(["Symbol", "Type", "Entry Price", "Size"])
        self.pos_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pos_table.setStyleSheet("background: #1a1a1a; color: white; gridline-color: #444;")
        self.pos_table.setMaximumHeight(150)
        step.content_layout.addWidget(self.pos_table)
        
        # Logs
        step.content_layout.addWidget(QLabel("Live Logs"))
        from PyQt6.QtWidgets import QTextEdit
        self.scan_log = QTextEdit()
        self.scan_log.setReadOnly(True)
        self.scan_log.setStyleSheet("background: #111; color: #00FF00; font-family: Consolas;")
        step.content_layout.addWidget(self.scan_log)
        
        # Dashboard Timer
        self.dash_timer = QTimer(self)
        self.dash_timer.timeout.connect(self._update_dashboard_metrics)
        self.dash_timer.start(1000)
        
        step.add_nav_buttons(back_cb=self._go_back)
        return step

    def _stop_scanner(self):
        if hasattr(self, 'scanner'):
            self.scanner.stop()
        self.dashboard_status.setText("STOPPED")
        self.dashboard_status.setStyleSheet("color: #FF5252; font-weight: bold; font-size: 16px;")
        self._append_log("Scanner Stopped by User.")
        if self.dash_timer.isActive():
            self.dash_timer.stop()

    def _append_log(self, msg):
        self.scan_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _update_dashboard_metrics(self):
        if hasattr(self, 'scanner') and self.scanner.running:
            # Stage 1 Count
            targets = len(self.scanner.verified_symbols)
            self.metric_targets.setText(str(targets))
            self.stage1_progress.setValue(min(targets, 50))
            
            # Stage 2 Count
            monitors = len(self.scanner.monitoring_candidates)
            self.metric_stage2.setText(str(monitors))
            self.stage2_progress.setValue(min(monitors, 10))
            
            # Active Count
            active = len(self.scanner.active_positions)
            self.metric_active.setText(str(active))
            self.position_progress.setValue(min(active, 5))
            
            # Status
            self.dashboard_status.setText("RUNNING (Stage 1 & 2 Active)")
            

    def _update_active_table(self, data):
        row = self.pos_table.rowCount()
        self.pos_table.insertRow(row)
        self.pos_table.setItem(row, 0, QTableWidgetItem(data['symbol']))
        self.pos_table.setItem(row, 1, QTableWidgetItem(data['direction']))
        self.pos_table.setItem(row, 2, QTableWidgetItem(str(data['price'])))
        self.pos_table.setItem(row, 3, QTableWidgetItem(str(data['size'])))

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = AutoPipelineWidget()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
