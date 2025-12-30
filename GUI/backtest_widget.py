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
import pyqtgraph as pg

from datetime import datetime
import sys
import os
import json
from pathlib import Path
import pandas as pd
import numpy as np

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
except ImportError:
    def get_preset_manager(): return None
    def get_backtest_params(name=None): return {}
    def save_strategy_params(params): pass

try:
    from constants import EXCHANGE_INFO, TF_MAPPING, TF_RESAMPLE_MAP, DEFAULT_PARAMS
except ImportError:
    EXCHANGE_INFO = {
        "bybit": {"type": "CEX", "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]},
        "binance": {"type": "CEX", "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
    }
    TF_MAPPING = {'1h': '15min', '4h': '1h', '1d': '4h', '1w': '1d'}
    TF_RESAMPLE_MAP = {
        '15min': '15min', '15m': '15min', '30min': '30min', '30m': '30min',
        '1h': '1h', '1H': '1h', '4h': '4h', '4H': '4h', '1d': '1D', '1D': '1D'
    }
    DEFAULT_PARAMS = {'atr_mult': 1.25, 'slippage': 0.0005, 'fee': 0.00055}

try:
    from paths import Paths
except ImportError:
    class Paths:
        CACHE = "data/cache"
        CONFIG = "config"
        BASE = os.getcwd()

# Shared resample import
try:
    from GUI.utils.data_utils import resample_data as shared_resample
except ImportError:
    shared_resample = None


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
            
            print(f"[BT] tolerance={params.get('pattern_tolerance')}, validity={params.get('entry_validity_hours')}h")
            
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
                print(f"Indicator calculation failed: {e}")
            
            self.progress.emit(50)
            
            # Run backtest
            combined_slippage = self.slippage + self.fee
            
            result = self.strategy.run_backtest(
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
                allowed_direction=self.direction  # [NEW] 방향성 필터링 전달
            )
            
            print(f"[BT] Result: {len(result) if result else 0} trades")
            
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
                
                win_count = len([p for p in pnls if p > 0])
                
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




class BacktestWidget(QWidget):
    """Main Backtest Widget"""
    
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
                        
                        print(f"Loading cached data from {latest_db}...")
                        df = dm.load_data(symbol, exchange, timeframe)
            except Exception as e:
                print(f"Cache load failed: {e}")

            from core.strategy_core import AlphaX7Core
            
            if df is not None and not df.empty:
                self.strategy = AlphaX7Core()
                self.strategy.df_15m = df
                print(f"Alpha-X7 Core Loaded with {len(df)} candles")
            else:
                self.strategy = AlphaX7Core()
                self.strategy.df_15m = None
                print("Alpha-X7 Core Loaded (No Data)")
                
        except Exception as e:
            print(f"Strategy load error: {e}")
            self.strategy = None
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Row 1: Data source + Preset
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        row1.addWidget(QLabel("거래소:"))
        self.exchange_combo = QComboBox()
        cex_list = [k for k, v in EXCHANGE_INFO.items() if v.get('type') == 'CEX']
        self.exchange_combo.addItems(cex_list if cex_list else ['bybit', 'binance'])
        self.exchange_combo.setMinimumWidth(80)
        self.exchange_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        self.exchange_combo.currentTextChanged.connect(self._on_exchange_changed)
        row1.addWidget(self.exchange_combo)
        
        row1.addWidget(QLabel("심볼:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setMinimumWidth(100)
        self.symbol_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        row1.addWidget(self.symbol_combo)
        
        row1.addWidget(QLabel("타임프레임:"))
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
        
        row1.addWidget(QLabel("프리셋:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self.preset_combo.setStyleSheet("QComboBox { background: #2b2b2b; color: white; padding: 5px; }")
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        row1.addWidget(self.preset_combo)
        
        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.setToolTip("프리셋 새로고침")
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
        save_btn.setToolTip("프리셋 저장")
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
        
        delete_btn = QPushButton("🗑 삭제")
        delete_btn.setToolTip("프리셋 삭제")
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
        param_grid.addWidget(self._make_label("레버리지:", lbl_style), 0, col)
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 100)
        self.leverage_spin.setValue(3)
        self.leverage_spin.setStyleSheet(spin_style)
        param_grid.addWidget(self.leverage_spin, 0, col + 1)
        
        col += 2
        param_grid.addWidget(self._make_label("슬리피지%:", lbl_style), 0, col)
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setRange(0, 5)
        self.slippage_spin.setValue(0.05)
        self.slippage_spin.setSingleStep(0.01)
        self.slippage_spin.setStyleSheet(spin_style)
        param_grid.addWidget(self.slippage_spin, 0, col + 1)
        
        col += 2
        param_grid.addWidget(self._make_label("수수료%:", lbl_style), 0, col)
        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setRange(0, 1)
        self.fee_spin.setValue(0.055)
        self.fee_spin.setSingleStep(0.005)
        self.fee_spin.setStyleSheet(spin_style)
        param_grid.addWidget(self.fee_spin, 0, col + 1)
        
        col += 2
        param_grid.addWidget(self._make_label("방향:", lbl_style), 0, col)
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
        
        self._run_btn = QPushButton("백테스트 실행")
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
        
        self._stat_trades = self._create_stat_label("총 매매", "0")
        self._stat_winrate = self._create_stat_label("승률", "0%")
        self._stat_simple = self._create_stat_label("단리 수익", "0%")
        self._stat_compound = self._create_stat_label("복리 수익", "0%")
        self._stat_mdd = self._create_stat_label("MDD", "0%")
        
        stats_layout.addWidget(self._stat_trades)
        stats_layout.addWidget(self._stat_winrate)
        stats_layout.addWidget(self._stat_simple)
        stats_layout.addWidget(self._stat_compound)
        stats_layout.addWidget(self._stat_mdd)
        stats_layout.addStretch()
        
        # 결과 저장 버튼
        self.save_result_btn = QPushButton("💾 결과 저장")
        self.save_result_btn.setStyleSheet("""
            QPushButton { background: #4CAF50; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388E3C; }
            QPushButton:disabled { background: #555; }
        """)
        self.save_result_btn.setToolTip("백테스트 결과를 JSON/CSV로 저장")
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
            print(f"Preset refresh error: {e}")
        
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
                if 'filter_tf' in params:
                    info.append(f"Filter:{params.get('filter_tf')}")
                if 'entry_tf' in params:
                    info.append(f"Entry:{params.get('entry_tf')}")
                if 'atr_mult' in params:
                    info.append(f"ATR:{params.get('atr_mult')}")
                self.preset_label.setText(" | ".join(info) if info else "Loaded")
                self.preset_label.setStyleSheet("color: #00e676; font-size: 11px;")
            
        except Exception as e:
            print(f"Preset load error: {e}")
    
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
            print(f"JSON params load error: {e}")
    
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
            print(f"Data load error: {e}")
    
    def _init_result_area(self):
        """결과 영역: 테이블(좌) + 차트(우)"""
        # 스플리터 생성 (좌우 배치)
        self.result_splitter = QSplitter(Qt.Horizontal)
        
        # 좌측: 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            '#', '진입', '청산', '방향', '수익률', '잔고', 'MDD', '기간'
        ])
        
        # 테이블 스타일링
        self.result_table.setStyleSheet("""
            QTableWidget {
                background: #1e222d;
                color: white;
                border: 1px solid #363a45;
                gridline-color: #363a45;
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background: #2962ff; }
            QHeaderView::section {
                background: #131722;
                color: white;
                border: 1px solid #363a45;
                padding: 8px;
                font-weight: bold;
            }
        """)
        # 컬럼 너비를 최소화하여 필요한 만큼만 차지하게 함
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.result_table.verticalHeader().setDefaultSectionSize(36)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        self.result_table.itemSelectionChanged.connect(self._on_trade_selected)
        self.result_splitter.addWidget(self.result_table)

        # 우측: 차트 박스
        self.chart_box = QGroupBox("📊 매매 상세 차트")
        self.chart_box.setStyleSheet("QGroupBox { color: white; font-weight: bold; border: 1px solid #363a45; margin-top: 5px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        chart_layout = QVBoxLayout(self.chart_box)
        chart_layout.setContentsMargins(2, 8, 2, 2)
        chart_layout.setSpacing(0)
        
        self.chart_widget = pg.PlotWidget()
        self.chart_widget.setBackground('#1a1a2e')
        self.chart_widget.showGrid(x=True, y=True, alpha=0.3)
        self.chart_widget.getAxis('bottom').setPen('#666')
        self.chart_widget.getAxis('left').setPen('#666')
        self.chart_widget.setAspectLocked(False)
        self.chart_widget.enableAutoRange()
        
        chart_layout.addWidget(self.chart_widget)
        self.result_splitter.addWidget(self.chart_box)
        
        # 비율 설정: 테이블 40%, 차트 60% (비율 유지)
        self.result_splitter.setStretchFactor(0, 4)
        self.result_splitter.setStretchFactor(1, 6)
        self.result_splitter.setHandleWidth(1)
        self.result_splitter.setSizes([400, 600])
        
        return self.result_splitter

    def _on_trade_selected(self):
        """테이블 행 클릭 시 우측 차트 업데이트"""
        selected = self.result_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        if hasattr(self, 'trades_detail') and row < len(self.trades_detail):
            trade = self.trades_detail[row]
            self._update_chart(trade)

    def _update_chart(self, trade: dict):
        """선택된 거래의 차트 표시"""
        self.chart_widget.clear()
        
        if not hasattr(self, 'candle_data') or self.candle_data is None:
            return

        # 캔들 데이터 추출 (entry 전후 50봉)
        entry_idx = trade.get('entry_idx', 0)
        start = max(0, int(entry_idx) - 25)
        end = min(len(self.candle_data), int(entry_idx) + 25)
        
        candles = self.candle_data.iloc[start:end]
        
        if candles.empty:
            return
        
        # 가격 범위 계산 (Y축 스케일링용)
        price_min = candles['low'].min()
        price_max = candles['high'].max()
        price_margin = (price_max - price_min) * 0.1
        
        # 캔들 차트 그리기 (OHLC 바 스타일)
        for i, (idx, c) in enumerate(candles.iterrows()):
            color = '#00d26a' if c['close'] >= c['open'] else '#ff6b6b'
            # High-Low (Wick)
            self.chart_widget.plot([i, i], [c['low'], c['high']], pen=pg.mkPen(color, width=1))
            # Open-Close (Body)
            body_width = 4
            self.chart_widget.plot([i, i], [c['open'], c['close']], pen=pg.mkPen(color, width=body_width))
        
        # === Trade Markers ===
        direction = trade.get('type', trade.get('direction', 'Long'))
        is_long = 'Long' in direction
        
        # Entry Marker (큰 화살표 + 라벨)
        entry_val = trade.get('entry_price', trade.get('entry', 0))
        entry_pos = int(entry_idx) - start
        
        if entry_val and 0 <= entry_pos < len(candles):
            # 진입 마커 (위/아래 삼각형)
            symbol = 't' if is_long else 't1'  # t=up, t1=down
            self.chart_widget.plot([entry_pos], [entry_val], 
                                   pen=None, symbol=symbol, symbolBrush='#00d26a', symbolSize=18)
            # 텍스트 라벨
            entry_label = pg.TextItem(f"Entry\n${entry_val:,.0f}", color='#00d26a', anchor=(0.5, 1.2 if is_long else -0.2))
            entry_label.setPos(entry_pos, entry_val)
            self.chart_widget.addItem(entry_label)
        
        # Exit Marker (있으면)
        exit_val = trade.get('exit_price', trade.get('exit', 0))
        exit_idx = trade.get('exit_idx', 0)
        exit_pos = int(exit_idx) - start if exit_idx else -1
        
        if exit_val and 0 <= exit_pos < len(candles):
            pnl = trade.get('pnl', 0)
            exit_color = '#00d26a' if pnl >= 0 else '#ff6b6b'
            symbol = 't1' if is_long else 't'  # 반대 방향
            self.chart_widget.plot([exit_pos], [exit_val],
                                   pen=None, symbol=symbol, symbolBrush=exit_color, symbolSize=18)
            exit_label = pg.TextItem(f"Exit\n{pnl:+.1f}%", color=exit_color, anchor=(0.5, -0.2 if is_long else 1.2))
            exit_label.setPos(exit_pos, exit_val)
            self.chart_widget.addItem(exit_label)
        
        # SL Line (손절선 - 빨간 점선)
        sl = trade.get('sl', trade.get('stop_loss', trade.get('initial_sl', 0)))
        if sl and sl > 0 and price_min <= sl <= price_max * 1.1:
            sl_line = pg.InfiniteLine(pos=sl, angle=0, pen=pg.mkPen('#ef5350', width=2, style=pg.QtCore.Qt.DashLine))
            self.chart_widget.addItem(sl_line)
            sl_label = pg.TextItem(f"SL ${sl:,.0f}", color='#ef5350', anchor=(0, 0.5))
            sl_label.setPos(len(candles) - 1, sl)
            self.chart_widget.addItem(sl_label)
        
        # Entry Line (진입 가격 수평선 - 녹색 점선)
        if entry_val and entry_val > 0:
            entry_line = pg.InfiniteLine(pos=entry_val, angle=0, pen=pg.mkPen('#00d26a', width=1, style=pg.QtCore.Qt.DotLine))
            self.chart_widget.addItem(entry_line)
        
        # [FIX] X/Y 축 자동 피팅
        self.chart_widget.setXRange(0, len(candles), padding=0.05)
        self.chart_widget.setYRange(price_min - price_margin, price_max + price_margin, padding=0)

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
        
        print(f"[BT] Preset: {self.preset_combo.currentText()}")
        print(f"[BT] Params: filter_tf={strategy_params.get('filter_tf')}, atr_mult={strategy_params.get('atr_mult')}")
        print(f"[BT] Cost: slippage={slippage:.4f} + fee={fee:.4f} = total_cost={total_cost:.4f}")
        
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
            print(f"Indicator calculation failed: {e}")
            resampled['rsi'] = 50
        
        return resampled


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background-color: #1e1e1e; }")
    w = BacktestWidget()
    w.show()
    sys.exit(app.exec_())
