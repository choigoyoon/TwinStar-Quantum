# data_collector_widget.py - 데이터 수집 위젯

from locales.lang_manager import t
import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QDateEdit, QSpinBox, QProgressBar,
    QTextEdit, QGridLayout, QMessageBox, QCheckBox, QListWidget,
    QListWidgetItem, QTabWidget, QLineEdit
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class DownloadThread(QThread):
    """데이터 다운로드 스레드"""
    progress = pyqtSignal(int, str)  # percent, message
    finished = pyqtSignal(str, int)  # symbol, count
    error = pyqtSignal(str, str)  # symbol, error message
    
    def __init__(self, symbols, exchange, timeframe, start_date, end_date):
        super().__init__()
        self.symbols = symbols
        self.exchange = exchange
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self._running = True
        self._current_symbol = ""
        self._current_count = 0
    
    def run(self):
        try:
            print(f"[Download] 시작: {len(self.symbols)}개 심볼")
            from data_manager import DataManager
            dm = DataManager()
            
            total = len(self.symbols)
            
            for i, symbol in enumerate(self.symbols):
                if not self._running:
                    print("[Download] 중지됨")
                    break
                
                self._current_symbol = symbol
                self._current_count = 0
                
                # 초기 진행률
                base_progress = int((i / total) * 100)
                self.progress.emit(base_progress, f"📥 {symbol} 다운로드 중...")
                print(f"[Download] {i+1}/{total}: {symbol}")
                
                try:
                    # 진행률 콜백
                    def on_progress(candle_count):
                        self._current_count = candle_count
                        msg = f"📥 {symbol}: {int(candle_count):,}개 캔들..."
                        # 같은 심볼 내에서의 세부 진행률
                        sub_progress = min(base_progress + int(10 / total), 99)
                        self.progress.emit(sub_progress, msg)
                    
                    # 지표 생성기 로드
                    from indicator_generator import IndicatorGenerator
                    
                    df = dm.download(
                        symbol=symbol,
                        timeframe=self.timeframe,
                        start_date=self.start_date,
                        end_date=self.end_date,
                        exchange=self.exchange,
                        limit=500000,
                        progress_callback=on_progress,
                        processor=IndicatorGenerator.add_all_indicators  # 지표 추가 콜백 전달
                    )
                    
                    count = len(df) if df is not None else 0
                    self.finished.emit(symbol, count)
                    print(f"[Download] ✅ {symbol}: {count:,}개")
                    
                except Exception as e:
                    self.error.emit(symbol, str(e))
                    print(f"[Download] ❌ {symbol}: {e}")
            
            self.progress.emit(100, "✅ 다운로드 완료!")
            print("[Download] 완료!")
            
        except Exception as e:
            self.error.emit("System", str(e))
            print(f"[Download] 시스템 에러: {e}")
    
    def stop(self):
        self._running = False


