"""
MultiExplorer - 전체 심볼 자동 수집 + 분석 (v2.0)

Extracted from trading_dashboard.py for Phase 10.2.2
"""

import logging
logger = logging.getLogger(__name__)

import requests


from PyQt6.QtWidgets import (
    QLabel, QPushButton, QComboBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QHBoxLayout,
    QVBoxLayout
)
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from locales.lang_manager import t

# Fallback imports
try:
    from constants import EXCHANGE_INFO
except ImportError:
    EXCHANGE_INFO = {
        "bybit": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]},
        "binance": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]},
        "okx": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]},
        "bitget": {"symbols": ["BTCUSDT", "ETHUSDT"]},
    }

try:
    HAS_MULTI_SNIPER = True
except ImportError:
    HAS_MULTI_SNIPER = False


class MultiExplorer(QGroupBox):
    """전체 심볼 자동 수집 + 분석 (v2.0)"""
    
    start_signal = pyqtSignal()
    stop_signal = pyqtSignal()
    add_coin_signal = pyqtSignal(str)  # 심볼 추가 시그널
    
    def __init__(self, parent=None):
        super().__init__(t("multi_explorer.title", "🔍 Multi Explorer (Premium)"), parent)
        self.is_scanning = False
        self.current_idx = 0
        self.total_symbols = 0
        self.signals_found = 0
        self.collected_count = 0
        self.symbols = []
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #9C27B0;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
                color: #9C27B0;
                font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Row 1: 거래소 + 모드 선택
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel(t("multi_explorer.exchange", "거래소:")))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['bybit', 'binance', 'okx', 'bitget'])
        self.exchange_combo.setStyleSheet("background: #2b2b2b; color: white; min-width: 80px;")
        row1.addWidget(self.exchange_combo)
        
        row1.addWidget(QLabel(t("multi_explorer.mode", "모드:")))
        self.scan_combo = QComboBox()
        self.scan_combo.addItems([
            t("multi_explorer.mode_all", "🌐 전체 (All USDT)"),
            t("multi_explorer.mode_top_vol", "📊 Top 100 거래량"),
            t("multi_explorer.mode_top_gainers", "🔥 Top 50 상승률")
        ])
        self.scan_combo.setStyleSheet("background: #2b2b2b; color: white; min-width: 120px;")
        row1.addWidget(self.scan_combo)
        
        row1.addStretch()
        
        # [REMOVE] row1 buttons moved to bottom
        layout.addLayout(row1)
        
        # Row 2: 진행 상태
        progress_layout = QHBoxLayout()
        
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 5px;
                text-align: center;
                background: #1a1a2e;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
            }
        """)
        self.progress_bar.setMinimumWidth(200)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel(t("multi_explorer.waiting", "대기 중"))
        self.status_label.setStyleSheet("color: #888; min-width: 250px;")
        progress_layout.addWidget(self.status_label)
        
        layout.addLayout(progress_layout)
        
        # Row 3: 통계
        stats_layout = QHBoxLayout()
        self.stats_collected = QLabel(t("multi_explorer.stat_collected", "📥 수집: 0").replace("{n}", "0"))
        self.stats_collected.setStyleSheet("color: #00d4ff;")
        self.stats_analyzed = QLabel(t("multi_explorer.stat_analyzed", "🔍 분석: 0").replace("{n}", "0"))
        self.stats_analyzed.setStyleSheet("color: #ffa500;")
        self.stats_signals = QLabel(t("multi_explorer.stat_signals", "✅ 시그널: 0").replace("{n}", "0"))
        self.stats_signals.setStyleSheet("color: #00d26a; font-weight: bold;")
        stats_layout.addWidget(self.stats_collected)
        stats_layout.addWidget(self.stats_analyzed)
        stats_layout.addWidget(self.stats_signals)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels([
            t("multi_explorer.header_coin", "코인"),
            t("multi_explorer.header_signal", "신호"),
            t("multi_explorer.header_price", "가격"),
            t("multi_explorer.header_score", "점수"),
            t("multi_explorer.header_candles", "캔들"),
            t("multi_explorer.header_action", "액션")
        ])
        if header := self.result_table.horizontalHeader():
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        if v_header := self.result_table.verticalHeader():
            v_header.setVisible(False)
        self.result_table.setMinimumHeight(200)
        self.result_table.setStyleSheet("""
            QTableWidget {
                background: #1a1a2e;
                gridline-color: #333;
                color: white;
            }
            QHeaderView::section {
                background: #252542;
                color: #00d4ff;
                font-weight: bold;
                padding: 5px;
                border: 1px solid #333;
            }
        """)
        layout.addWidget(self.result_table)
        
        # [NEW] 버튼 행 하단 이동
        bottom_btn_layout = QHBoxLayout()
        bottom_btn_layout.addStretch()
        
        # 시작/중지 버튼
        self.start_btn = QPushButton(t("multi_explorer.btn_scan_all", "▶ 전체 스캔"))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d26a, stop:1 #00a854);
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
            QPushButton:hover { background: #00a854; }
        """)
        self.start_btn.clicked.connect(self._toggle_scan)
        bottom_btn_layout.addWidget(self.start_btn)
        
        # [NEW] Sniper 버튼
        self.sniper_btn = QPushButton(t("multi_explorer.btn_sniper", "🎯 Sniper"))
        self.sniper_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
            QPushButton:hover { background: #764ba2; }
        """)
        self.sniper_btn.setToolTip(t("multi_explorer.tip_sniper", "Top 100 코인 자동 스캔 및 매매 (Premium)"))
        self.sniper_btn.clicked.connect(self._toggle_sniper)
        bottom_btn_layout.addWidget(self.sniper_btn)
        
        layout.addLayout(bottom_btn_layout)
    
    def _toggle_scan(self):
        """스캔 시작/중지 토글"""
        if self.is_scanning:
            self._stop_scan()
        else:
            self._start_scan()
    
    def _start_scan(self):
        """전체 스캔 시작"""
        self.is_scanning = True
        self.start_btn.setText(t("multi_explorer.btn_stop_scan", "⏹ 스캔 중지"))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #ff4757;
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
        """)
        
        # 초기화
        self.current_idx = 0
        self.signals_found = 0
        self.collected_count = 0
        self.result_table.setRowCount(0)
        
        # 심볼 조회
        mode = self.scan_combo.currentIndex()
        self.status_label.setText(t("multi_explorer.msg_fetching_list", "🔄 심볼 목록 조회 중..."))
        
        if mode == 0:
            self.symbols = self._get_all_symbols()
        elif mode == 1:
            self.symbols = self._get_top_volume(100)
        else:
            self.symbols = self._get_top_gainers(50)
        
        self.total_symbols = len(self.symbols)
        self.progress_bar.setMaximum(self.total_symbols)
        self.progress_bar.setValue(0)
        
        self.status_label.setText(t("multi_explorer.msg_scanning_start", "🚀 {n}개 심볼 스캔 시작").replace("{n}", str(self.total_symbols)))
        logger.info(f"[MultiExplorer] 스캔 시작: {self.total_symbols}개")
        
        # 스캔 시작
        QTimer.singleShot(100, self._process_next)
    
    def _stop_scan(self):
        """스캔 중지"""
        self.is_scanning = False
        self.start_btn.setText(t("multi_explorer.btn_scan_all", "▶ 전체 스캔"))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d26a, stop:1 #00a854);
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
        """)
        self.status_label.setText(
            t("multi_explorer.msg_stopped", "⏹ 중지됨 ({current}/{total})")
            .replace("{current}", str(self.current_idx))
            .replace("{total}", str(self.total_symbols))
        )
        self.stop_signal.emit()
    
    # [NEW] Sniper 토글
    def _toggle_sniper(self):
        """Sniper 시작/종료 토글"""
        # 부모 위젯 (TradingDashboard)에 위임
        parent = self.parent()
        while parent:
            if hasattr(parent, '_start_sniper') and hasattr(parent, '_stop_sniper'):
                # 현재 상태 확인
                if hasattr(parent, '_sniper') and parent._sniper and getattr(parent._sniper, 'running', False): # type: ignore
                    # 종료
                    parent._stop_sniper() # type: ignore
                    self.sniper_btn.setText(t("multi_explorer.btn_sniper", "🎯 Sniper"))
                    self.sniper_btn.setStyleSheet("""
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #667eea, stop:1 #764ba2);
                            color: white; font-weight: bold;
                            padding: 8px 20px; border-radius: 5px;
                        }
                        QPushButton:hover { background: #764ba2; }
                    """)
                else:
                    # 시작
                    exchange = self.exchange_combo.currentText().lower()
                    parent._start_sniper(exchange=exchange, total_seed=1000) # type: ignore
                    self.sniper_btn.setText(t("multi_explorer.btn_stop_sniper", "⏹ Sniper 종료"))
                    self.sniper_btn.setStyleSheet("""
                        QPushButton {
                            background: #e74c3c;
                            color: white; font-weight: bold;
                            padding: 8px 20px; border-radius: 5px;
                        }
                        QPushButton:hover { background: #c0392b; }
                    """)
                return
            parent = parent.parent() if hasattr(parent, 'parent') else None
        
        # 부모에서 못 찾은 경우
        self.status_label.setText("❌ Sniper 연동 불가")
    
    def _get_all_symbols(self) -> list:
        """거래소 전체 USDT 심볼"""
        exchange = self.exchange_combo.currentText().lower()
        
        try:
            if 'bybit' in exchange:
                url = "https://api.bybit.com/v5/market/tickers"
                params = {"category": "linear"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get("retCode") == 0:
                    tickers = data.get("result", {}).get("list", [])
                    symbols = [t["symbol"] for t in tickers 
                              if t["symbol"].endswith("USDT")
                              and "1000" not in t["symbol"]]  # 레버리지 토큰 제외
                    logger.info(f"[MultiExplorer] {exchange} 전체 심볼: {len(symbols)}개")
                    return sorted(symbols)
            
            elif 'binance' in exchange:
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                response = requests.get(url, timeout=10)
                tickers = response.json()
                symbols = [t["symbol"] for t in tickers if t["symbol"].endswith("USDT")]
                logger.info(f"[MultiExplorer] {exchange} 전체 심볼: {len(symbols)}개")
                return sorted(symbols)
            
            elif 'okx' in exchange:
                url = "https://www.okx.com/api/v5/market/tickers"
                params = {"instType": "SWAP"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data.get("code") == "0":
                    tickers = data.get("data", [])
                    symbols = [t["instId"].replace("-USDT-SWAP", "USDT") 
                              for t in tickers if "USDT" in t["instId"]]
                    logger.info(f"[MultiExplorer] {exchange} 전체 심볼: {len(symbols)}개")
                    return sorted(symbols)
        
        except Exception as e:
            logger.info(f"[MultiExplorer] 심볼 조회 실패: {e}")
        
        return ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "DOGEUSDT"]
    
    def _get_top_volume(self, count: int = 100) -> list:
        """거래량 상위"""
        exchange = self.exchange_combo.currentText().lower()
        
        try:
            if 'bybit' in exchange:
                url = "https://api.bybit.com/v5/market/tickers"
                params = {"category": "linear"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get("retCode") == 0:
                    tickers = data.get("result", {}).get("list", [])
                    usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
                    sorted_t = sorted(usdt, key=lambda x: float(x.get("turnover24h", 0)), reverse=True)
                    symbols = [t["symbol"] for t in sorted_t[:count]]
                    logger.info(f"[MultiExplorer] Top {count} Volume: {symbols[:3]}...")
                    return symbols
            
            elif 'binance' in exchange:
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                response = requests.get(url, timeout=10)
                tickers = response.json()
                usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
                sorted_t = sorted(usdt, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
                return [t["symbol"] for t in sorted_t[:count]]
        
        except Exception as e:
            logger.info(f"[MultiExplorer] 거래량 조회 실패: {e}")
        
        return self._get_all_symbols()[:count]
    
    def _get_top_gainers(self, count: int = 50) -> list:
        """상승률 상위"""
        exchange = self.exchange_combo.currentText().lower()
        
        try:
            if 'bybit' in exchange:
                url = "https://api.bybit.com/v5/market/tickers"
                params = {"category": "linear"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get("retCode") == 0:
                    tickers = data.get("result", {}).get("list", [])
                    usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
                    sorted_t = sorted(usdt, key=lambda x: float(x.get("price24hPcnt", 0)), reverse=True)
                    symbols = [t["symbol"] for t in sorted_t[:count]]
                    logger.info(f"[MultiExplorer] Top {count} Gainers: {symbols[:3]}...")
                    return symbols
            
            elif 'binance' in exchange:
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                response = requests.get(url, timeout=10)
                tickers = response.json()
                usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
                sorted_t = sorted(usdt, key=lambda x: float(x.get("priceChangePercent", 0)), reverse=True)
                return [t["symbol"] for t in sorted_t[:count]]
        
        except Exception as e:
            logger.info(f"[MultiExplorer] 상승률 조회 실패: {e}")
        
        return self._get_all_symbols()[:count]
    
    def _process_next(self):
        """다음 심볼 처리"""
        if not self.is_scanning:
            return
        
        if self.current_idx >= self.total_symbols:
            self._scan_complete()
            return
        
        symbol = self.symbols[self.current_idx]
        self._process_symbol(symbol)
    
    def _process_symbol(self, symbol: str):
        """심볼 처리 - 캐시 없으면 자동 다운로드"""
        try:
            import pandas as pd
            from pathlib import Path
            from paths import Paths
            from GUI.data_cache import DataManager
            
            exchange = self.exchange_combo.currentText().lower()
            symbol_clean = symbol.lower().replace('/', '').replace('-', '')
            cache_path = Path(Paths.CACHE) / f"{exchange}_{symbol_clean}_15m.parquet"
            
            dm = DataManager()
            df = None
            candle_count = 0
            
            # 1. 캐시 확인
            if cache_path.exists():
                try:
                    df = pd.read_parquet(cache_path)
                    candle_count = len(df) if df is not None else 0
                except Exception as e:
                    logging.debug(f"[CACHE] Parquet 읽기 실패: {e}")
                    candle_count = 0
            
            # 2. 캐시 부족 → 자동 다운로드 (상장일부터)
            min_candles = 5000  # 최소 5000봉 (MTF 분석용)
            
            if df is None or candle_count < min_candles:
                self.status_label.setText(
                    t("multi_explorer.msg_downloading", "📥 [{current}/{total}] {symbol} 다운로드...")
                    .replace("{current}", str(self.current_idx+1))
                    .replace("{total}", str(self.total_symbols))
                    .replace("{symbol}", symbol)
                )
                
                try:
                    df = dm.download(
                        symbol=symbol,
                        timeframe='15m',
                        exchange=exchange,
                        limit=50000  # 최대 50000봉
                    )
                    
                    if df is not None and len(df) > 0:
                        candle_count = len(df)
                        self.collected_count += 1
                        self.stats_collected.setText(t("multi_explorer.stat_collected", "📥 수집: {n}").replace("{n}", str(self.collected_count)))
                        logger.info(f"[MultiExplorer] {symbol} 다운로드: {candle_count}봉")
                        
                except Exception as e:
                    logger.info(f"[MultiExplorer] {symbol} 다운로드 실패: {e}")
            
            # 3. 데이터 부족 → 스킵
            if df is None or candle_count < 500:
                self._next_symbol()
                return
            
            # 4. 리샘플링 (4h 필터용)
            self.status_label.setText(
                t("multi_explorer.msg_analyzing", "🔄 [{current}/{total}] {symbol} 분석...")
                .replace("{current}", str(self.current_idx+1))
                .replace("{total}", str(self.total_symbols))
                .replace("{symbol}", symbol)
            )
            
            df_4h = dm.resample(df, '4h') if hasattr(dm, 'resample') else None
            
            # 5. 시그널 감지
            try:
                from core.strategy_core import AlphaX7Core
                
                df_1h = dm.resample(df, '1h') if hasattr(dm, 'resample') else df
                strategy = AlphaX7Core()
                
                # [수정] AlphaX7Core에는 detect_pattern 대신 detect_signal이 있음
                if hasattr(strategy, 'detect_signal'):
                    # detect_signal(df_1h, df_15m, ...)
                    signal_obj = strategy.detect_signal(df_1h, df)
                    if signal_obj:
                        # signal_obj는 TradeSignal 객체임
                        signal = {
                            'direction': getattr(signal_obj, 'signal_type', None),
                            'strength': 80
                        }
                
                # 시그널 처리
                if signal:
                    direction = signal.get('direction') if isinstance(signal, dict) else getattr(signal, 'direction', None)
                    strength = signal.get('strength', 80) if isinstance(signal, dict) else getattr(signal, 'strength', 80)
                    
                    if direction:
                        self.signals_found += 1
                        self.stats_signals.setText(t("multi_explorer.stat_signals", "✅ 시그널: {n}").replace("{n}", str(self.signals_found)))
                        
                        self._add_result(
                            symbol=symbol,
                            signal=direction,
                            price=float(df['close'].iloc[-1]),
                            score=strength,
                            candles=candle_count
                        )
                        logger.info(f"[MultiExplorer] ✅ {symbol}: {direction}")
            
            except Exception as e:
                pass  # Error silenced
            
            self.stats_analyzed.setText(t("multi_explorer.stat_analyzed", "🔍 분석: {n}").replace("{n}", str(self.current_idx + 1)))
        except Exception as e:
            logger.info(f"[MultiExplorer] {symbol} 오류: {e}")
        
        self._next_symbol()
    
    def _next_symbol(self):
        """다음 심볼로"""
        self.current_idx += 1
        self.progress_bar.setValue(self.current_idx)
        
        # API 속도 제한 (100ms)
        QTimer.singleShot(100, self._process_next)
    
    def _add_result(self, symbol: str, signal: str, price: float, score: int, candles: int):
        """결과 테이블에 추가"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        # Symbol
        self.result_table.setItem(row, 0, QTableWidgetItem(symbol))
        
        # Signal (색상)
        signal_item = QTableWidgetItem(signal.upper())
        if signal.lower() == 'long':
            signal_item.setBackground(QColor(0, 210, 106, 50))
            signal_item.setForeground(QColor(0, 210, 106))
        else:
            signal_item.setBackground(QColor(255, 71, 87, 50))
            signal_item.setForeground(QColor(255, 71, 87))
        self.result_table.setItem(row, 1, signal_item)
        
        # Price
        price_str = f"{price:.4f}" if price < 1 else f"{price:.2f}"
        self.result_table.setItem(row, 2, QTableWidgetItem(price_str))
        
        # Score
        self.result_table.setItem(row, 3, QTableWidgetItem(f"{score}"))
        
        # Candles
        self.result_table.setItem(row, 4, QTableWidgetItem(f"{candles:,}"))
        
        # Action 버튼
        add_btn = QPushButton(t("multi_explorer.btn_add", "+ 추가"))
        add_btn.setStyleSheet("background: #667eea; color: white; border-radius: 3px; padding: 3px 8px;")
        add_btn.clicked.connect(lambda checked, s=symbol: self.add_coin_signal.emit(s))
        self.result_table.setCellWidget(row, 5, add_btn)
        
        # 자동 스크롤
        self.result_table.scrollToBottom()
    
    def _scan_complete(self):
        """스캔 완료"""
        self.is_scanning = False
        self.start_btn.setText(t("multi_explorer.btn_scan_all", "▶ 전체 스캔"))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d26a, stop:1 #00a854);
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
        """)
        self.status_label.setText(
            t("multi_explorer.complete_status", "✅ 완료! {total}개 스캔, {found}개 시그널")
            .replace("{total}", str(self.total_symbols))
            .replace("{found}", str(self.signals_found))
        )
        logger.info(f"[MultiExplorer] 스캔 완료: {self.total_symbols}개 중 {self.signals_found}개 시그널")
        self.stop_signal.emit()
    
    def update_status(self, text: str, color: str = "#4CAF50"):
        """상태 업데이트 (호환용)"""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")
