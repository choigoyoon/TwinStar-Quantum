# backtest_widget.py
"""
Backtest Widget - Full Version
- AlphaX7Core strategy integration
- Parameter management with presets
- Trade visualization and statistics
"""

from locales.lang_manager import t
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QCheckBox,
    QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QDoubleSpinBox, QSpinBox,
    QComboBox, QFileDialog, QInputDialog, QScrollArea, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor


from datetime import datetime
import sys
import os
import json
from pathlib import Path
import pandas as pd

# Path setup for EXE compatibility
if not getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

# Imports with fallbacks
try:
    from utils.preset_manager import get_preset_manager, get_backtest_params, save_strategy_params
    from constants import DEFAULT_PARAMS, EXCHANGE_INFO, TF_MAPPING, TF_RESAMPLE_MAP
except ImportError:
    def get_preset_manager(): return None
    def get_backtest_params(name=None): return {}
    def save_strategy_params(params): pass
    DEFAULT_PARAMS = {}
    EXCHANGE_INFO = {
        "bybit": {"type": "CEX", "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]},
        "binance": {"type": "CEX", "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
    }
    TF_MAPPING = {'1h': '15min', '4h': '1h', '1d': '4h', '1w': '1d'}
    TF_RESAMPLE_MAP = {
        '15min': '15min', '15m': '15min', '30min': '30min', '30m': '30min',
        '1h': '1h', '1H': '1h', '4h': '4h', '4H': '4h', '1d': '1D', '1D': '1D'
    }

    # [REMOVED] Local DEFAULT_PARAMS removed in favor of constants.py



try:
    from paths import Paths
except ImportError:
    class Paths:
        CACHE = "data/cache"
        CONFIG = "config"
        BASE = os.getcwd()

# Shared resample import
try:
    from utils.data_utils import resample_data as shared_resample
except ImportError:
    shared_resample = None

from GUI.components.interactive_chart import InteractiveChart

import logging
logger = logging.getLogger(__name__)


class BacktestWorker(QThread):
    """Backtest execution thread"""
    
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    
    def __init__(self, strategy, slippage, fee, leverage, strategy_params=None, use_pyramiding=False, direction='Both'):
        super().__init__()
        self.strategy = strategy
        self.slippage = slippage
        self.fee = fee
        self.leverage = leverage
        self.strategy_params = strategy_params or {}
        self.use_pyramiding = use_pyramiding
        self.direction = direction
        
        self.trades_detail = []
        self.audit_logs = []
        self.df_15m = None
        self.result_stats = None
    
    def run(self):
        try:
            self.progress.emit(10)
            self.df_15m = self.strategy.df_15m
            self.progress.emit(30)
            
            # Merge parameters
            params = {
                'atr_mult': DEFAULT_PARAMS.get('atr_mult', 1.5),
                'trail_start_r': DEFAULT_PARAMS.get('trail_start_r', 0.8),
                'trail_dist_r': DEFAULT_PARAMS.get('trail_dist_r', 0.5),
                'pattern_tolerance': DEFAULT_PARAMS.get('pattern_tolerance', 0.03),
                'entry_validity_hours': DEFAULT_PARAMS.get('entry_validity_hours', 12.0),
                'pullback_rsi_long': DEFAULT_PARAMS.get('pullback_rsi_long', 40),
                'pullback_rsi_short': DEFAULT_PARAMS.get('pullback_rsi_short', 60),
                'max_adds': DEFAULT_PARAMS.get('max_adds', 1),
                'rsi_period': DEFAULT_PARAMS.get('rsi_period', 14),
                'atr_period': DEFAULT_PARAMS.get('atr_period', 14)
            }
            params.update(self.strategy_params)
            
            logger.info(f"[BT] tolerance={params.get('pattern_tolerance')}, validity={params.get('entry_validity_hours')}h")
            
            if self.df_15m is None or self.df_15m.empty:
                raise ValueError("No data available for backtest")

            df_entry = self.df_15m.copy()

            # Timestamp conversion
            if not pd.api.types.is_datetime64_any_dtype(df_entry['timestamp']):
                if pd.api.types.is_numeric_dtype(df_entry['timestamp']) and df_entry['timestamp'].iloc[0] > 1e12:
                    df_entry['timestamp'] = pd.to_datetime(df_entry['timestamp'], unit='ms')
                else:
                    df_entry['timestamp'] = pd.to_datetime(df_entry['timestamp'])

            # Create pattern data (resample to trend_tf)
            trend_tf = params.get('trend_interval', '1h')
            rule = TF_RESAMPLE_MAP.get(trend_tf, trend_tf)
            
            df_temp = df_entry.copy()
            if pd.api.types.is_numeric_dtype(df_temp['timestamp']):
                df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'], unit='ms')
            
            df_temp = df_temp.set_index('timestamp')
            df_pattern = df_temp.resample(rule).agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
            
            # Add indicators
            try:
                from indicator_generator import IndicatorGenerator
                df_pattern = IndicatorGenerator.add_all_indicators(df_pattern)
            except Exception as e:
                logger.info(f"Indicator calculation failed: {e}")
            
            self.progress.emit(50)
            
            # Run backtest
            combined_slippage = self.slippage + self.fee
            
            result, audit_logs = self.strategy.run_backtest(
                df_pattern=df_pattern,
                df_entry=df_entry,
                slippage=combined_slippage,
                atr_mult=params.get('atr_mult'),
                trail_start_r=params.get('trail_start_r'),
                trail_dist_r=params.get('trail_dist_r'),
                pattern_tolerance=params.get('pattern_tolerance'),
                entry_validity_hours=params.get('entry_validity_hours'),
                pullback_rsi_long=params.get('pullback_rsi_long'),
                pullback_rsi_short=params.get('pullback_rsi_short'),
                max_adds=params.get('max_adds'),
                rsi_period=params.get('rsi_period', 14),
                atr_period=params.get('atr_period', 14),
                filter_tf=params.get('filter_tf', '4h'),
                enable_pullback=self.use_pyramiding,
                allowed_direction=self.direction,
                macd_fast=params.get('macd_fast'),
                macd_slow=params.get('macd_slow'),
                macd_signal=params.get('macd_signal'),
                ema_period=params.get('ema_period'),
                collect_audit=True
            )
            self.audit_logs = audit_logs
            
            logger.info(f"[BT] Result: {len(result) if result else 0} trades")
            
            if result:
                self.trades_detail = result
                leverage = self.leverage
                pnls = [t.get('pnl', 0) * leverage for t in result]
                
                # Simple return
                simple_return = sum(pnls)
                
                # Compound return
                import math
                log_sum = 0
                for p in pnls:
                    if p > -100:
                        log_sum += math.log(1 + p / 100)
                compound_return = min((math.exp(log_sum) - 1) * 100, 999999)
                
                # MDD calculation
                cumulative = []
                equity = 1.0
                for p in pnls:
                    equity *= (1 + p / 100)
                    cumulative.append(equity)
                
                peak = 1.0
                mdd = 0
                for c in cumulative:
                    if c > peak:
                        peak = c
                    drawdown = (peak - c) / peak * 100
                    if drawdown > mdd:
                        mdd = drawdown
                
                # [FIX] raw_pnl 기준 승률 (수수료 무관, 순수 가격 움직임)
                win_count = len([t for t in result if t.get('raw_pnl', t.get('pnl', 0)) > 0])

                
                self.result_stats = {
                    'count': len(result),
                    'simple_return': simple_return,
                    'compound_return': compound_return,
                    'total_return': compound_return,
                    'win_rate': (win_count / len(result)) * 100 if result else 0,
                    'mdd': mdd,
                    'leverage': leverage,
                }
            
            self.progress.emit(100)
            self.finished.emit()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))




