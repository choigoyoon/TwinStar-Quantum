# data_download_widget.py

from locales.lang_manager import t
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDateEdit, QCheckBox, QProgressBar, QGroupBox, QTextEdit,
    QMessageBox
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from datetime import datetime

from exchange_selector_widget import ExchangeSelectorWidget
from data_manager import DataManager


class DownloadWorker(QThread):
    """백그라운드 다운로드 워커"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(int)
    
    def __init__(self, data_manager, exchange, symbol, timeframes, start_date, end_date):
        super().__init__()
        self.dm = data_manager
        self.exchange = exchange
        self.symbol = symbol
        self.timeframes = timeframes
        self.start_date = start_date
        self.end_date = end_date
        self.is_running = True
        
    def run(self):
        total_count = 0
        
        for i, tf in enumerate(self.timeframes):
            if not self.is_running:
                break
                
            self.progress.emit(0, f"Downloading {tf}...")
            
            def on_progress(p, msg):
                # 전체 진행률 계산 (단순화)
                base_p = (i / len(self.timeframes)) * 100
                current_p = (p / len(self.timeframes))
                total_p = int(base_p + current_p)
                self.progress.emit(total_p, f"[{tf}] {msg}")
            
            count = self.dm.download_ohlcv(
                self.exchange, self.symbol, tf,
                self.start_date, self.end_date,
                progress_callback=on_progress
            )
            total_count += count
            
        self.progress.emit(100, "Complete!")
        self.finished.emit(total_count)
        
    def stop(self):
        self.is_running = False


class DataDownloadWidget(QWidget):
    """데이터 다운로드 위젯"""
    
    def __init__(self):
        super().__init__()
        self.dm = DataManager()
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 1. 거래소/심볼 선택
        group_sel = QGroupBox("Target Symbol")
        sel_layout = QVBoxLayout(group_sel)
        self.selector = ExchangeSelectorWidget()
        sel_layout.addWidget(self.selector)
        layout.addWidget(group_sel)
        
        # 2. 기간 및 타임프레임
        group_opt = QGroupBox("Options")
        opt_layout = QVBoxLayout(group_opt)
        
        # 기간
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Period:"))
        
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-6)) # 기본 6개월
        
        # 상장일 찾기 버튼
        btn_listing = QPushButton("📅 상장일")
        btn_listing.setToolTip("거래소 상장일(첫 데이터) 자동 검색")
        btn_listing.clicked.connect(self.find_listing_date)
        btn_listing.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #3d3d3d; }
        """)
        
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        
        date_layout.addWidget(self.date_start)
        date_layout.addWidget(btn_listing)
        date_layout.addWidget(QLabel("~"))
        date_layout.addWidget(self.date_end)
        opt_layout.addLayout(date_layout)
        
        # 타임프레임
        tf_layout = QHBoxLayout()
        tf_layout.addWidget(QLabel("Timeframes:"))
        
        self.chk_tfs = {}
        tfs = ['1m', '5m', '15m', '1h', '4h', '1d']
        for tf in tfs:
            chk = QCheckBox(tf)
            if tf in ['15m', '1h', '4h']:
                chk.setChecked(True)
            self.chk_tfs[tf] = chk
            tf_layout.addWidget(chk)
            
        opt_layout.addLayout(tf_layout)
        layout.addWidget(group_opt)
        
        # 3. 진행상황 및 제어
        group_prog = QGroupBox("Progress")
        prog_layout = QVBoxLayout(group_prog)
        
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setTextVisible(True)
        self.pbar.setFormat("%p% - Ready")
        prog_layout.addWidget(self.pbar)
        
        self.lbl_status = QLabel("다운로드 준비됨")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prog_layout.addWidget(self.lbl_status)
        
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("📥 다운로드 시작")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.clicked.connect(self.start_download)
        self.btn_start.setStyleSheet("background-color: #238636; color: white; font-weight: bold;")
        
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.clicked.connect(self.stop_download)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #da3633; color: white; font-weight: bold;")
        
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        prog_layout.addLayout(btn_layout)
        
        layout.addWidget(group_prog)
        
        # 4. 로그
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        layout.addWidget(self.log_text)
        
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")
        
    def find_listing_date(self):
        """상장일(첫 데이터) 찾기"""
        exchange_id = self.selector.current_exchange
        symbol = self.selector.current_symbol
        
        self.log(f"🔍 Finding listing date for {symbol} on {exchange_id}...")
        self.btn_start.setEnabled(False)
        
        try:
            import ccxt
            
            # 거래소 인스턴스 생성
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({'enableRateLimit': True})
            
            # 1. since=0 (Epoch)으로 시도
            # 바이낸스 등 대부분은 가장 오래된 데이터를 반환함
            ohlcv = exchange.fetch_ohlcv(symbol, '1d', since=0, limit=1)
            
            if not ohlcv:
                # 2. 2010년 1월 1일로 시도 (비트코인 초기)
                since_ts = int(datetime(2010, 1, 1).timestamp() * 1000)
                ohlcv = exchange.fetch_ohlcv(symbol, '1d', since=since_ts, limit=1)
            
            if ohlcv and len(ohlcv) > 0:
                first_ts = ohlcv[0][0]
                first_date = datetime.fromtimestamp(first_ts / 1000)
                
                # UI 업데이트
                self.date_start.setDate(QDate(first_date.year, first_date.month, first_date.day))
                
                msg = f"✅ Found listing date: {first_date.strftime('%Y-%m-%d')}"
                self.log(msg)
                QMessageBox.information(self, "Found", f"Listing Date: {first_date.strftime('%Y-%m-%d')}")
            else:
                self.log("❌ Could not find listing date (No data returned).")
                QMessageBox.warning(self, t("common.error"), "Could not find listing date.\nTry downloading manually.")
                
        except Exception as e:
            self.log(f"❌ Error finding listing date: {e}")
            QMessageBox.warning(self, t("common.error"), f"Error finding listing date:\n{e}")
            
        finally:
            self.btn_start.setEnabled(True)

    def start_download(self):
        # 파라미터 수집
        exchange = self.selector.current_exchange
        symbol = self.selector.current_symbol
        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_end.date().toString("yyyy-MM-dd")
        
        selected_tfs = [tf for tf, chk in self.chk_tfs.items() if chk.isChecked()]
        
        if not selected_tfs:
            QMessageBox.warning(self, t("common.warning"), "Please select at least one timeframe.")
            return
            
        # UI 업데이트
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.pbar.setValue(0)
        self.log(f"Starting download for {symbol} ({len(selected_tfs)} TFs)")
        
        # 워커 시작
        self.worker = DownloadWorker(self.dm, exchange, symbol, selected_tfs, start_date, end_date)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    def stop_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("Stopping download...")
            self.btn_stop.setEnabled(False)
            
    def on_progress(self, value, msg):
        self.pbar.setValue(value)
        self.pbar.setFormat(f"%p% - {msg}")
        self.lbl_status.setText(msg)
        
    def on_finished(self, count):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.pbar.setValue(100)
        self.pbar.setFormat("100% - Complete")
        self.lbl_status.setText(f"Download Complete! ({count} candles)")
        self.log(f"Download finished. Total {count} candles saved.")


# 테스트
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = DataDownloadWidget()
    window.setWindowTitle("데이터 다운로드 관리")
    window.resize(500, 600)
    window.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
    window.show()
    
    sys.exit(app.exec())
