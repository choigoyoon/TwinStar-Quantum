# developer_mode_widget.py - 개발자 모드 위젯

from locales.lang_manager import t
import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTextEdit, QGridLayout, QSpinBox, QDoubleSpinBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class DeveloperModeWidget(QWidget):
    """개발자 모드 위젯 - 파라미터 최적화 및 디버그"""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 헤더
        header = QLabel("🔧 Developer Mode")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)
        
        # 탭
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2a2e3b; background: #131722; }
            QTabBar::tab { background: #1e2330; color: #787b86; padding: 10px 20px; }
            QTabBar::tab:selected { background: #131722; color: white; border-bottom: 2px solid #2962FF; }
        """)
        
        tabs.addTab(self._create_param_optimizer_tab(), "📊 Parameter Optimizer")
        tabs.addTab(self._create_log_tab(), "📝 Debug Log")
        tabs.addTab(self._create_system_tab(), "⚙️ System Info")
        
        layout.addWidget(tabs)
    
    def _create_param_optimizer_tab(self):
        """파라미터 최적화 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 심볼 선택
        symbol_layout = QHBoxLayout()
        symbol_layout.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])
        symbol_layout.addWidget(self.symbol_combo)
        symbol_layout.addStretch()
        layout.addLayout(symbol_layout)
        
        # 파라미터 그리드
        param_group = QGroupBox("Strategy Parameters")
        param_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        param_layout = QGridLayout(param_group)
        
        # MACD 파라미터
        param_layout.addWidget(QLabel("MACD Fast:"), 0, 0)
        self.macd_fast = QSpinBox()
        self.macd_fast.setRange(5, 20)
        self.macd_fast.setValue(12)
        param_layout.addWidget(self.macd_fast, 0, 1)
        
        param_layout.addWidget(QLabel("MACD Slow:"), 0, 2)
        self.macd_slow = QSpinBox()
        self.macd_slow.setRange(15, 50)
        self.macd_slow.setValue(26)
        param_layout.addWidget(self.macd_slow, 0, 3)
        
        param_layout.addWidget(QLabel("MACD Signal:"), 0, 4)
        self.macd_signal = QSpinBox()
        self.macd_signal.setRange(5, 15)
        self.macd_signal.setValue(9)
        param_layout.addWidget(self.macd_signal, 0, 5)
        
        # Swing 파라미터
        param_layout.addWidget(QLabel("Swing Length:"), 1, 0)
        self.swing_length = QSpinBox()
        self.swing_length.setRange(2, 10)
        self.swing_length.setValue(3)
        param_layout.addWidget(self.swing_length, 1, 1)
        
        param_layout.addWidget(QLabel("ATR Period:"), 1, 2)
        self.atr_period = QSpinBox()
        self.atr_period.setRange(7, 28)
        self.atr_period.setValue(14)
        param_layout.addWidget(self.atr_period, 1, 3)
        
        param_layout.addWidget(QLabel("ATR Multiplier:"), 1, 4)
        self.atr_mult = QDoubleSpinBox()
        self.atr_mult.setRange(1.0, 5.0)
        self.atr_mult.setValue(2.0)
        self.atr_mult.setSingleStep(0.1)
        param_layout.addWidget(self.atr_mult, 1, 5)
        
        # BE 파라미터
        param_layout.addWidget(QLabel("BE Trigger (x Risk):"), 2, 0)
        self.be_trigger = QDoubleSpinBox()
        self.be_trigger.setRange(1.0, 3.0)
        self.be_trigger.setValue(1.5)
        self.be_trigger.setSingleStep(0.1)
        param_layout.addWidget(self.be_trigger, 2, 1)
        
        param_layout.addWidget(QLabel("Pattern Tolerance (%):"), 2, 2)
        self.pattern_tol = QDoubleSpinBox()
        self.pattern_tol.setRange(1.0, 10.0)
        self.pattern_tol.setValue(3.0)
        self.pattern_tol.setSingleStep(0.5)
        param_layout.addWidget(self.pattern_tol, 2, 3)
        
        layout.addWidget(param_group)
        
        # 진행률 막대
        from PyQt5.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2a2e3b;
                border-radius: 5px;
                text-align: center;
                background: #131722;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #2962FF;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        run_btn = QPushButton("▶️ Run Backtest")
        run_btn.setStyleSheet("""
            QPushButton {
                background: #26a69a;
                color: white;
                padding: 12px 30px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background: #2bbd9a; }
        """)
        run_btn.clicked.connect(self._run_backtest)
        btn_layout.addWidget(run_btn)
        
        self.optimize_btn = QPushButton("🔍 Auto Optimize")
        self.optimize_btn.setStyleSheet("""
            QPushButton {
                background: #2962FF;
                color: white;
                padding: 12px 30px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background: #1e88e5; }
        """)
        self.optimize_btn.clicked.connect(self._run_auto_optimize)
        btn_layout.addWidget(self.optimize_btn)
        
        load_btn = QPushButton("📂 Load Best")
        load_btn.setToolTip("저장된 최적 파라미터 로드")
        load_btn.clicked.connect(self._load_best_params)
        btn_layout.addWidget(load_btn)
        
        save_btn = QPushButton("💾 Save Params")
        save_btn.clicked.connect(self._save_params)
        btn_layout.addWidget(save_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(7)
        self.result_table.setHorizontalHeaderLabels([
            "Rank", "Score", "Trades", "Win Rate", "Total PnL", "Max DD", "PF"
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setStyleSheet("""
            QTableWidget {
                background: #131722;
                color: white;
                border: 1px solid #2a2e3b;
            }
            QHeaderView::section {
                background: #1e2330;
                color: white;
                padding: 8px;
                border: 1px solid #2a2e3b;
            }
        """)
        self.result_table.cellClicked.connect(self._on_result_selected)
        layout.addWidget(self.result_table)
        
        # 최적화 결과 저장
        self._optimization_results = []
        
        return widget
    
    def _create_log_tab(self):
        """디버그 로그 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.debug_log = QTextEdit()
        self.debug_log.setReadOnly(True)
        self.debug_log.setStyleSheet("""
            QTextEdit {
                background: #0b0e14;
                color: #26a69a;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                border: 1px solid #2a2e3b;
            }
        """)
        self.debug_log.append("[System] Developer Mode initialized")
        self.debug_log.append("[Info] Use 'Auto Optimize' to find best parameters for each symbol")
        layout.addWidget(self.debug_log)
        
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(lambda: self.debug_log.clear())
        layout.addWidget(clear_btn)
        
        return widget
    
    def _create_system_tab(self):
        """시스템 정보 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setStyleSheet("""
            QTextEdit {
                background: #131722;
                color: white;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                border: 1px solid #2a2e3b;
            }
        """)
        
        import platform
        info_text.append(f"Python: {platform.python_version()}")
        info_text.append(f"OS: {platform.system()} {platform.release()}")
        info_text.append(f"Architecture: {platform.machine()}")
        
        try:
            import PyQt5.QtCore
            info_text.append(f"PyQt5: {PyQt5.QtCore.QT_VERSION_STR}")
        except ImportError:
            pass
        
        try:
            import pyqtgraph
            info_text.append(f"PyQtGraph: {pyqtgraph.__version__}")
        except ImportError:
            pass
        
        layout.addWidget(info_text)
        
        return widget
    
    def _run_backtest(self):
        """단일 백테스트 실행"""
        params = self._get_current_params()
        symbol = params['symbol']
        
        self.debug_log.append(f"\n[Backtest] Running for {symbol}...")
        self.debug_log.append(f"[Params] {params}")
        
        try:
            from strategies.parameter_optimizer import ParameterOptimizer
            from strategies.wm_pattern_strategy import WMStrategyParams
            
            optimizer = ParameterOptimizer()
            
            # 데이터 로드
            df = optimizer.load_data(symbol)
            if df.empty:
                self.debug_log.append(f"[Error] No data for {symbol}")
                QMessageBox.warning(self, t("common.error"), f"No data found for {symbol}. Please download data first.")
                return
            
            candles = optimizer._df_to_candles(df)
            self.debug_log.append(f"[Data] Loaded {len(candles)} candles")
            
            # 파라미터 생성
            wm_params = WMStrategyParams(
                macd_fast=params['macd_fast'],
                macd_slow=params['macd_slow'],
                macd_signal=params['macd_signal'],
                swing_length=params['swing_length'],
                atr_period=params['atr_period'],
                atr_multiplier=params['atr_multiplier'],
                be_trigger_mult=params['be_trigger_mult'],
                pattern_tolerance=params['pattern_tolerance']
            )
            
            # 백테스트 실행
            result = optimizer.run_backtest(candles, wm_params)
            score = optimizer.calculate_score(result)
            
            self.debug_log.append(f"\n[Result] =============================")
            self.debug_log.append(f"  Total Trades: {result.get('total_trades', 0)}")
            self.debug_log.append(f"  Win Rate: {result.get('win_rate', 0):.1f}%")
            self.debug_log.append(f"  Total PnL: {result.get('total_pnl', 0):.2f}%")
            self.debug_log.append(f"  Max Drawdown: {result.get('max_drawdown', 0):.2f}%")
            self.debug_log.append(f"  Profit Factor: {result.get('profit_factor', 0):.2f}")
            self.debug_log.append(f"  Score: {score:.2f}")
            self.debug_log.append(f"=====================================")
            
            # 테이블에 결과 추가
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("1"))
            self.result_table.setItem(0, 1, QTableWidgetItem(f"{score:.1f}"))
            self.result_table.setItem(0, 2, QTableWidgetItem(str(result.get('total_trades', 0))))
            self.result_table.setItem(0, 3, QTableWidgetItem(f"{result.get('win_rate', 0):.1f}%"))
            self.result_table.setItem(0, 4, QTableWidgetItem(f"{result.get('total_pnl', 0):.2f}%"))
            self.result_table.setItem(0, 5, QTableWidgetItem(f"{result.get('max_drawdown', 0):.2f}%"))
            self.result_table.setItem(0, 6, QTableWidgetItem(f"{result.get('profit_factor', 0):.2f}"))
            
        except Exception as e:
            import traceback
            self.debug_log.append(f"[Error] {e}")
            traceback.print_exc()
    
    def _run_auto_optimize(self):
        """자동 파라미터 최적화 실행"""
        symbol = self.symbol_combo.currentText()
        
        self.debug_log.append(f"\n[Auto Optimize] Starting for {symbol}...")
        self.debug_log.append("[Info] This may take a few minutes...")
        
        self.optimize_btn.setEnabled(False)
        self.optimize_btn.setText("⏳ Optimizing...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        try:
            from strategies.parameter_optimizer import ParameterOptimizer, ParameterRange
            
            optimizer = ParameterOptimizer()
            
            # 콜백 함수
            def update_progress(progress, message):
                self.progress_bar.setValue(progress)
                self.debug_log.append(f"[Progress] {message}")
                QApplication.processEvents()
            
            # 파라미터 범위 설정 (조합 수를 적절히 유지)
            param_range = ParameterRange(
                macd_fast=[10, 12, 14],
                macd_slow=[24, 26, 28],
                macd_signal=[8, 9, 10],
                swing_length=[2, 3, 4],
                atr_period=[12, 14, 16],
                atr_multiplier=[1.5, 2.0, 2.5],
                be_trigger_mult=[1.0, 1.5, 2.0],
                pattern_tolerance=[0.02, 0.03, 0.04]
            )
            
            # 그리드 서치 실행
            results = optimizer.grid_search(symbol, param_range, callback=update_progress)
            
            if not results:
                self.debug_log.append("[Error] No results. Check if data exists.")
                return
            
            self._optimization_results = results
            
            # 상위 10개 결과 표시
            top_results = results[:10]
            self.result_table.setRowCount(len(top_results))
            
            for i, r in enumerate(top_results):
                self.result_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                self.result_table.setItem(i, 1, QTableWidgetItem(f"{r.score:.1f}"))
                self.result_table.setItem(i, 2, QTableWidgetItem(str(r.total_trades)))
                self.result_table.setItem(i, 3, QTableWidgetItem(f"{r.win_rate:.1f}%"))
                self.result_table.setItem(i, 4, QTableWidgetItem(f"{r.total_pnl:.2f}%"))
                self.result_table.setItem(i, 5, QTableWidgetItem(f"{r.max_drawdown:.2f}%"))
                self.result_table.setItem(i, 6, QTableWidgetItem(f"{r.profit_factor:.2f}"))
            
            # 최적 결과 로그
            best = results[0]
            self.debug_log.append(f"\n🎯 [Best Result] =============================")
            self.debug_log.append(f"  Symbol: {symbol}")
            self.debug_log.append(f"  Score: {best.score:.2f}")
            self.debug_log.append(f"  Trades: {best.total_trades}")
            self.debug_log.append(f"  Win Rate: {best.win_rate:.1f}%")
            self.debug_log.append(f"  Total PnL: {best.total_pnl:.2f}%")
            self.debug_log.append(f"  Max DD: {best.max_drawdown:.2f}%")
            self.debug_log.append(f"  Profit Factor: {best.profit_factor:.2f}")
            self.debug_log.append(f"\n  Best Params: {getattr(best, 'params', {})}")
            self.debug_log.append(f"=============================================")
            
            # 결과 저장
            optimizer.save_result(symbol, best)
            self.debug_log.append(f"\n[Saved] Best params saved to optimization_results/{symbol}_optimized.json")
            
            # 최적 파라미터를 UI에 적용
            self._apply_params(best.params)
            
            QMessageBox.information(self, "Complete", 
                f"Optimization complete!\n\n"
                f"Best for {symbol}:\n"
                f"Win Rate: {best.win_rate:.1f}%\n"
                f"Total PnL: {best.total_pnl:.2f}%\n"
                f"Profit Factor: {best.profit_factor:.2f}")
            
        except Exception as e:
            import traceback
            self.debug_log.append(f"[Error] {e}")
            traceback.print_exc()
            QMessageBox.critical(self, t("common.error"), f"Optimization failed: {e}")
        
        finally:
            self.optimize_btn.setEnabled(True)
            self.optimize_btn.setText("🔍 Auto Optimize")
            self.progress_bar.setVisible(False)
    
    def _on_result_selected(self, row, col):
        """결과 행 선택 시 파라미터 적용"""
        if row < len(self._optimization_results):
            result = self._optimization_results[row]
            self._apply_params(result.params)
            self.debug_log.append(f"[Selected] Applied params from rank {row + 1}")
    
    def _apply_params(self, params):
        """파라미터를 UI에 적용"""
        if 'macd_fast' in params:
            self.macd_fast.setValue(params['macd_fast'])
        if 'macd_slow' in params:
            self.macd_slow.setValue(params['macd_slow'])
        if 'macd_signal' in params:
            self.macd_signal.setValue(params['macd_signal'])
        if 'swing_length' in params:
            self.swing_length.setValue(params['swing_length'])
        if 'atr_period' in params:
            self.atr_period.setValue(params['atr_period'])
        if 'atr_multiplier' in params:
            self.atr_mult.setValue(params['atr_multiplier'])
        if 'be_trigger_mult' in params:
            self.be_trigger.setValue(params['be_trigger_mult'])
        if 'pattern_tolerance' in params:
            self.pattern_tol.setValue(params['pattern_tolerance'] * 100)
    
    def _load_best_params(self):
        """저장된 최적 파라미터 로드"""
        symbol = self.symbol_combo.currentText()
        
        try:
            from strategies.parameter_optimizer import ParameterOptimizer
            
            optimizer = ParameterOptimizer()
            params = optimizer.load_optimized_params(symbol)
            
            if params:
                self._apply_params(params)
                self.debug_log.append(f"[Loaded] Best params for {symbol}")
                QMessageBox.information(self, "Loaded", f"Loaded optimized params for {symbol}")
            else:
                self.debug_log.append(f"[Info] No saved params for {symbol}")
                QMessageBox.information(self, "Not Found", f"No saved params for {symbol}. Run Auto Optimize first.")
        
        except Exception as e:
            self.debug_log.append(f"[Error] {e}")
    
    def _save_params(self):
        """현재 파라미터 저장"""
        params = self._get_current_params()
        symbol = params['symbol']
        
        try:
            import json
            filepath = f"optimization_results/{symbol}_manual.json"
            os.makedirs("optimization_results", exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'symbol': symbol,
                    'saved_at': datetime.now().isoformat(),
                    'params': params
                }, f, indent=2)
            
            self.debug_log.append(f"[Saved] Params saved to {filepath}")
            QMessageBox.information(self, "Saved", f"Parameters saved to {filepath}")
        
        except Exception as e:
            self.debug_log.append(f"[Error] {e}")
    
    def _get_current_params(self):
        """현재 파라미터 가져오기"""
        return {
            'symbol': self.symbol_combo.currentText(),
            'macd_fast': self.macd_fast.value(),
            'macd_slow': self.macd_slow.value(),
            'macd_signal': self.macd_signal.value(),
            'swing_length': self.swing_length.value(),
            'atr_period': self.atr_period.value(),
            'atr_multiplier': self.atr_mult.value(),
            'be_trigger_mult': self.be_trigger.value(),
            'pattern_tolerance': self.pattern_tol.value() / 100
        }


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from datetime import datetime
    app = QApplication(sys.argv)
    w = DeveloperModeWidget()
    w.resize(900, 700)
    w.show()
    sys.exit(app.exec_())