class SingleBacktestWidget(QWidget):
    """싱글 심볼 백테스트 위젯 (기존 기능)"""
    
    backtest_finished = pyqtSignal(list, object, object)
    
    def __init__(self):
        super().__init__()
        self.strategy = None
        self._worker = None
        self._current_params = {}
        self._fixed_labels = {}
        self._init_data()
        self._init_ui()
    
    def closeEvent(self, event):
        if hasattr(self, '_worker') and self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(3000)
        super().closeEvent(event)
    
    def _init_data(self):
        try:
            from paths import Paths
            project_root = Paths.BASE
            if os.getcwd() != project_root:
                os.chdir(project_root)
            
            try:
                from GUI.data_manager import DataManager
            except ImportError:
                from data_manager import DataManager
            
            dm = DataManager()
            df = None
            
            try:
                cache_files = list(dm.cache_dir.glob("*.parquet"))
                if cache_files:
                    latest_db = max(cache_files, key=lambda p: p.stat().st_mtime)
                    parts = latest_db.stem.split('_')
                    
                    if len(parts) >= 3:
                        exchange = parts[0]
                        symbol = parts[1]
                        timeframe = parts[2]
                        
                        logger.info(f"Loading cached data from {latest_db}...")
                        df = dm.load_data(symbol, exchange, timeframe)
            except Exception as e:
                logger.info(f"Cache load failed: {e}")

            from core.strategy_core import AlphaX7Core
            
            if df is not None and not df.empty:
                self.strategy = AlphaX7Core()
                self.strategy.df_15m = df
                logger.info(f"Alpha-X7 Core Loaded with {len(df)} candles")
            else:
                self.strategy = AlphaX7Core()
                self.strategy.df_15m = None
                logger.info("Alpha-X7 Core Loaded (No Data)")
                
        except Exception as e:
            logger.info(f"Strategy load error: {e}")
            self.strategy = None
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Row 1: Data source + Preset
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        row1.addWidget(QLabel(t("backtest.exchange") + ":"))
        self.exchange_combo = QComboBox()
        cex_list = [k for k, v in EXCHANGE_INFO.items() if v.get('type') == 'CEX']
        self.exchange_combo.addItems(cex_list if cex_list else ['bybit', 'binance'])
        self.exchange_combo.setMinimumWidth(80)
        self.exchange_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        self.exchange_combo.currentTextChanged.connect(self._on_exchange_changed)
        row1.addWidget(self.exchange_combo)
        
        row1.addWidget(QLabel(t("backtest.symbol") + ":"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setMinimumWidth(100)
        self.symbol_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        row1.addWidget(self.symbol_combo)
        
        row1.addWidget(QLabel(t("backtest.timeframe") + ":"))
        self.trend_tf_combo = QComboBox()
        self.trend_tf_combo.addItems(['1h', '4h', '1d'])
        self.trend_tf_combo.setMinimumWidth(60)
        self.trend_tf_combo.setToolTip("추세 판단/데이터 필터 타임프레임\n선택한 TF의 추세가 정렬될 때만 진입합니다.")
        self.trend_tf_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        row1.addWidget(self.trend_tf_combo)
        
        self.load_btn = QPushButton(t("backtest.load"))
        self.load_btn.clicked.connect(self._load_selected_data)
        self.load_btn.setStyleSheet("background: #2962ff; color: white; padding: 8px 12px; border-radius: 4px;")
        row1.addWidget(self.load_btn)
        
        self.data_status = QLabel(t("backtest.no_data"))
        self.data_status.setStyleSheet("color: #888; font-size: 11px;")
        row1.addWidget(self.data_status)
        
        row1.addSpacing(20)
        
        row1.addWidget(QLabel(t("backtest.preset") + ":"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self.preset_combo.setStyleSheet("QComboBox { background: #2b2b2b; color: white; padding: 5px; }")
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        row1.addWidget(self.preset_combo)
        
        refresh_btn = QPushButton("🔄 " + t("backtest.refresh"))
        refresh_btn.setToolTip(t("backtest.refresh"))
        refresh_btn.setMinimumWidth(80)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #2a2e3b; 
                color: white; 
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background: #3a3e4b; }
        """)
        refresh_btn.clicked.connect(self._refresh_presets)
        row1.addWidget(refresh_btn)
        
        save_btn = QPushButton("💾 " + t("common.save"))
        save_btn.setToolTip(t("common.save"))
        save_btn.setMinimumWidth(70)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #512da8; 
                color: white; 
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background: #6a3fc4; }
        """)
        save_btn.clicked.connect(self._save_preset)
        row1.addWidget(save_btn)
        
        delete_btn = QPushButton("🗑 " + t("common.delete"))
        delete_btn.setToolTip(t("common.delete"))
        delete_btn.setMinimumWidth(60)
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #c62828; 
                color: white; 
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background: #e53935; }
        """)
        delete_btn.clicked.connect(self._delete_preset)
        row1.addWidget(delete_btn)
        
        self.preset_label = QLabel("")
        self.preset_label.setStyleSheet("color: #888; font-size: 11px;")
        row1.addWidget(self.preset_label)
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # Row 2: Parameters
        param_frame = QFrame()
        param_frame.setStyleSheet("background: #1e222d; border-radius: 6px; padding: 8px;")
        param_grid = QGridLayout(param_frame)
        param_grid.setSpacing(10)
        param_grid.setContentsMargins(10, 8, 10, 8)
        
        lbl_style = "color: #888; font-size: 12px;"
        spin_style = "background: #2b2b2b; color: white; min-width: 70px; padding: 4px;"
        
        # Row 0: Leverage, Slippage, Fee
        col = 0
        param_grid.addWidget(self._make_label(t("backtest.leverage_label") + ":", lbl_style), 0, col)
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 100)
        self.leverage_spin.setValue(3)
        self.leverage_spin.setStyleSheet(spin_style)
        param_grid.addWidget(self.leverage_spin, 0, col + 1)
        
        col += 2
        param_grid.addWidget(self._make_label(t("backtest.slippage_label") + ":", lbl_style), 0, col)
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setRange(0, 5)
        self.slippage_spin.setValue(0.05)
        self.slippage_spin.setSingleStep(0.01)
        self.slippage_spin.setStyleSheet(spin_style)
        param_grid.addWidget(self.slippage_spin, 0, col + 1)
        
        col += 2
        param_grid.addWidget(self._make_label(t("backtest.fee_label") + ":", lbl_style), 0, col)
        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setRange(0, 1)
        self.fee_spin.setValue(0.055)
        self.fee_spin.setSingleStep(0.005)
        self.fee_spin.setStyleSheet(spin_style)
        param_grid.addWidget(self.fee_spin, 0, col + 1)
        
        col += 2
        param_grid.addWidget(self._make_label(t("backtest.direction_label") + ":", lbl_style), 0, col)
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Both", "Long", "Short"])
        self.direction_combo.setStyleSheet("background: #2b2b2b; color: white; min-width: 80px; padding: 4px;")
        param_grid.addWidget(self.direction_combo, 0, col + 1)
        
        # Row 1: Fixed parameter display
        param_items = [
            ("trail_start", "시작", f"{DEFAULT_PARAMS.get('trail_start_r', 0.8)}R"),
            ("trail_dist", "거리", f"{DEFAULT_PARAMS.get('trail_dist_r', 0.5)}R"),
            ("rsi_period", "RSI", str(DEFAULT_PARAMS.get('rsi_period', 14))),
            ("atr_mult", "ATR", str(DEFAULT_PARAMS.get('atr_mult', 1.5))),
            ("validity", "유효", f"{DEFAULT_PARAMS.get('entry_validity_hours', 12.0)}H"),
            ("tolerance", "허용", f"{DEFAULT_PARAMS.get('pattern_tolerance', 0.03)*100:.0f}%"),
        ]
        
        for i, (key, label, value) in enumerate(param_items):
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet("color: #888; font-size: 11px;")
            val = QLabel(value)
            val.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 11px;")
            self._fixed_labels[key] = val
            param_grid.addWidget(lbl, 1, i * 2)
            param_grid.addWidget(val, 1, i * 2 + 1)
        
        layout.addWidget(param_frame)
        
        # Row 3: Run button + Options
        row3 = QHBoxLayout()
        row3.setSpacing(10)
        
        self._run_btn = QPushButton(t("backtest.run"))
        self._run_btn.clicked.connect(self._run_backtest)
        self._run_btn.setMinimumWidth(200)
        self._run_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        row3.addWidget(self._run_btn)
        
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMinimumWidth(200)
        self._progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #363a45;
                border-radius: 4px;
                text-align: center;
                background: #1e222d;
                color: white;
            }
            QProgressBar::chunk { background-color: #4CAF50; }
        """)
        row3.addWidget(self._progress)
        
        row3.addStretch()
        
        # [REMOVED] 4H Filter, Pyramiding checkboxes
        
        layout.addLayout(row3)
        
        
        # Row 4: Stats summary
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background: #1e222d; border-radius: 6px;")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(15, 10, 15, 10)
        stats_layout.setSpacing(30)
        
        self._stat_trades = self._create_stat_label(t("backtest.stat_trades"), "0")
        self._stat_winrate = self._create_stat_label(t("backtest.stat_winrate"), "0%")
        self._stat_simple = self._create_stat_label(t("backtest.stat_simple"), "0%")
        self._stat_compound = self._create_stat_label(t("backtest.stat_compound"), "0%")
        self._stat_mdd = self._create_stat_label(t("backtest.stat_mdd"), "0%")
        
        stats_layout.addWidget(self._stat_trades)
        stats_layout.addWidget(self._stat_winrate)
        stats_layout.addWidget(self._stat_simple)
        stats_layout.addWidget(self._stat_compound)
        stats_layout.addWidget(self._stat_mdd)
        stats_layout.addStretch()
        
        # 결과 저장 버튼
        self.save_result_btn = QPushButton("💾 " + t("backtest.save_result"))
        self.save_result_btn.setStyleSheet("""
            QPushButton { background: #4CAF50; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388E3C; }
            QPushButton:disabled { background: #555; }
        """)
        self.save_result_btn.setToolTip(t("backtest.save_result"))
        self.save_result_btn.clicked.connect(self._save_result)
        self.save_result_btn.setEnabled(False)
        stats_layout.addWidget(self.save_result_btn)
        
        layout.addWidget(stats_frame)
        
        # Row 5: Result Area (Table + Chart)
        layout.addWidget(self._init_result_area(), stretch=1)
        
        # Initialize
        self._refresh_presets()
        if self.exchange_combo.count() > 0:
            self._on_exchange_changed(self.exchange_combo.currentText())
        self._load_json_params()
    
    def _make_label(self, text, style):
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl
    
    def _create_stat_label(self, title, value):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title_lbl = QLabel(f"{title}:")
        title_lbl.setStyleSheet("color: #787b86; font-size: 13px;")
        layout.addWidget(title_lbl)
        
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        layout.addWidget(value_lbl)
        
        frame.value_label = value_lbl
        return frame
    
    def _on_exchange_changed(self, exchange_name: str):
        self.symbol_combo.clear()
        exchange_info = EXCHANGE_INFO.get(exchange_name.lower(), {})
        symbols = exchange_info.get('symbols', ['BTCUSDT', 'ETHUSDT'])
        self.symbol_combo.addItems(symbols)
        if self.symbol_combo.count() > 0:
            self.symbol_combo.setCurrentIndex(0)
    
    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_presets()
        if self.symbol_combo.count() == 0:
            self._on_exchange_changed(self.exchange_combo.currentText())
    
    def _refresh_presets(self):
        current = self.preset_combo.currentText()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("Default")
        
        try:
            pm = get_preset_manager()
            if pm:
                pm.clear_cache()
                presets = pm.list_presets()
                if presets:
                    self.preset_combo.insertSeparator(1)
                    self.preset_combo.addItems(presets)
        except Exception as e:
            logger.info(f"Preset refresh error: {e}")
        
        idx = self.preset_combo.findText(current)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        else:
            self.preset_combo.setCurrentIndex(0)
        
        self.preset_combo.blockSignals(False)
    
    def _on_preset_changed(self, text):
        if text == "Default" or not text:
            return
        
        pm = get_preset_manager()
        if not pm:
            return
        
        try:
            params = pm.load_preset_flat(text)
            self._current_params = params
            
            if 'leverage' in params:
                self.leverage_spin.setValue(int(params['leverage']))
            
            # [NEW] 거래소 및 심볼 자동 선택
            # 프리셋에는 'exchange' 또는 'symbol' 정보가 포함되어 있을 수 있음
            preset_exchange = params.get('exchange')
            preset_symbol = params.get('symbol')
            
            if preset_exchange:
                idx = self.exchange_combo.findText(preset_exchange.lower())
                if idx >= 0:
                    self.exchange_combo.blockSignals(True)
                    self.exchange_combo.setCurrentIndex(idx)
                    self._on_exchange_changed(preset_exchange.lower()) # 심볼 리스트 갱신 강제
                    self.exchange_combo.blockSignals(False)

            if preset_symbol:
                idx = self.symbol_combo.findText(preset_symbol.upper())
                if idx < 0:
                    # 혹시 리스트에 없으면 추가
                    self.symbol_combo.addItem(preset_symbol.upper())
                    idx = self.symbol_combo.findText(preset_symbol.upper())
                
                if idx >= 0:
                    self.symbol_combo.setCurrentIndex(idx)

            # [FIX] trend_interval (기준 TF)을 우선으로 UI 업데이트
            tf_key = 'trend_interval' if 'trend_interval' in params else ('filter_tf' if 'filter_tf' in params else None)
            if tf_key:
                idx = self.trend_tf_combo.findText(params.get(tf_key, ""))
                if idx >= 0:
                    self.trend_tf_combo.blockSignals(True)
                    self.trend_tf_combo.setCurrentIndex(idx)
                    self.trend_tf_combo.blockSignals(False)
            
            self._update_fixed_labels(params)
            
            # Update preset label
            if hasattr(self, 'preset_label'):
                info = []
                if preset_exchange: info.append(preset_exchange.upper())
                if preset_symbol: info.append(preset_symbol.upper())
                if 'filter_tf' in params:
                    info.append(f"F:{params.get('filter_tf')}")
                if 'atr_mult' in params:
                    info.append(f"A:{params.get('atr_mult')}")
                self.preset_label.setText(" | ".join(info) if info else "Loaded")
                self.preset_label.setStyleSheet("color: #00e676; font-size: 11px;")
            
        except Exception as e:
            logger.info(f"Preset load error: {e}")
    
    def _update_fixed_labels(self, params):
        if 'atr_mult' in params:
            self._fixed_labels['atr_mult'].setText(str(params['atr_mult']))
        if 'trail_start_r' in params:
            self._fixed_labels['trail_start'].setText(f"{params['trail_start_r']}R")
        if 'trail_dist_r' in params:
            self._fixed_labels['trail_dist'].setText(f"{params['trail_dist_r']}R")
        if 'rsi_period' in params:
            self._fixed_labels['rsi_period'].setText(str(params['rsi_period']))
        if 'pattern_tolerance' in params:
            tol = params['pattern_tolerance']
            self._fixed_labels['tolerance'].setText(f"{tol*100:.0f}%" if tol < 1 else f"{tol}%")
        if 'entry_validity_hours' in params:
            self._fixed_labels['validity'].setText(f"{params['entry_validity_hours']}H")
    
    def _load_json_params(self):
        try:
            params = get_backtest_params()
            if params:
                self._current_params = params
                self._update_fixed_labels(params)
                
                # [FIX] filter_tf 또는 trend_interval로 UI 업데이트
                tf_key = 'filter_tf' if 'filter_tf' in params else ('trend_interval' if 'trend_interval' in params else None)
                if tf_key:
                    idx = self.trend_tf_combo.findText(params[tf_key])
                    if idx >= 0:
                        self.trend_tf_combo.blockSignals(True)
                        self.trend_tf_combo.setCurrentIndex(idx)
                        self.trend_tf_combo.blockSignals(False)
        except Exception as e:
            logger.info(f"JSON params load error: {e}")
    
    def _reset_to_defaults(self):
        self.leverage_spin.setValue(3)
        self.slippage_spin.setValue(0.05)
        self.fee_spin.setValue(0.055)
        self.trend_tf_combo.setCurrentText("1h")
        self.preset_combo.setCurrentIndex(0)
        self._current_params = {}
    
    def _load_selected_data(self):
        exchange = self.exchange_combo.currentText()
        symbol = self.symbol_combo.currentText()
        
        if not symbol:
            QMessageBox.warning(self, t("common.error"), "Select a symbol")
            return
        
        try:
            from data_manager import DataManager
            from core.strategy_core import AlphaX7Core
            
            dm = DataManager()
            df = dm.load_data(symbol, exchange, '15m')
            
            if df is not None and not df.empty:
                try:
                    from indicator_generator import IndicatorGenerator
                    df = IndicatorGenerator.add_all_indicators(df)
                except ImportError:
                    pass
                
                if 'rsi' not in df.columns and 'rsi_14' in df.columns:
                    df['rsi'] = df['rsi_14']
                if 'atr' not in df.columns and 'atr_14' in df.columns:
                    df['atr'] = df['atr_14']
                
                self.strategy = AlphaX7Core()
                self.strategy.df_15m = df
                
                self.data_status.setText(f"{exchange}/{symbol} ({len(df):,} candles)")
                self.data_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            else:
                self.data_status.setText("No data - download first")
                self.data_status.setStyleSheet("color: #ef5350; font-size: 11px;")
                
        except Exception as e:
            self.data_status.setText("Load failed")
            self.data_status.setStyleSheet("color: #ef5350; font-size: 11px;")
            logger.info(f"Data load error: {e}")
    
    def _init_result_area(self):
        """결과 영역: 탭 구성 (Trades vs Logic Audit)"""
        from PyQt5.QtWidgets import QTabWidget
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.result_tabs = QTabWidget()
        self.result_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #363a45; background: #131722; }
            QTabBar::tab { background: #1e222d; color: #787b86; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #2962ff; color: white; font-weight: bold; }
        """)

        # 1. Trades Tab
        self.trades_tab = QWidget()
        trades_layout = QVBoxLayout(self.trades_tab)
        trades_layout.setContentsMargins(0, 0, 0, 0)
        
        self.result_splitter = QSplitter(Qt.Horizontal)
        
        # 좌측: 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            '#', t("trade.entry"), t("trade.exit"), t("trade.type"), 
            t("trade.pnl_pct_header"), t("dashboard.balance"), t("backtest.mdd"), t("backtest.header_duration") if t("backtest.header_duration") != "backtest.header_duration" else "Duration"
        ])
        self.result_table.setStyleSheet(self._get_table_style())
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.itemSelectionChanged.connect(self._on_trade_selected)
        self.result_splitter.addWidget(self.result_table)

        # 우측: 차트
        self.chart_box = QGroupBox(t("backtest.chart_title"))
        self.chart_box.setStyleSheet("QGroupBox { color: white; font-weight: bold; border: 1px solid #363a45; margin-top: 5px; }")
        chart_vbox = QVBoxLayout(self.chart_box)
        
        # [MOD] Use InteractiveChart component
        self.chart_widget = InteractiveChart()
        chart_vbox.addWidget(self.chart_widget)
        
        self.result_splitter.addWidget(self.chart_box)
        
        self.result_splitter.setStretchFactor(0, 4)
        self.result_splitter.setStretchFactor(1, 6)
        trades_layout.addWidget(self.result_splitter)
        
        self.result_tabs.addTab(self.trades_tab, "📈 Trades")

        # 2. Logic Audit Tab
        self.audit_tab = QWidget()
        audit_layout = QVBoxLayout(self.audit_tab)
        
        self.logic_table = QTableWidget()
        self.logic_table.setColumnCount(5)
        self.logic_table.setHorizontalHeaderLabels(['Timestamp', 'Signal/Logic', 'Action', 'PnL/Status', 'Details'])
        self.logic_table.setStyleSheet(self._get_table_style())
        self.logic_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.logic_table.horizontalHeader().setStretchLastSection(True)
        
        audit_layout.addWidget(self.logic_table)
        self.result_tabs.addTab(self.audit_tab, "🔍 Logic Audit")
        
        return self.result_tabs

    def _get_table_style(self):
        return """
            QTableWidget { background: #1e222d; color: white; border: none; gridline-color: #363a45; }
            QHeaderView::section { background: #131722; color: #787b86; padding: 6px; border: 1px solid #363a45; }
            QTableWidget::item { padding: 4px; }
        """

    def _on_trade_selected(self):
        """테이블 행 클릭 시 (현재는 기능 없음, 추후 줌 연동 가능)"""
        pass

    # _update_chart removed (moved to InteractiveChart)

    def _populate_result_table(self, trades):
        self.result_table.setRowCount(0)
        self.result_table.setRowCount(len(trades))
        
        balance = 10000 
        equity = 1.0
        peak = 1.0
        
        for row, trade in enumerate(trades):
            self.result_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            # Entry
            entry_time = trade.get('entry_time', '')
            try:
                entry_str = pd.Timestamp(entry_time).strftime('%Y-%m-%d %H:%M')
            except (ValueError, TypeError):
                entry_str = str(entry_time)[:16] if entry_time else '-'
            self.result_table.setItem(row, 1, QTableWidgetItem(entry_str))
            
            # Exit
            exit_time = trade.get('exit_time', '')
            try:
                exit_str = pd.Timestamp(exit_time).strftime('%Y-%m-%d %H:%M')
            except (ValueError, TypeError):
                exit_str = str(exit_time)[:16] if exit_time else '-'
            self.result_table.setItem(row, 2, QTableWidgetItem(exit_str))

            # Direction
            direction = trade.get('type', '-')
            dir_item = QTableWidgetItem(direction)
            if 'Long' in direction:
                dir_item.setForeground(QColor('#26a69a'))
            elif 'Short' in direction:
                dir_item.setForeground(QColor('#ef5350'))
            self.result_table.setItem(row, 3, dir_item)
            
            # PnL%
            pnl = trade.get('pnl', 0)
            pnl_item = QTableWidgetItem(f"{pnl:+.2f}%")
            pnl_item.setForeground(QColor('#26a69a') if pnl >= 0 else QColor('#ef5350'))
            self.result_table.setItem(row, 4, pnl_item)
            
            # Balance & MDD 
            equity *= (1 + pnl/100)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            
            curr_balance = balance * equity
            self.result_table.setItem(row, 5, QTableWidgetItem(f"{curr_balance:.0f}"))
            self.result_table.setItem(row, 6, QTableWidgetItem(f"{dd:.2f}%"))
            
            # Duration
            duration = "-"
            try:
                et = entry_time
                xt = exit_time if exit_time else et
                if xt != '':
                    diff = xt - et
                    # [FIX] numpy.timedelta64 → pd.Timedelta 변환
                    hours = pd.Timedelta(diff).total_seconds() / 3600
                    duration = f"{hours:.1f}h"
            except (TypeError, ValueError, AttributeError):
                pass  # 시간 계산 실패 시 무시
            self.result_table.setItem(row, 7, QTableWidgetItem(duration))

    def _run_backtest(self):
        if not self.strategy:
            QMessageBox.warning(self, t("common.error"), "Strategy not loaded")
            return
        
        if self.strategy.df_15m is None or self.strategy.df_15m.empty:
            QMessageBox.warning(self, "No Data", "No data for backtest. Download data first.")
            return
        
        # Reset previous results
        self.result_table.setRowCount(0)
        self.chart_widget.clear()
        self.trades_detail = []
        for stat in [self._stat_trades, self._stat_winrate, self._stat_simple, self._stat_compound, self._stat_mdd]:
            stat.value_label.setText("...")
        
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._run_btn.setEnabled(False)
        self._run_btn.setText("Running...")
        
        slippage = self.slippage_spin.value() / 100.0
        fee = self.fee_spin.value() / 100.0
        total_cost = slippage + fee  # [FIX] Optimizer와 동일하게 합산
        leverage = self.leverage_spin.value()
        
        strategy_params = get_backtest_params(self.preset_combo.currentText())
        strategy_params.update(self._current_params)
        
        # [FIX] UI 선택값으로 필터/Resample TF 동기화
        tf = self.trend_tf_combo.currentText()
        strategy_params['trend_interval'] = tf
        # [MOD] filter_tf가 파라미터에 이미 있으면(최적화 적용 건) 유지, 없으면 현재 TF와 동기화
        if 'filter_tf' not in strategy_params:
            strategy_params['filter_tf'] = tf
        
        logger.info(f"[BT] Preset: {self.preset_combo.currentText()}")
        logger.info(f"[BT] Params: filter_tf={strategy_params.get('filter_tf')}, atr_mult={strategy_params.get('atr_mult')}")
        logger.info(f"[BT] Cost: slippage={slippage:.4f} + fee={fee:.4f} = total_cost={total_cost:.4f}")
        
        self.worker = BacktestWorker(
            strategy=self.strategy,
            slippage=total_cost,  # [FIX] 합산된 비용 전달 (Optimizer와 동일)
            fee=0,                # [FIX] fee는 이미 합산됨
            leverage=leverage,
            strategy_params=strategy_params,
            use_pyramiding=False,  # [FIX] Pyramiding UI 제거에 따른 하드코딩
            direction=self.direction_combo.currentText()  # [NEW] 방향성 전달
        )
        self.worker.finished.connect(self._on_finished)
        self.worker.progress.connect(self._progress.setValue)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_finished(self):
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._run_btn.setText("백테스트 실행")
        
        if self.worker and self.worker.trades_detail:
            trades = self.worker.trades_detail
            df_15m = self.worker.df_15m
            
            if self.worker.result_stats:
                r = self.worker.result_stats
                self._stat_trades.value_label.setText(str(r.get('count', len(trades))))
                self._stat_winrate.value_label.setText(f"{r.get('win_rate', 0):.1f}%")
                self._stat_simple.value_label.setText(f"{r.get('simple_return', 0):+.1f}%")
                self._stat_compound.value_label.setText(f"{r.get('compound_return', 0):+.1f}%")
                self._stat_mdd.value_label.setText(f"-{r.get('mdd', 0):.1f}%")
            
            # 결과 저장용 데이터 보관
            self.last_result = {
                'stats': r,
                'trades': trades,
                'params': self._current_params.copy()
            }
            self.save_result_btn.setEnabled(True)
            
            self.trades_detail = trades
            self.candle_data = df_15m
            self._populate_result_table(trades)
            self._populate_audit_table(self.worker.audit_logs)
            
            # [MOD] Update InteractiveChart
            self.chart_widget.set_data(df_15m)
            self.chart_widget.add_trades(trades)
            
            self.backtest_finished.emit(trades, df_15m, None)
        else:
            QMessageBox.warning(self, "No Result", "No trades or error occurred.")
    
    def _save_result(self):
        """백테스트 결과 저장"""
        from PyQt5.QtWidgets import QFileDialog
        import json
        from datetime import datetime
        
        if not hasattr(self, 'last_result') or not self.last_result:
            QMessageBox.warning(self, "저장 실패", "저장할 결과가 없습니다.")
            return
        
        # 파일 선택 다이얼로그
        default_name = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "📁 결과 저장",
            default_name,
            "JSON (*.json);;CSV (*.csv)"
        )
        
        if not path:
            return
        
        try:
            if path.endswith('.csv'):
                # CSV 저장
                import csv
                trades = self.last_result.get('trades', [])
                if trades:
                    with open(path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                        writer.writeheader()
                        writer.writerows(trades)
            else:
                # JSON 저장
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.last_result, f, ensure_ascii=False, indent=2, default=str)
            
            QMessageBox.information(self, "저장 완료", f"✅ 결과가 저장되었습니다.\n{path}")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"❌ 저장 중 오류 발생: {e}")
    
    def _populate_audit_table(self, logs):
        """로직 감사 테이블 채우기"""
        if not logs:
            self.logic_table.setRowCount(0)
            return

        self.logic_table.setRowCount(0)
        self.logic_table.setRowCount(len(logs))
        
        for row, log in enumerate(logs):
            ts = log.get('timestamp', '-')
            if isinstance(ts, pd.Timestamp):
                ts_str = ts.strftime('%m-%d %H:%M:%S')
            else:
                ts_str = str(ts)
                
            self.logic_table.setItem(row, 0, QTableWidgetItem(ts_str))
            
            logic_item = QTableWidgetItem(log.get('logic', '-'))
            # 색상 코딩
            if "SIGNAL DETECTED" in logic_item.text():
                logic_item.setForeground(QColor('#4CAF50')) # Green
            elif "SL UPDATE" in logic_item.text():
                logic_item.setForeground(QColor('#2196F3')) # Blue
            elif "STOP LOSS HIT" in logic_item.text() or "CLOSE" in logic_item.text():
                logic_item.setForeground(QColor('#f44336')) # Red
                
            self.logic_table.setItem(row, 1, logic_item)
            self.logic_table.setItem(row, 2, QTableWidgetItem(log.get('action', '-')))
            self.logic_table.setItem(row, 3, QTableWidgetItem(log.get('pnl', '-')))
            self.logic_table.setItem(row, 4, QTableWidgetItem(log.get('details', '-')))
            
        self.logic_table.scrollToBottom()

    def _on_error(self, message):
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._run_btn.setText("백테스트 실행")
        QMessageBox.critical(self, t("common.error"), message)
    
    def load_strategy_params(self):
        """Load parameters (called from main window)"""
        self._load_json_params()
    
    def apply_params(self, params: dict):
        """Apply optimization results"""
        try:
            self._current_params.update(params)
            
            if 'leverage' in params:
                self.leverage_spin.setValue(int(params['leverage']))
            
            self._update_fixed_labels(params)
            QMessageBox.information(self, "Applied", "Optimization parameters applied. Run backtest to verify.")
        except Exception as e:
            QMessageBox.warning(self, t("common.error"), f"Apply failed: {e}")
    
    def _refresh_data_sources(self):
        if hasattr(self, 'exchange_combo'):
            self._on_exchange_changed(self.exchange_combo.currentText())

    def _save_preset(self):
        """Save current settings as preset"""
        text, ok = QInputDialog.getText(self, "Save Preset", "Preset name (e.g. BTC_4h_Conservative):")
        if ok and text:
            pm = get_preset_manager()
            if pm:
                params = {
                    'exchange': self.exchange_combo.currentText(),
                    'symbol': self.symbol_combo.currentText(),
                    'leverage': self.leverage_spin.value(),
                    'slippage_pct': self.slippage_spin.value(),
                    'fee_pct': self.fee_spin.value(),
                    'trend_interval': self.trend_tf_combo.currentText(),
                }
                params.update(self._current_params)
                
                if pm.save_preset(text, params):
                    QMessageBox.information(self, t("common.success"), f"Preset '{text}' saved.")
                    self._refresh_presets()
                    idx = self.preset_combo.findText(text)
                    if idx >= 0:
                        self.preset_combo.setCurrentIndex(idx)
                else:
                    QMessageBox.warning(self, t("data.failed"), "Preset save failed")

    def _delete_preset(self):
        """Delete selected preset"""
        current = self.preset_combo.currentText()
        if current == "Default" or not current:
            QMessageBox.warning(self, t("common.error"), "Cannot delete default preset.")
            return
        
        reply = QMessageBox.question(self, "Confirm", f"Delete preset '{current}'?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            pm = get_preset_manager()
            if pm and pm.delete_preset(current):
                self._refresh_presets()
                self.preset_combo.setCurrentIndex(0)
                QMessageBox.information(self, "Deleted", "Preset deleted.")

    def _browse_csv_file(self):
        """CSV file selection dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV Data File",
            os.path.dirname(os.path.abspath(__file__)),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self._load_csv_file(file_path)
    
    def _load_csv_file(self, file_path):
        """Load CSV file"""
        try:
            from core.strategy_core import AlphaX7Core
            
            df = pd.read_csv(file_path)
            
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                first_ts = df['timestamp'].iloc[0] if len(df) > 0 else 0
                try:
                    ts_val = float(first_ts)
                except (ValueError, TypeError):
                    ts_val = 0
                if ts_val > 1000000000000:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                else:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            self.strategy = AlphaX7Core()
            self.strategy.df_15m = df
            
            filename = os.path.basename(file_path)
            self.data_status.setText(f"CSV: {filename} ({len(df):,} candles)")
            self.data_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            
            QMessageBox.information(self, "Loaded", f"CSV loaded!\n{len(df):,} candles")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Failed", f"CSV load failed: {e}")

    def _resample_data(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
        """Data resampling (15m -> target TF)"""
        if shared_resample:
            return shared_resample(df, target_tf, add_indicators=True)
        
        if df is None or df.empty:
            return df
        
        rule = TF_RESAMPLE_MAP.get(target_tf, target_tf)
        if rule == '15min':
            return df
        
        df = df.copy()
        if 'datetime' not in df.columns:
            if pd.api.types.is_numeric_dtype(df['timestamp']):
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            else:
                df['datetime'] = pd.to_datetime(df['timestamp'])
        
        df = df.set_index('datetime')
        agg_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        if 'timestamp' in df.columns:
            agg_dict['timestamp'] = 'first'
        
        resampled = df.resample(rule).agg(agg_dict).dropna().reset_index()
        
        try:
            from indicator_generator import IndicatorGenerator
            resampled = IndicatorGenerator.add_all_indicators(resampled)
            if 'rsi' not in resampled.columns and 'rsi_14' in resampled.columns:
                resampled['rsi'] = resampled['rsi_14']
            if 'atr' not in resampled.columns and 'atr_14' in resampled.columns:
                resampled['atr'] = resampled['atr_14']
        except Exception as e:
            logger.info(f"Indicator calculation failed: {e}")
            resampled['rsi'] = 50
        
        return resampled


class MultiBacktestWidget(QWidget):
    """멀티 심볼 백테스트 위젯 (v1.7.0)"""
    
    status_updated = pyqtSignal(str, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.backtest = None
        self.bt_thread = None
        self._init_ui()
        self.status_updated.connect(self._on_status_update)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === 설정 영역 ===
        settings = QGroupBox("⚙️ 멀티 심볼 백테스트 설정")
        settings.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #444; 
                border-radius: 5px; 
                margin-top: 10px; 
                padding-top: 10px;
                font-weight: bold; 
            }
        """)
        s_layout = QHBoxLayout(settings)
        
        s_layout.addWidget(QLabel("거래소:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['bybit', 'binance', 'okx', 'bitget'])
        self.exchange_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        s_layout.addWidget(self.exchange_combo)
        
        s_layout.addWidget(QLabel("TF:"))
        self.tf_4h = QCheckBox("4H")
        self.tf_4h.setChecked(True)
        self.tf_1d = QCheckBox("1D")
        self.tf_1d.setChecked(True)
        s_layout.addWidget(self.tf_4h)
        s_layout.addWidget(self.tf_1d)
        
        s_layout.addWidget(QLabel("시드:"))
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(10, 100000)
        self.seed_spin.setValue(100)
        self.seed_spin.setPrefix("$")
        self.seed_spin.setStyleSheet("background: #2b2b2b; color: white;")
        s_layout.addWidget(self.seed_spin)
        
        s_layout.addWidget(QLabel("레버리지:"))
        self.lev_spin = QSpinBox()
        self.lev_spin.setRange(1, 50)
        self.lev_spin.setValue(5)
        self.lev_spin.setSuffix("x")
        self.lev_spin.setStyleSheet("background: #2b2b2b; color: white;")
        s_layout.addWidget(self.lev_spin)
        
        s_layout.addStretch()
        layout.addWidget(settings)
        
        # === 진행 상태 ===
        progress_group = QGroupBox("📊 진행 상태")
        progress_group.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #4CAF50; 
                border-radius: 5px; 
                margin-top: 10px; 
                font-weight: bold; 
                color: #4CAF50; 
            }
        """)
        p_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { 
                border: 1px solid #333; 
                border-radius: 5px; 
                text-align: center; 
                background: #1a1a2e; 
                color: white; 
                height: 25px; 
            }
            QProgressBar::chunk { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #667eea, stop:1 #764ba2); 
            }
        """)
        p_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("대기 중 - 시작 버튼을 눌러주세요")
        self.status_label.setStyleSheet("color: #888;")
        p_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        # === 결과 요약 ===
        result_group = QGroupBox("📈 결과 요약")
        result_group.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #2962ff; 
                border-radius: 5px; 
                margin-top: 10px; 
                font-weight: bold; 
                color: #2962ff; 
            }
        """)
        r_layout = QVBoxLayout(result_group)
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(['항목', '값', '항목', '값'])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setStyleSheet("""
            QTableWidget { background: #1e222d; color: white; }
            QHeaderView::section { background: #2b2b2b; color: white; }
        """)
        self.result_table.setMaximumHeight(150)
        self.result_table.setRowCount(4)
        r_layout.addWidget(self.result_table)
        
        layout.addWidget(result_group)
        
        # === 거래 내역 ===
        trades_group = QGroupBox("📜 거래 내역")
        trades_group.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #FF9800; 
                border-radius: 5px; 
                margin-top: 10px; 
                font-weight: bold; 
                color: #FF9800; 
            }
        """)
        t_layout = QVBoxLayout(trades_group)
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(7)
        self.trades_table.setHorizontalHeaderLabels([
            '심볼', '방향', '진입시간', '청산시간', '청산사유', 'PnL%', 'PnL$'
        ])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setStyleSheet("""
            QTableWidget { background: #1e222d; color: white; }
            QHeaderView::section { background: #2b2b2b; color: white; }
        """)
        t_layout.addWidget(self.trades_table)
        
        layout.addWidget(trades_group)
        
        # === 버튼 ===
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ 멀티 백테스트 시작")
        self.start_btn.setStyleSheet("""
            QPushButton { 
                background: #4CAF50; 
                color: white; 
                padding: 12px 30px; 
                border-radius: 5px; 
                font-weight: bold; 
                font-size: 14px;
            }
            QPushButton:hover { background: #45a049; }
            QPushButton:disabled { background: #555; }
        """)
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton { 
                background: #f44336; 
                color: white; 
                padding: 12px 30px; 
                border-radius: 5px; 
                font-weight: bold; 
            }
            QPushButton:hover { background: #d32f2f; }
            QPushButton:disabled { background: #555; }
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_btn)
        
        self.save_btn = QPushButton("💾 결과 저장")
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton { 
                background: #2196F3; 
                color: white; 
                padding: 12px 30px; 
                border-radius: 5px; 
                font-weight: bold; 
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:disabled { background: #555; }
        """)
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _on_status_update(self, message: str, progress: float):
        """상태 업데이트 (UI 스레드)"""
        self.status_label.setText(message)
        self.progress_bar.setValue(int(progress))
    
    def _status_callback(self, message: str, progress: float):
        """상태 콜백 (워커 스레드에서 호출)"""
        self.status_updated.emit(message, progress)
    
    def _on_start(self):
        """시작 버튼"""
        import threading
        
        try:
            from core.multi_symbol_backtest import MultiSymbolBacktest
        except ImportError:
            QMessageBox.critical(self, "오류", "MultiSymbolBacktest 모듈을 찾을 수 없습니다.")
            return
        
        timeframes = []
        if self.tf_4h.isChecked():
            timeframes.append('4h')
        if self.tf_1d.isChecked():
            timeframes.append('1d')
        
        if not timeframes:
            QMessageBox.warning(self, "경고", "최소 1개 타임프레임을 선택하세요.")
            return
        
        self.backtest = MultiSymbolBacktest(
            exchange=self.exchange_combo.currentText(),
            timeframes=timeframes,
            initial_capital=self.seed_spin.value(),
            leverage=self.lev_spin.value()
        )
        self.backtest.set_status_callback(self._status_callback)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.trades_table.setRowCount(0)
        
        self.bt_thread = threading.Thread(target=self._run_backtest, daemon=True)
        self.bt_thread.start()
    
    def _run_backtest(self):
        """백테스트 실행 (워커 스레드)"""
        try:
            result = self.backtest.run()
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, "_display_result",
                Qt.QueuedConnection,
                Q_ARG(dict, result)
            )
        except Exception as e:
            self._status_callback(f"❌ 오류: {e}", 100)
        finally:
            from PyQt5.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "_on_complete", Qt.QueuedConnection)
    
    def _on_complete(self):
        """완료 후 UI 복원"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.save_btn.setEnabled(True)
    
    def _on_stop(self):
        """중지 버튼"""
        if self.backtest:
            self.backtest.stop()
            self.status_label.setText("⏹ 사용자에 의해 중지됨")
    
    def _on_save(self):
        """결과 저장"""
        if self.backtest:
            filepath = self.backtest.save_result()
            QMessageBox.information(self, "저장 완료", f"결과가 저장되었습니다:\n{filepath}")
    
    def _display_result(self, result: dict):
        """결과 표시"""
        data = [
            ('총 거래', str(result.get('total_trades', 0)), 
             '승률', f"{result.get('win_rate', 0):.1f}%"),
            ('승리', str(result.get('wins', 0)), 
             'PF', f"{result.get('profit_factor', 0):.2f}"),
            ('패배', str(result.get('losses', 0)), 
             'MDD', f"{result.get('max_drawdown', 0):.1f}%"),
            ('초기자본', f"${result.get('initial_capital', 0):.2f}", 
             '최종자본', f"${result.get('final_capital', 0):.2f}"),
        ]
        
        for row, (k1, v1, k2, v2) in enumerate(data):
            self.result_table.setItem(row, 0, QTableWidgetItem(k1))
            self.result_table.setItem(row, 1, QTableWidgetItem(v1))
            self.result_table.setItem(row, 2, QTableWidgetItem(k2))
            self.result_table.setItem(row, 3, QTableWidgetItem(v2))
        
        trades = result.get('trades', [])
        self.trades_table.setRowCount(len(trades))
        
        for row, t in enumerate(trades):
            self.trades_table.setItem(row, 0, QTableWidgetItem(t.get('symbol', '')))
            
            dir_item = QTableWidgetItem(t.get('direction', ''))
            if t.get('direction') == 'Long':
                dir_item.setForeground(QColor('#4CAF50'))
            else:
                dir_item.setForeground(QColor('#f44336'))
            self.trades_table.setItem(row, 1, dir_item)
            
            self.trades_table.setItem(row, 2, QTableWidgetItem(str(t.get('entry_time', ''))[:16]))
            self.trades_table.setItem(row, 3, QTableWidgetItem(str(t.get('exit_time', ''))[:16]))
            self.trades_table.setItem(row, 4, QTableWidgetItem(t.get('exit_reason', '')))
            
            pnl_pct = t.get('pnl_pct', 0)
            pnl_item = QTableWidgetItem(f"{pnl_pct:+.2f}%")
            if pnl_pct > 0:
                pnl_item.setForeground(QColor('#4CAF50'))
            else:
                pnl_item.setForeground(QColor('#f44336'))
            self.trades_table.setItem(row, 5, pnl_item)
            
            pnl_usd = t.get('pnl_usd', 0)
            usd_item = QTableWidgetItem(f"${pnl_usd:+.2f}")
            if pnl_usd > 0:
                usd_item.setForeground(QColor('#4CAF50'))
            else:
                usd_item.setForeground(QColor('#f44336'))
            self.trades_table.setItem(row, 6, usd_item)


class BacktestWidget(QWidget):
    """백테스트 메인 위젯 - 서브탭 컨테이너 (v1.7.0)"""
    
    # SingleBacktestWidget의 시그널을 그대로 노출
    backtest_finished = pyqtSignal(list, object, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        from PyQt5.QtWidgets import QTabWidget
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 서브탭
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #444; 
                border-radius: 4px; 
            }
            QTabBar::tab { 
                background: #2b2b2b; 
                color: #888; 
                padding: 10px 25px; 
                margin-right: 2px; 
                font-weight: bold;
            }
            QTabBar::tab:selected { 
                background: #3c3c3c; 
                color: white; 
                border-bottom: 2px solid #4CAF50; 
            }
            QTabBar::tab:hover { 
                background: #3c3c3c; 
            }
        """)
        
        # 싱글 백테스트 탭 (기존 기능)
        self.single_widget = SingleBacktestWidget()
        self.sub_tabs.addTab(self.single_widget, "📈 싱글 심볼")
        
        # 멀티 백테스트 탭 (v1.7.0 신규) - [HIDDEN]
        # self.multi_widget = MultiBacktestWidget()
        # self.sub_tabs.addTab(self.multi_widget, "📊 멀티 심볼")
        
        layout.addWidget(self.sub_tabs)
        
        # 시그널 연결 (하위 호환성)
        if hasattr(self.single_widget, 'backtest_finished'):
            self.single_widget.backtest_finished.connect(self.backtest_finished.emit)

    def _refresh_data_sources(self):
        """데이터 소스 새로고침 (수집 완료 시 호출)"""
        if hasattr(self, 'single_widget'):
            # 심볼 리스트 갱신을 위해 거래소 변경 이벤트를 다시 트리거
            exchange = self.single_widget.exchange_combo.currentText()
            self.single_widget._on_exchange_changed(exchange)

    def load_strategy_params(self):
        """파라미터 로드 (메인 윈도우에서 호출)"""
        if hasattr(self, 'single_widget'):
            self.single_widget.load_strategy_params()

    def apply_params(self, params: dict):
        """최적화 결과 적용"""
        if hasattr(self, 'single_widget'):
            self.single_widget.apply_params(params)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background-color: #1e1e1e; }")
    w = BacktestWidget()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec_())