class DataCollectorWidget(QWidget):
    """데이터 수집 위젯"""
    
    download_finished = pyqtSignal(str, int)  # symbol, count
    
    # 주요 코인 목록
    POPULAR_SYMBOLS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT",
        "LTCUSDT", "ATOMUSDT", "UNIUSDT", "ETCUSDT", "APTUSDT",
        "ARBUSDT", "OPUSDT", "SUIUSDT", "NEARUSDT", "FILUSDT"
    ]
    
    TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    
    def __init__(self):
        super().__init__()
        self._download_thread = None
        self._init_ui()
    
    def closeEvent(self, event):
        """안전한 QThread 종료"""
        if hasattr(self, '_download_thread') and self._download_thread and self._download_thread.isRunning():
            self._download_thread.quit()
            self._download_thread.wait(3000)
        super().closeEvent(event)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 헤더
        header = QLabel("📥 데이터 수집")
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
        
        tabs.addTab(self._create_download_tab(), "📥 Download")
        tabs.addTab(self._create_status_tab(), "📊 Status")
        
        layout.addWidget(tabs)
    
    def _create_download_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 거래소 & 시장 타입 & 타임프레임
        top_layout = QHBoxLayout()
        
        top_layout.addWidget(QLabel("거래소:"))
        self.exchange_combo = QComboBox()
        # CEX만 (DEX는 과거 데이터 API 미지원)
        self.exchange_combo.addItems(["bybit", "binance", "okx", "bitget", "bithumb", "upbit", "bingx"])
        self.exchange_combo.setMinimumWidth(100)
        top_layout.addWidget(self.exchange_combo)
        
        top_layout.addWidget(QLabel("시장:"))
        self.market_type_combo = QComboBox()
        self.market_type_combo.addItems(["선물 (swap)", "현물 (spot)"])
        self.market_type_combo.setMinimumWidth(120)
        top_layout.addWidget(self.market_type_combo)
        
        # 타임프레임은 1h 고정 (UI에서 제거됨)
        self.timeframe_combo = None  # 호환성 유지용
        
        # 심볼 새로고침 버튼
        self.refresh_symbols_btn = QPushButton("🔄 심볼 새로고침")
        self.refresh_symbols_btn.setStyleSheet("""
            QPushButton { background: #2962FF; color: white; padding: 5px 15px; }
            QPushButton:hover { background: #1e88e5; }
        """)
        self.refresh_symbols_btn.clicked.connect(self._refresh_symbols)
        top_layout.addWidget(self.refresh_symbols_btn)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # 심볼 선택
        symbol_group = QGroupBox(t("data.select_symbols"))
        symbol_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        symbol_layout = QVBoxLayout(symbol_group)
        
        # 빠른 선택 버튼 - Row 1: 선택 + Top N
        btn_row1 = QHBoxLayout()
        
        select_all_btn = QPushButton(t("common.select_all"))
        select_all_btn.clicked.connect(self._select_all)
        btn_row1.addWidget(select_all_btn)
        
        select_none_btn = QPushButton(t("common.clear_all"))
        select_none_btn.clicked.connect(self._select_none)
        btn_row1.addWidget(select_none_btn)
        
        btn_row1.addStretch()
        
        select_top10_btn = QPushButton("Top 10")
        select_top10_btn.clicked.connect(self._select_top10)
        btn_row1.addWidget(select_top10_btn)
        
        select_top50_btn = QPushButton("Top 50")
        select_top50_btn.clicked.connect(lambda: self._select_top_n(50))
        btn_row1.addWidget(select_top50_btn)
        
        select_top100_btn = QPushButton("Top 100")
        select_top100_btn.clicked.connect(lambda: self._select_top_n(100))
        btn_row1.addWidget(select_top100_btn)
        
        symbol_layout.addLayout(btn_row1)
        
        # 빠른 선택 버튼 - Row 2: 마켓 필터
        btn_row2 = QHBoxLayout()
        
        new_listing_btn = QPushButton("🆕 신규")
        new_listing_btn.setToolTip("최근 상장된 코인 선택")
        new_listing_btn.clicked.connect(self._select_new_listings)
        new_listing_btn.setStyleSheet("color: #4CAF50;")
        btn_row2.addWidget(new_listing_btn)
        
        gainers_btn = QPushButton("📈 급등")
        gainers_btn.setToolTip("24시간 상승률 상위 코인")
        gainers_btn.clicked.connect(self._select_top_gainers)
        gainers_btn.setStyleSheet("color: #00e676;")
        btn_row2.addWidget(gainers_btn)
        
        losers_btn = QPushButton("📉 급락")
        losers_btn.setToolTip("24시간 하락률 상위 코인")
        losers_btn.clicked.connect(self._select_top_losers)
        losers_btn.setStyleSheet("color: #f44336;")
        btn_row2.addWidget(losers_btn)
        
        btn_row2.addStretch()
        symbol_layout.addLayout(btn_row2)
        
        # 검색창
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("심볼 검색 (예: DOGE, BTC)")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #1e2330;
                color: white;
                border: 1px solid #2962FF;
                padding: 8px;
                border-radius: 4px;
            }
        """)
        self.search_input.textChanged.connect(self._filter_symbols)
        search_layout.addWidget(self.search_input)
        symbol_layout.addLayout(search_layout)
        
        # 심볼 리스트 (체크박스)
        self.symbol_list = QListWidget()
        self.symbol_list.setStyleSheet("""
            QListWidget {
                background: #0b0e14;
                color: white;
                border: 1px solid #2a2e3b;
            }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background: #2962FF; }
        """)
        symbol_layout.addWidget(self.symbol_list)
        
        # 콤보 변경 시 재로드
        self.exchange_combo.currentTextChanged.connect(self._on_exchange_changed)
        self.market_type_combo.currentTextChanged.connect(self._load_symbols)
        
        
        # 커스텀 심볼 입력
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("사용자:"))
        self.custom_symbol = QComboBox()
        self.custom_symbol.setEditable(True)
        self.custom_symbol.setPlaceholderText("Enter symbol (e.g., DOGEUSDT)")
        custom_layout.addWidget(self.custom_symbol)
        
        add_btn = QPushButton(t("common.add"))
        add_btn.clicked.connect(self._add_custom)
        custom_layout.addWidget(add_btn)
        
        symbol_layout.addLayout(custom_layout)
        layout.addWidget(symbol_group)
        
        # 기간 설정 (처음부터 현재까지)
        period_layout = QHBoxLayout()
        
        period_layout.addWidget(QLabel("Start:"))
        self.start_date = QDateEdit()
        # 2017년 1월 1일부터 (암호화폐 데이터 시작점)
        self.start_date.setDate(QDate(2017, 1, 1))
        self.start_date.setCalendarPopup(True)
        period_layout.addWidget(self.start_date)
        
        period_layout.addWidget(QLabel("End:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        period_layout.addWidget(self.end_date)
        
        # [NEW] 상장일부터 체크박스
        self.since_listing_chk = QCheckBox("Since Listing (상장일부터)")
        self.since_listing_chk.setStyleSheet("color: white; font-weight: bold;")
        self.since_listing_chk.toggled.connect(self._toggle_date_edit)
        period_layout.addWidget(self.since_listing_chk)
        
        period_layout.addStretch()
        layout.addLayout(period_layout)
        
        # 진행률
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
            QProgressBar::chunk { background-color: #26a69a; }
        """)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("대기 중...")
        self.status_label.setStyleSheet("""
            color: #ffd700;
            font-size: 14px;
            font-weight: bold;
            padding: 5px;
        """)
        layout.addWidget(self.status_label)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("📥 다운로드 시작")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background: #26a69a; color: white;
                padding: 15px 40px; font-size: 16px; font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background: #2bbd9a; }
            QPushButton:disabled { background: #555; }
        """)
        self.download_btn.clicked.connect(self._start_download)
        btn_layout.addWidget(self.download_btn)
        
        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #ef5350; color: white;
                padding: 15px 30px; font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background: #f06560; }
            QPushButton:disabled { background: #555; }
        """)
        self.stop_btn.clicked.connect(self._stop_download)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 로그
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #0b0e14; color: #d1d4dc;
                border: 1px solid #2a2e3b;
                font-family: 'Consolas', monospace; font-size: 12px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # 초기 심볼 로드 (UI 초기화 후 실행)
        self._load_symbols()
        
        return widget

    def _on_exchange_changed(self, exchange_name: str):
        """거래소 변경 시 시장 타입 자동 조정"""
        is_krw_exchange = exchange_name.lower() in ['bithumb', 'upbit']
        
        if is_krw_exchange:
            # KRW 거래소는 현물만 지원 → 현물로 고정
            self.market_type_combo.setCurrentText("현물 (spot)")
            self.market_type_combo.setEnabled(False)
            self.log_text.append(f"ℹ️ {exchange_name}은 현물(KRW) 전용입니다")
        else:
            # USDT 거래소는 선물/현물 선택 가능
            self.market_type_combo.setEnabled(True)
        
        # 심볼 재로드
        self._load_symbols()

    def _toggle_date_edit(self, checked):
        """상장일부터 체크 시 시작 날짜 비활성화"""
        self.start_date.setEnabled(not checked)
    
    def _create_status_tab(self):
        """캐시 상태 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 새로고침 버튼
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_cache_status)
        layout.addWidget(refresh_btn)
        
        # 캐시 상태 표시
        self.cache_text = QTextEdit()
        self.cache_text.setReadOnly(True)
        self.cache_text.setStyleSheet("""
            QTextEdit {
                background: #0b0e14; color: #26a69a;
                border: 1px solid #2a2e3b;
                font-family: 'Consolas', monospace; font-size: 13px;
            }
        """)
        layout.addWidget(self.cache_text)
        
        # 초기 상태 로드
        self._refresh_cache_status()
        
        return widget
    
    def _select_all(self):
        for i in range(self.symbol_list.count()):
            self.symbol_list.item(i).setCheckState(Qt.Checked)
    
    def _select_none(self):
        for i in range(self.symbol_list.count()):
            self.symbol_list.item(i).setCheckState(Qt.Unchecked)
    
    def _select_top10(self):
        """거래량 기준 Top 10 선택"""
        exchange = self.exchange_combo.currentText().lower()
        
        # Top 10 버튼 찾기 (sender 사용)
        sender = self.sender()
        if sender:
            sender.setEnabled(False)
            original_text = sender.text()
            sender.setText("⏳ 조회중...")
        
        try:
            self.log_text.append(f"🔍 {exchange} 거래량 Top 10 조회 중...")
            
            top10 = self._get_top10_by_volume(exchange)
            
            if not top10:
                raise Exception("거래량 데이터 없음")
            
            self.log_text.append(f"📊 거래량 Top 10: {', '.join(top10[:5])}...")
            
            # 체크박스 전체 해제 후 Top 10만 선택
            for i in range(self.symbol_list.count()):
                item = self.symbol_list.item(i)
                symbol = item.text()
                item.setCheckState(Qt.Checked if symbol in top10 else Qt.Unchecked)
            
            self.status_label.setText(f"✅ 거래량 Top 10 선택됨")
            self.log_text.append(f"✅ Top 10 선택 완료!")
            
        except Exception as e:
            self.log_text.append(f"❌ Top 10 조회 실패: {e}")
            # 폴백: 기본 상위 10개
            self._select_none()
            for i in range(min(10, self.symbol_list.count())):
                self.symbol_list.item(i).setCheckState(Qt.Checked)
            self.status_label.setText("⚠️ 기본 Top 10 선택됨 (API 오류)")
        
        finally:
            if sender:
                sender.setEnabled(True)
                sender.setText(original_text if 'original_text' in dir() else "Top 10")
    
    def _get_top10_by_volume(self, exchange: str) -> list:
        """거래소별 24시간 거래량 Top 10 조회"""
        if exchange == "bybit":
            return self._get_bybit_top10()
        elif exchange == "binance":
            return self._get_binance_top10()
        elif exchange == "okx":
            return self._get_okx_top10()
        elif exchange == "bitget":
            return self._get_bitget_top10()
        else:
            # 기타 거래소는 기본 POPULAR_SYMBOLS 사용
            return self.POPULAR_SYMBOLS[:10]
    
    def _get_bybit_top10(self) -> list:
        """Bybit 거래량 Top 10"""
        import requests
        
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "linear"}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("retCode") != 0:
            raise Exception(data.get("retMsg", "Bybit API Error"))
        
        # USDT 페어만 필터 + 거래량 정렬
        tickers = data.get("result", {}).get("list", [])
        usdt_pairs = [t for t in tickers if t.get("symbol", "").endswith("USDT")]
        
        # 24시간 거래대금(turnover24h) 기준 정렬
        sorted_pairs = sorted(
            usdt_pairs,
            key=lambda x: float(x.get("turnover24h", 0)),
            reverse=True
        )
        
        return [t["symbol"] for t in sorted_pairs[:10]]
    
    def _get_binance_top10(self) -> list:
        """Binance 선물 거래량 Top 10"""
        import requests
        
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # USDT 페어만 필터
        usdt_pairs = [t for t in data if t.get("symbol", "").endswith("USDT")]
        
        # 24시간 거래대금(quoteVolume) 기준 정렬
        sorted_pairs = sorted(
            usdt_pairs,
            key=lambda x: float(x.get("quoteVolume", 0)),
            reverse=True
        )
        
        return [t["symbol"] for t in sorted_pairs[:10]]
    
    def _get_okx_top10(self) -> list:
        """OKX 거래량 Top 10"""
        import requests
        
        url = "https://www.okx.com/api/v5/market/tickers"
        params = {"instType": "SWAP"}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("code") != "0":
            raise Exception(data.get("msg", "OKX API Error"))
        
        tickers = data.get("data", [])
        usdt_pairs = [t for t in tickers if "USDT" in t.get("instId", "")]
        
        # 24시간 거래량 기준 정렬
        sorted_pairs = sorted(
            usdt_pairs,
            key=lambda x: float(x.get("volCcy24h", 0)),
            reverse=True
        )
        
        # OKX 형식: BTC-USDT-SWAP → BTCUSDT
        return [t["instId"].split("-")[0] + "USDT" for t in sorted_pairs[:10]]
    
    def _get_bitget_top10(self) -> list:
        """Bitget 거래량 Top 10"""
        import requests
        
        url = "https://api.bitget.com/api/v2/mix/market/tickers"
        params = {"productType": "USDT-FUTURES"}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("code") != "00000":
            raise Exception(data.get("msg", "Bitget API Error"))
        
        tickers = data.get("data", [])
        
        # 24시간 거래량 기준 정렬
        sorted_pairs = sorted(
            tickers,
            key=lambda x: float(x.get("quoteVolume", 0)),
            reverse=True
        )
        
        # Bitget 형식: BTCUSDT_UMCBL → BTCUSDT
        return [t["symbol"].replace("_UMCBL", "").replace("USDT", "") + "USDT" for t in sorted_pairs[:10]]
    
    def _select_top_n(self, n: int):
        """거래량 기준 Top N 선택"""
        exchange = self.exchange_combo.currentText().lower()
        
        try:
            self.log_text.append(f"🔍 {exchange} 거래량 Top {n} 조회 중...")
            
            # 거래량 상위 전체 가져오기
            top_symbols = self._get_top_by_volume(exchange, n)
            
            if not top_symbols:
                raise Exception("거래량 데이터 없음")
            
            self.log_text.append(f"📊 거래량 Top {n}: {len(top_symbols)}개")
            
            # 체크박스 설정
            for i in range(self.symbol_list.count()):
                item = self.symbol_list.item(i)
                symbol = item.text()
                item.setCheckState(Qt.Checked if symbol in top_symbols else Qt.Unchecked)
            
            self.status_label.setText(f"✅ 거래량 Top {n} 선택됨")
            self.log_text.append(f"✅ Top {n} 선택 완료!")
            
        except Exception as e:
            self.log_text.append(f"❌ Top {n} 조회 실패: {e}")
            self.status_label.setText(f"⚠️ Top {n} 조회 실패")
    
    def _get_top_by_volume(self, exchange: str, n: int = 100) -> list:
        """거래량 상위 N개 조회"""
        import requests
        
        try:
            if exchange == 'bybit':
                url = "https://api.bybit.com/v5/market/tickers?category=linear"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                tickers = data.get("result", {}).get("list", [])
                sorted_pairs = sorted(tickers, key=lambda x: float(x.get("turnover24h", 0)), reverse=True)
                return [t["symbol"] for t in sorted_pairs[:n] if t["symbol"].endswith("USDT")]
                
            elif exchange == 'binance':
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                sorted_pairs = sorted(data, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
                return [t["symbol"] for t in sorted_pairs[:n] if t["symbol"].endswith("USDT")]
                
            elif exchange == 'okx':
                url = "https://www.okx.com/api/v5/market/tickers?instType=SWAP"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                tickers = data.get("data", [])
                sorted_pairs = sorted(tickers, key=lambda x: float(x.get("volCcy24h", 0)), reverse=True)
                return [t["instId"].replace("-USDT-SWAP", "USDT") for t in sorted_pairs[:n] if "USDT" in t["instId"]]
                
            elif exchange == 'bitget':
                url = "https://api.bitget.com/api/mix/v1/market/tickers?productType=umcbl"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                tickers = data.get("data", [])
                sorted_pairs = sorted(tickers, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
                return [t["symbol"].replace("_UMCBL", "") for t in sorted_pairs[:n]]
        except Exception:
            pass
        return []
    
    def _select_new_listings(self):
        """신규 상장 코인 선택"""
        self.log_text.append("🆕 신규 상장 코인 조회 중...")
        
        # 최근 상장된 코인 (예시: 리스트 끝부분)
        try:
            # 전체 리스트의 마지막 20개를 신규로 간주
            total = self.symbol_list.count()
            new_count = min(20, total)
            
            self._select_none()
            for i in range(total - new_count, total):
                self.symbol_list.item(i).setCheckState(Qt.Checked)
            
            self.status_label.setText(f"✅ 신규 상장 {new_count}개 선택됨")
            self.log_text.append(f"✅ 신규 상장 코인 선택 완료!")
        except Exception as e:
            self.log_text.append(f"❌ 신규 상장 조회 실패: {e}")
    
    def _select_top_gainers(self):
        """24시간 상승률 상위 코인 선택"""
        exchange = self.exchange_combo.currentText().lower()
        
        try:
            self.log_text.append(f"📈 {exchange} 급등 코인 조회 중...")
            
            gainers = self._get_price_change_top(exchange, ascending=False)
            
            if gainers:
                for i in range(self.symbol_list.count()):
                    item = self.symbol_list.item(i)
                    item.setCheckState(Qt.Checked if item.text() in gainers else Qt.Unchecked)
                
                self.status_label.setText(f"✅ 급등 코인 {len(gainers)}개 선택됨")
                self.log_text.append(f"✅ 급등 코인: {', '.join(gainers[:5])}...")
            else:
                self.log_text.append("⚠️ 급등 코인 데이터 없음")
        except Exception as e:
            self.log_text.append(f"❌ 급등 코인 조회 실패: {e}")
    
    def _select_top_losers(self):
        """24시간 하락률 상위 코인 선택"""
        exchange = self.exchange_combo.currentText().lower()
        
        try:
            self.log_text.append(f"📉 {exchange} 급락 코인 조회 중...")
            
            losers = self._get_price_change_top(exchange, ascending=True)
            
            if losers:
                for i in range(self.symbol_list.count()):
                    item = self.symbol_list.item(i)
                    item.setCheckState(Qt.Checked if item.text() in losers else Qt.Unchecked)
                
                self.status_label.setText(f"✅ 급락 코인 {len(losers)}개 선택됨")
                self.log_text.append(f"✅ 급락 코인: {', '.join(losers[:5])}...")
            else:
                self.log_text.append("⚠️ 급락 코인 데이터 없음")
        except Exception as e:
            self.log_text.append(f"❌ 급락 코인 조회 실패: {e}")
    
    def _get_price_change_top(self, exchange: str, ascending: bool = False, n: int = 20) -> list:
        """가격 변동률 상위/하위 코인 조회"""
        import requests
        
        try:
            if exchange == 'bybit':
                url = "https://api.bybit.com/v5/market/tickers?category=linear"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                tickers = data.get("result", {}).get("list", [])
                sorted_pairs = sorted(
                    tickers, 
                    key=lambda x: float(x.get("price24hPcnt", 0)), 
                    reverse=not ascending
                )
                return [t["symbol"] for t in sorted_pairs[:n] if t["symbol"].endswith("USDT")]
                
            elif exchange == 'binance':
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                sorted_pairs = sorted(
                    data, 
                    key=lambda x: float(x.get("priceChangePercent", 0)), 
                    reverse=not ascending
                )
                return [t["symbol"] for t in sorted_pairs[:n] if t["symbol"].endswith("USDT")]
        except Exception:
            pass
        return []
    
    def _load_symbols(self):
        """심볼 리스트 로드 (CCXT API에서 직접)"""
        try:
            import ccxt
            
            exchange_name = self.exchange_combo.currentText().lower()
            market_text = self.market_type_combo.currentText()
            market_type = 'swap' if '선물' in market_text else 'spot'
            
            self.log_text.append(f"🔄 {exchange_name} 심볼 로드 중...")
            
            # [FIX] 빗썸/업비트는 KRW 거래소
            is_krw_exchange = exchange_name in ['bithumb', 'upbit']
            
            # 거래소 인스턴스
            exchange = getattr(ccxt, exchange_name)()
            exchange.load_markets()
            
            # 전체 심볼 필터링
            symbols = []
            for symbol, market in exchange.markets.items():
                if market_type == 'swap' and market.get('swap'):
                    if 'USDT' in symbol:
                        # 형식 통일: BTCUSDT
                        clean = symbol.replace('/', '').replace(':USDT', '')
                        symbols.append(clean)
                elif market_type == 'spot' and market.get('spot'):
                    # [FIX] KRW 거래소 지원
                    if is_krw_exchange:
                        # KRW 페어만 (BTC/KRW, KRW-BTC 등)
                        if 'KRW' in symbol:
                            # 형식 통일: KRW-BTC (업비트 스타일)
                            if '/' in symbol:
                                base = symbol.split('/')[0]
                                clean = f"KRW-{base}"
                            else:
                                clean = symbol
                            symbols.append(clean)
                    else:
                        # USDT 페어 (기존 로직)
                        if 'USDT' in symbol:
                            clean = symbol.replace('/', '')
                            symbols.append(clean)
            
            symbols = sorted(set(symbols))
            
            self.symbol_list.clear()
            for sym in symbols:
                item = QListWidgetItem(sym)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.symbol_list.addItem(item)
            
            quote = "KRW" if is_krw_exchange else "USDT"
            self.log_text.append(f"✅ {exchange_name} {market_type} ({quote}): {len(symbols)}개 심볼")
            
        except Exception as e:
            self.log_text.append(f"❌ 심볼 로드 실패: {e}")
            # 실패시 기본 목록
            self.symbol_list.clear()
            for sym in self.POPULAR_SYMBOLS:
                item = QListWidgetItem(sym)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.symbol_list.addItem(item)
    
    def _refresh_symbols(self):
        """거래소에서 최신 심볼 가져와서 캐시 업데이트"""
        self.log_text.append("🔄 심볼 새로고침 중...")
        
        try:
            from symbol_cache import SymbolCache
            import asyncio
            import sys
            
            # Windows asyncio 호환
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
            exchange = self.exchange_combo.currentText().lower()
            cache = SymbolCache()
            
            # 동기적으로 업데이트 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(cache.update_exchange_async(exchange))
            loop.close()
            
            self._load_symbols()
            self.log_text.append("✅ 심볼 새로고침 완료!")
            
        except Exception as e:
            self.log_text.append(f"❌ 새로고침 실패: {e}")
    
    def _add_custom(self):
        symbol = self.custom_symbol.currentText().strip().upper()
        if symbol and symbol not in self.POPULAR_SYMBOLS:
            item = QListWidgetItem(symbol)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.symbol_list.addItem(item)
            self.log_text.append(f"[Added] {symbol}")
            
    def _get_listing_date(self, symbol, exchange_name):
        """거래소 API에서 심볼 상장일 조회"""
        try:
            import ccxt
            import time
            exchange_class = getattr(ccxt, exchange_name.lower())
            ex = exchange_class()
            
            # 가장 오래된 데이터 조회 (1일봉 기준)
            # 바이낸스/바이비트는 시간순 정렬 보장
            if exchange_name.lower() in ['bybit', 'binance']:
                 # 2017년부터 조회 시도
                since = int(datetime(2017, 1, 1).timestamp() * 1000)
                ohlcv = ex.fetch_ohlcv(symbol, '1d', since=since, limit=1)
                if ohlcv:
                    return datetime.fromtimestamp(ohlcv[0][0] / 1000)
            
            # 기타 거래소거나 조회 실패 시
            return datetime(2017, 1, 1)
        except Exception as e:
            print(f"Listing date fetch failed: {e}")
            return datetime(2017, 1, 1)  # 폴백
    
    def _get_selected_symbols(self):
        symbols = []
        for i in range(self.symbol_list.count()):
            item = self.symbol_list.item(i)
            if item.checkState() == Qt.Checked:
                symbols.append(item.text())
        return symbols
    
    def _toggle_date_edit(self, checked):
        """상장일부터 체크 시 시작일 입력 비활성화"""
        self.start_date.setEnabled(not checked)
        if checked:
            self.start_date.setStyleSheet("background: #444; color: #888;")
        else:
            self.start_date.setStyleSheet("")
    
    def _start_download(self):
        symbols = self._get_selected_symbols()
        
        if not symbols:
            QMessageBox.warning(self, t("common.warning"), "Please select at least one symbol!")
            return
        
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_text.clear()
        self.log_text.append(f"[Start] Downloading {len(symbols)} symbols...")
        self.log_text.append(f"[Info] Exchange: {self.exchange_combo.currentText()}")
        self.log_text.append(f"[Info] Timeframe: 15m (fixed)")
        
        
        # 시작 날짜 처리
        if self.since_listing_chk.isChecked():
            self.log_text.append("📅 Fetching listing date...")
            start_date_obj = self._get_listing_date(symbols[0], self.exchange_combo.currentText())
            start_date_str = start_date_obj.strftime("%Y-%m-%d")
            self.log_text.append(f"📅 Start Date set to: {start_date_str} (Listed)")
        else:
            start_date_str = self.start_date.date().toString("yyyy-MM-dd")
            
        # 스레드 시작
        self._download_thread = DownloadThread(
            symbols=symbols,
            exchange=self.exchange_combo.currentText(),
            timeframe='15m',  # 15분봉 고정 (리샘플링으로 1h/4h 생성)
            start_date=start_date_str,
            end_date=self.end_date.date().toString("yyyy-MM-dd")
        )
        self._download_thread.progress.connect(self._on_progress)
        self._download_thread.finished.connect(self._on_symbol_finished)
        self._download_thread.error.connect(self._on_error)
        self._download_thread.start()
    
    def _stop_download(self):
        if self._download_thread:
            self._download_thread.stop()
            self._download_thread.wait(3000)  # 3초 대기
            self._download_thread = None
        
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_text.append("[Stopped] Download cancelled by user")
    
    def _on_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
        
        # 로그에도 진행률 추가 (10% 단위)
        if percent % 10 == 0 or '캔들' in message:
            self.log_text.append(f"📊 {message}")
        
        if percent == 100:
            self.download_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.log_text.append("\n✅ [Complete] All downloads finished!")
            self._refresh_cache_status()
    
    def _on_symbol_finished(self, symbol, count):
        self.log_text.append(f"✅ {symbol}: {count:,} candles 완료")
        self.download_finished.emit(symbol, count)
        # 스크롤 아래로
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def _on_error(self, symbol, error):
        self.log_text.append(f"❌ {symbol}: {error}")
    
    def _refresh_cache_status(self):
        """캐시 상태 새로고침"""
        try:
            from data_manager import DataManager
            dm = DataManager()
            
            cache_dir = dm.cache_dir
            
            text = f"📁 Cache Directory: {cache_dir}\n"
            text += "=" * 60 + "\n\n"
            
            if cache_dir.exists():
                files = list(cache_dir.glob("*.parquet"))
                
                if files:
                    text += f"Found {len(files)} cached datasets:\n\n"
                    
                    for f in sorted(files):
                        size_mb = f.stat().st_size / (1024 * 1024)
                        name = f.stem
                        
                        # 캔들 수 확인
                        # 캔들 수 확인 (Parquet)
                        try:
                            import pandas as pd
                            # 메타데이터만 읽으면 더 좋겠지만 pyarrow 필요
                            # 간단히 전체 읽되 컬럼 하나만
                            df = pd.read_parquet(f, columns=['timestamp'])
                            count = len(df)
                            text += f"  📊 {name}: {count:,} candles ({size_mb:.2f} MB)\n"
                        except Exception:
                            text += f"  📊 {name}: {size_mb:.2f} MB\n"
                else:
                    text += "No cached data found.\n"
                    text += "\nGo to 'Download' tab to collect data!"
            else:
                text += "Cache directory does not exist yet.\n"
                text += "Download some data to create it!"
            
            self.cache_text.setText(text)
            
        except Exception as e:
            self.cache_text.setText(f"Error loading cache status: {e}")

    def _filter_symbols(self, text: str):
        """심볼 리스트 필터링"""
        text = text.upper().strip()
        for i in range(self.symbol_list.count()):
            item = self.symbol_list.item(i)
            if text == "" or text in item.text():
                item.setHidden(False)
            else:
                item.setHidden(True)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = DataCollectorWidget()
    w.resize(700, 700)
    w.show()
    sys.exit(app.exec_())
