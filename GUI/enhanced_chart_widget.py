"""
enhanced_chart_widget.py 수정사항
- NowcastWidget 통합
- CandleAggregator 연결
- WebSocket 실시간 데이터 흐름
"""

import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QComboBox, QGroupBox)
from PyQt6.QtCore import Qt

# Logging
import logging
logger = logging.getLogger(__name__)

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# ===== 상단 import 추가 =====
try:
    from candle_aggregator import CandleAggregator, Candle
except ImportError:
    from GUI.candle_aggregator import CandleAggregator, Candle

# websocket_manager가 있으면
try:
    from websocket_manager import WebSocketManager
    HAS_WEBSOCKET = True
except ImportError:
    try:
        from GUI.websocket_manager import WebSocketManager
        HAS_WEBSOCKET = True
    except ImportError:
        HAS_WEBSOCKET = False
        logger.info("[Warning] websocket_manager not found")


class EnhancedChartWidget(QWidget):
    """차트 위젯 - 나우캐스트 통합"""
    
    def __init__(self, data_manager=None, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        
        # 나우캐스트 관련
        self.aggregator = CandleAggregator()
        self.ws_manager = None
        self._ws_connected = False
        
        self.init_ui()
        self._setup_nowcast()
    
    def init_ui(self):
        """UI 초기화 - 간소화된 차트 뷰"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ===== 1. 상단 컨트롤 (심볼만) =====
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("심볼:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"])
        self.symbol_combo.setMinimumWidth(120)
        self.symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        control_layout.addWidget(self.symbol_combo)
        
        control_layout.addWidget(QLabel("거래소:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["bybit", "binance"])
        self.exchange_combo.setMinimumWidth(100)
        control_layout.addWidget(self.exchange_combo)
        
        # 연결 버튼
        self.connect_btn = QPushButton("🔗 실시간 연결")
        self.connect_btn.clicked.connect(self._toggle_websocket)
        self.connect_btn.setStyleSheet("""
            QPushButton { background: #2962FF; color: white; padding: 8px 15px; border-radius: 4px; }
            QPushButton:hover { background: #1e88e5; }
        """)
        control_layout.addWidget(self.connect_btn)
        
        control_layout.addStretch()
        
        # 현재가 표시
        self.price_label = QLabel("현재가: -")
        self.price_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #26a69a;")
        control_layout.addWidget(self.price_label)
        
        main_layout.addLayout(control_layout)
        
        # ===== 2. 차트 영역 =====
        self.chart_group = QGroupBox("📊 실시간 차트")
        self.chart_group.setMinimumHeight(500)
        self.chart_group.setStyleSheet("""
            QGroupBox { color: white; font-weight: bold; border: 1px solid #333; border-radius: 5px; padding: 10px; }
        """)
        chart_layout = QVBoxLayout(self.chart_group)
        
        # pyqtgraph 차트
        try:
            import pyqtgraph as pg
            self.chart_view = pg.PlotWidget()
            self.chart_view.setBackground('#0d1117')
            self.chart_view.showGrid(x=True, y=True, alpha=0.3)
            self.chart_view.setLabel('left', 'Price', color='#8b949e')
            self.chart_view.setLabel('bottom', 'Time', color='#8b949e')
            chart_layout.addWidget(self.chart_view)
            self._has_chart = True
        except ImportError:
            self.chart_view = QLabel("pyqtgraph 설치 필요")
            self.chart_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chart_view.setStyleSheet("color: #8b949e; font-size: 14px;")
            chart_layout.addWidget(self.chart_view)
            self._has_chart = False
        
        main_layout.addWidget(self.chart_group, 1)  # stretch=1
        
        # ===== 3. 상태 바 =====
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("⏸ 대기 중")
        self.status_label.setStyleSheet("color: #888;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.candle_count_label = QLabel("")
        self.candle_count_label.setStyleSheet("color: #8b949e;")
        status_layout.addWidget(self.candle_count_label)
        
        main_layout.addLayout(status_layout)
    
    def _setup_nowcast(self):
        """Aggregator 콜백 연결"""
        self.aggregator.on_candle_update = self._on_aggregator_update
        self.aggregator.on_candle_closed = self._on_aggregator_closed
    
    def _on_symbol_changed(self, symbol: str):
        """심볼 변경 시"""
        if self._ws_connected:
            self._stop_websocket()
            self._start_websocket()
    
    def _toggle_websocket(self):
        """WebSocket 연결 토글"""
        if self._ws_connected:
            self._stop_websocket()
            self.connect_btn.setText("🔗 실시간 연결")
        else:
            self._start_websocket()
            self.connect_btn.setText("🔌 연결 해제")
    
    def _start_websocket(self):
        """WebSocket 연결 시작"""
        if not HAS_WEBSOCKET:
            self.status_label.setText("❌ WebSocket 미지원")
            return
        
        try:
            exchange = self.exchange_combo.currentText()
            symbol = self.symbol_combo.currentText()
            
            self.status_label.setText("🔄 연결 중...")
            
            if self.ws_manager is None:
                self.ws_manager = WebSocketManager()
            
            # 콜백 설정
            self.ws_manager.on_candle = self._on_ws_candle_data
            self.ws_manager.on_status = self._on_ws_status
            
            # 1분봉 구독
            self.ws_manager.start(exchange, [symbol], "1m")
            
            # 데이터 큐 처리 타이머 (100ms마다)
            if not hasattr(self, '_ws_timer'):
                from PyQt6.QtCore import QTimer
                self._ws_timer = QTimer()
                self._ws_timer.timeout.connect(self._process_ws_queue)
            self._ws_timer.start(100)
            
            self._ws_connected = True
            self.status_label.setText(f"✅ {symbol} 실시간 연결됨")
            logger.info(f"[Chart] WebSocket 시작: {exchange} {symbol}")
            
        except Exception as e:
            logger.info(f"[Error] WebSocket 시작 실패: {e}")
            self.status_label.setText(f"❌ 연결 실패")
    
    def _process_ws_queue(self):
        """WebSocket 데이터 큐 처리"""
        if self.ws_manager:
            self.ws_manager._process_queue()
    
    def _on_ws_status(self, status):
        """WebSocket 상태 변경"""
        from GUI.websocket_manager import ConnectionStatus
        if status == ConnectionStatus.CONNECTED:
            self.status_label.setText("✅ 연결됨")
        elif status == ConnectionStatus.DISCONNECTED:
            self.status_label.setText("⚠️ 연결 끊김")
        elif status == ConnectionStatus.ERROR:
            self.status_label.setText("❌ 오류")
    
    def _stop_websocket(self):
        """WebSocket 연결 종료"""
        if hasattr(self, '_ws_timer'):
            self._ws_timer.stop()
        
        if self.ws_manager:
            self.ws_manager.stop()
        
        self._ws_connected = False
        self.status_label.setText("⏸ 대기 중")
        logger.info("[Chart] WebSocket 종료")
    
    def _on_ws_candle_data(self, realtime_candle):
        """WebSocket 데이터 수신 → Aggregator 전달"""
        # realtime_candle는 RealtimeCandle 객체
        try:
            candle = Candle(
                timestamp=realtime_candle.timestamp,
                open=float(realtime_candle.open),
                high=float(realtime_candle.high),
                low=float(realtime_candle.low),
                close=float(realtime_candle.close),
                volume=float(realtime_candle.volume),
                is_closed=realtime_candle.is_closed
            )
            
            # Aggregator로 전달
            self.aggregator.process_candle(candle)
            
            # 현재가 업데이트
            self.price_label.setText(f"현재가: ${candle.close:,.2f}")
            
        except Exception as e:
            logger.info(f"[Error] 캔들 처리: {e}")
    
    def _on_aggregator_update(self, tf: str, candle: Candle, is_closed: bool):
        """Aggregator 캔들 업데이트 → 차트 반영"""
        base_tf = self.nowcast_widget.get_base_timeframe()
        
        if tf == base_tf:
            # 기준 TF 캔들 → 차트 업데이트
            if is_closed:
                self._add_candle_to_chart(candle)
            else:
                self._update_last_candle(candle)
    
    def _on_aggregator_closed(self, tf: str, candle: Candle):
        """Aggregator 캔들 완성"""
        logger.info(f"[Aggregator] {tf} 캔들 완성: C:{candle.close:.2f}")
    
    # ===== 차트 업데이트 =====
    def _add_candle_to_chart(self, candle: Candle):
        """새 캔들 추가"""
        if not hasattr(self, '_chart_prices'):
            self._chart_prices = []
        
        self._chart_prices.append(candle.close)
        
        # 최대 500개 유지
        if len(self._chart_prices) > 500:
            self._chart_prices = self._chart_prices[-500:]
        
        self._redraw_chart()
        logger.info(f"[Chart] 새 캔들: ${candle.close:,.2f}")
    
    def _update_last_candle(self, candle: Candle):
        """마지막 캔들 업데이트 (실시간)"""
        if not hasattr(self, '_chart_prices') or len(self._chart_prices) == 0:
            self._chart_prices = [candle.close]
        else:
            self._chart_prices[-1] = candle.close
        
        self._redraw_chart()
        self.price_label.setText(f"현재가: ${candle.close:,.2f}")
    
    def _redraw_chart(self):
        """차트 다시 그리기"""
        if not hasattr(self, '_has_chart') or not self._has_chart:
            return
        if not hasattr(self, '_chart_prices') or len(self._chart_prices) == 0:
            return
        
        try:
            import pyqtgraph as pg
            
            self.chart_view.clear()
            
            prices = self._chart_prices
            x = list(range(len(prices)))
            
            # 상승/하락 색상
            if len(prices) > 1:
                color = '#26a69a' if prices[-1] >= prices[0] else '#ef5350'
            else:
                color = '#26a69a'
            
            pen = pg.mkPen(color=color, width=2)
            self.chart_view.plot(x, prices, pen=pen)
            
        except Exception as e:
            logger.info(f"[Chart] 리드로우 에러: {e}")
    
    def _reload_chart(self):
        """차트 새로고침 - Download 실행"""
        self._on_download()
    
    def _on_download(self):
        """데이터 다운로드 및 차트 표시"""
        exchange = self.exchange_combo.currentText()
        symbol = self.symbol_combo.currentText()
        tf = self.nowcast_widget.get_base_timeframe()
        
        logger.info(f"[Chart] 다운로드: {exchange} {symbol} {tf}")
        
        try:
            from data_manager import DataManager
            dm = DataManager()
            
            # 심볼 정규화
            clean_symbol = symbol.replace('/', '')
            
            df = dm.download(
                symbol=clean_symbol,
                timeframe=tf,
                exchange=exchange,
                limit=500
            )
            
            if df is not None and len(df) > 0:
                self.candle_count_label.setText(f"캔들: {len(df)}개")
                self._draw_chart(df)
                logger.info(f"[Chart] ✅ {len(df)}개 캔들 표시 완료")
            else:
                logger.info("[Chart] 데이터 없음")
                
        except Exception as e:
            logger.info(f"[Chart] 다운로드 에러: {e}")
    
    def _draw_chart(self, df):
        """차트 그리기"""
        if not hasattr(self, '_has_chart') or not self._has_chart:
            return
        
        try:
            import pyqtgraph as pg
            
            self.chart_view.clear()
            
            # 종가 라인 차트
            prices = df['close'].values
            x = list(range(len(prices)))
            
            # 색상: 상승 녹색, 하락 빨강
            if len(prices) > 1:
                color = '#26a69a' if prices[-1] >= prices[0] else '#ef5350'
            else:
                color = '#26a69a'
            
            pen = pg.mkPen(color=color, width=2)
            self.chart_view.plot(x, prices, pen=pen)
            
            # 현재가 업데이트
            if len(prices) > 0:
                self.price_label.setText(f"현재가: ${prices[-1]:,.2f}")
            
        except Exception as e:
            logger.info(f"[Chart] 차트 그리기 에러: {e}")
    
    # ===== 종료 처리 =====
    def closeEvent(self, event):
        """위젯 종료 시 정리"""
        self._stop_websocket()
        super().closeEvent(event)


# ===== 테스트 =====
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    try:
        from styles import StarUTheme
        style = StarUTheme.get_stylesheet()
    except ImportError:
        style = "QWidget { background-color: #0d1117; color: #f0f6fc; }"
    
    app = QApplication(sys.argv)
    app.setStyleSheet(style)
    
    # DataManager Mock
    class MockDataManager:
        def download_ohlcv(self, exchange, symbol, tf, limit=500):
            logger.info(f"Mock Download: {exchange} {symbol} {tf}")
            return [1] * limit # Fake data
            
    widget = EnhancedChartWidget(data_manager=MockDataManager())
    widget.setWindowTitle("Enhanced Chart + Nowcast 테스트")
    widget.setMinimumSize(800, 600)
    widget.show()
    
    sys.exit(app.exec())
