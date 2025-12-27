# E:/trading/gui/backtest_result_widget.py
"""
백테스트 결과 위젯
- 거래 내역 테이블
- CSV 내보내기
- 차트 마커 연동
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QGroupBox, QHeaderView, QFileDialog, QSplitter,
    QAbstractItemView
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor

import csv
from datetime import datetime
from typing import List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.common.strategy_interface import BacktestResult, TradeSignal, TradeStatus, Candle
from trade_chart_dialog import TradeChartDialog


class TradeTableWidget(QTableWidget):
    """거래 내역 테이블"""
    
    trade_clicked = pyqtSignal(int)  # candle_index
    
    def __init__(self):
        super().__init__()
        self._trades: List[TradeSignal] = []
        self._candles: List[Candle] = []  # 캔들 데이터 저장
        self._init_ui()
    
    def _init_ui(self):
        # 컬럼 설정
        columns = ["#", "시간", "방향", "진입가", "손절가", "익절가", "청산가", "결과", "수익%"]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        # 스타일
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                gridline-color: #333333;
                border: none;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
            QTableWidget::item:selected {
                background-color: #2d5016;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # 설정
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        
        # 컬럼 너비
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 50)
        
        # 클릭 이벤트
        self.cellClicked.connect(self._on_cell_clicked)
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)  # 더블클릭 추가
    
    def set_trades(self, trades: List[TradeSignal]):
        """거래 내역 설정"""
        self._trades = trades
        self.setRowCount(len(trades))
        
        for row, trade in enumerate(trades):
            # 번호
            self.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            # 시간
            time_str = datetime.fromtimestamp(trade.signal_time / 1000).strftime("%m-%d %H:%M")
            self.setItem(row, 1, QTableWidgetItem(time_str))
            
            # 방향
            direction = trade.signal_type.value.upper()
            dir_item = QTableWidgetItem(direction)
            dir_item.setForeground(QColor("#4CAF50") if direction == "LONG" else QColor("#f44336"))
            self.setItem(row, 2, dir_item)
            
            # 가격들
            self.setItem(row, 3, QTableWidgetItem(f"{trade.entry_price:,.2f}"))
            self.setItem(row, 4, QTableWidgetItem(f"{trade.stop_loss:,.2f}"))
            self.setItem(row, 5, QTableWidgetItem(f"{trade.take_profit:,.2f}"))
            self.setItem(row, 6, QTableWidgetItem(f"{trade.exit_price:,.2f}"))
            
            # 결과
            result_map = {
                TradeStatus.TP_HIT: ("TP ✅", "#4CAF50"),
                TradeStatus.SL_HIT: ("SL ❌", "#f44336"),
                TradeStatus.CLOSED: ("청산", "#888888")
            }
            result_text, result_color = result_map.get(trade.status, ("", "#ffffff"))
            result_item = QTableWidgetItem(result_text)
            result_item.setForeground(QColor(result_color))
            self.setItem(row, 7, result_item)
            
            # 수익률
            pnl_text = f"{trade.pnl_percent:+.2f}%"
            pnl_item = QTableWidgetItem(pnl_text)
            pnl_color = "#4CAF50" if trade.pnl_percent > 0 else "#f44336"
            pnl_item.setForeground(QColor(pnl_color))
            self.setItem(row, 8, pnl_item)
    
    def _on_cell_clicked(self, row, col):
        """셀 클릭 → 차트 이동"""
        if row < len(self._trades):
            self.trade_clicked.emit(self._trades[row].candle_index)
    
    def _on_cell_double_clicked(self, row, col):
        """셀 더블클릭 → 거래 차트 표시"""
        if row < len(self._trades) and self._candles:
            trade = self._trades[row]
            dialog = TradeChartDialog(trade, self._candles, self)
            dialog.exec_()
    
    def set_candles(self, candles: List[Candle]):
        """캔들 데이터 설정 (차트 표시용)"""
        self._candles = candles
    
    def get_trades(self) -> List[TradeSignal]:
        return self._trades


class BacktestResultWidget(QWidget):
    """백테스트 결과 전체 위젯"""
    
    go_to_candle = pyqtSignal(int)  # 차트 이동 시그널
    
    def __init__(self):
        super().__init__()
        self._result: BacktestResult = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 헤더
        header = QHBoxLayout()
        
        title = QLabel("📊 백테스트 결과")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        
        header.addStretch()
        
        # 스크린샷 저장 버튼
        screenshot_btn = QPushButton("📸 스크린샷")
        screenshot_btn.clicked.connect(self._save_screenshot)
        screenshot_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        header.addWidget(screenshot_btn)
        
        # CSV 내보내기 버튼
        self._export_btn = QPushButton("📥 CSV 내보내기")
        self._export_btn.clicked.connect(self._export_csv)
        self._export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        header.addWidget(self._export_btn)
        
        # 상세 매매 보기 버튼
        self._detail_btn = QPushButton("📊 상세 매매")
        self._detail_btn.clicked.connect(self._show_trade_details)
        self._detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        header.addWidget(self._detail_btn)
        
        layout.addLayout(header)
        
        # 통계 요약
        self._stats_group = QGroupBox("📈 통계 요약")
        self._stats_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 10px;
                padding: 15px;
            }
        """)
        stats_layout = QHBoxLayout(self._stats_group)
        
        self._stat_labels = {}
        stat_names = ["총 거래", "승률", "총 수익", "MDD", "PF", "샤프"]
        
        for name in stat_names:
            vbox = QVBoxLayout()
            label = QLabel(name)
            label.setStyleSheet("color: #888888; font-size: 11px;")
            label.setAlignment(Qt.AlignCenter)
            
            value = QLabel("-")
            value.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
            value.setAlignment(Qt.AlignCenter)
            
            vbox.addWidget(label)
            vbox.addWidget(value)
            stats_layout.addLayout(vbox)
            
            self._stat_labels[name] = value
        
        layout.addWidget(self._stats_group)
        
        # 에쿼티 커브 차트
        chart_group = QGroupBox("📈 에쿼티 커브")
        chart_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 10px;
                padding: 10px;
            }
        """)
        chart_layout = QVBoxLayout(chart_group)
        
        try:
            import pyqtgraph as pg
            pg.setConfigOptions(antialias=True)
            
            # 에쿼티 차트
            self._equity_chart = pg.PlotWidget()
            self._equity_chart.setBackground('#1e1e1e')
            self._equity_chart.setLabel('left', '수익률 (%)')
            self._equity_chart.setLabel('bottom', '거래 번호')
            self._equity_chart.showGrid(x=True, y=True, alpha=0.3)
            self._equity_chart.setMinimumHeight(200)
            chart_layout.addWidget(self._equity_chart)
            
            self._has_chart = True
        except ImportError:
            self._has_chart = False
            no_chart = QLabel("pyqtgraph 설치 필요: pip install pyqtgraph")
            no_chart.setStyleSheet("color: #888; padding: 20px;")
            chart_layout.addWidget(no_chart)
        
        layout.addWidget(chart_group)
        
        # 거래 내역 테이블
        trades_group = QGroupBox("📋 거래 내역")
        trades_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 10px;
                padding: 10px;
            }
        """)
        trades_layout = QVBoxLayout(trades_group)
        
        self._table = TradeTableWidget()
        self._table.trade_clicked.connect(self._on_trade_clicked)
        trades_layout.addWidget(self._table)
        
        layout.addWidget(trades_group, stretch=1)
    
    def set_result(self, result: BacktestResult, candles: List[Candle] = None):
        """결과 설정"""
        self._result = result
        
        # 통계 업데이트
        self._stat_labels["총 거래"].setText(f"{result.total_trades}건")
        self._stat_labels["승률"].setText(f"{result.win_rate}%")
        
        pnl_color = "#4CAF50" if result.total_pnl > 0 else "#f44336"
        self._stat_labels["총 수익"].setText(f"{result.total_pnl:+.1f}%")
        self._stat_labels["총 수익"].setStyleSheet(f"color: {pnl_color}; font-size: 16px; font-weight: bold;")
        
        self._stat_labels["MDD"].setText(f"{result.max_drawdown:.1f}%")
        self._stat_labels["MDD"].setStyleSheet("color: #f44336; font-size: 16px; font-weight: bold;")
        
        self._stat_labels["PF"].setText(f"{result.profit_factor:.2f}")
        self._stat_labels["샤프"].setText(f"{result.sharpe_ratio:.2f}")
        
        # 테이블 업데이트
        self._table.set_trades(result.trades)
        
        # 캔들 데이터 설정 (더블클릭 차트용)
        if candles:
            self._table.set_candles(candles)
        
        # 에쿼티 커브 그리기
        self._draw_equity_curve(result.trades)
    
    def _draw_equity_curve(self, trades):
        """에쿼티 커브 차트 그리기"""
        if not hasattr(self, '_has_chart') or not self._has_chart:
            return
        if not trades:
            return
        
        try:
            import pyqtgraph as pg
            
            self._equity_chart.clear()
            
            # 누적 수익률 계산
            equity = [0]
            for trade in trades:
                equity.append(equity[-1] + trade.pnl_percent)
            
            x = list(range(len(equity)))
            
            # 에쿼티 커브 (녹색)
            pen = pg.mkPen(color='#26a69a', width=2)
            self._equity_chart.plot(x, equity, pen=pen)
            
            # 0 기준선
            self._equity_chart.addLine(y=0, pen=pg.mkPen('#555', width=1, style=pg.QtCore.Qt.DashLine))
            
            # 드로우다운 영역 (빨간색 채우기)
            peak = 0
            dd_x, dd_y = [], []
            for i, eq in enumerate(equity):
                if eq > peak:
                    peak = eq
                dd = eq - peak
                if dd < 0:
                    dd_x.append(i)
                    dd_y.append(dd)
            
            if dd_x:
                fill = pg.FillBetweenItem(
                    pg.PlotCurveItem(dd_x, [0]*len(dd_x)),
                    pg.PlotCurveItem(dd_x, dd_y),
                    brush=pg.mkBrush('#ef535020')
                )
                self._equity_chart.addItem(fill)
            
        except Exception as e:
            print(f"[Chart] 에쿼티 그리기 오류: {e}")
    
    def _on_trade_clicked(self, candle_index: int):
        """거래 클릭 → 차트 이동"""
        self.go_to_candle.emit(candle_index)
    
    def _save_screenshot(self):
        """위젯 스크린샷 저장"""
        if not self._result:
            return
        
        # 파일 저장 다이얼로그
        default_name = f"backtest_result_{self._result.strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "백테스트 결과 스크린샷 저장",
            default_name,
            "PNG Files (*.png);;JPG Files (*.jpg);;All Files (*)"
        )
        
        if filename:
            # 위젯 스크린샷
            pixmap = self.grab()
            pixmap.save(filename)
            print(f"✅ 스크린샷 저장: {filename}")
    
    def _export_csv(self):
        """CSV 내보내기"""
        if not self._result or not self._result.trades:
            return
        
        # 파일 저장 다이얼로그
        filename, _ = QFileDialog.getSaveFileName(
            self, "CSV 내보내기", 
            f"backtest_{self._result.strategy_id}_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not filename:
            return
        
        # CSV 작성
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                "번호", "시간", "방향", "진입가", "손절가", "익절가", 
                "청산가", "청산시간", "결과", "수익률"
            ])
            
            # 데이터
            for i, trade in enumerate(self._result.trades):
                entry_time = datetime.fromtimestamp(trade.signal_time / 1000).strftime("%Y-%m-%d %H:%M")
                exit_time = datetime.fromtimestamp(trade.exit_time / 1000).strftime("%Y-%m-%d %H:%M") if trade.exit_time else ""
                
                result_map = {
                    TradeStatus.TP_HIT: "TP",
                    TradeStatus.SL_HIT: "SL",
                    TradeStatus.CLOSED: "청산"
                }
                
                writer.writerow([
                    i + 1,
                    entry_time,
                    trade.signal_type.value.upper(),
                    f"{trade.entry_price:.2f}",
                    f"{trade.stop_loss:.2f}",
                    f"{trade.take_profit:.2f}",
                    f"{trade.exit_price:.2f}",
                    exit_time,
                    result_map.get(trade.status, ""),
                    f"{trade.pnl_percent:+.2f}%"
                ])
        
        print(f"✅ CSV 저장 완료: {filename}")
    
    def _show_trade_details(self):
        """상세 매매 팝업 표시"""
        try:
            from trade_detail_popup import TradeDetailPopup
            import pandas as pd
            
            # 현재 거래 데이터를 상세 형식으로 변환
            if not self._result or not self._result.trades:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "알림", "표시할 매매 데이터가 없습니다.")
                return
            
            detailed_trades = []
            for i, trade in enumerate(self._result.trades):
                detailed_trades.append({
                    'number': i + 1,
                    'type': 'Long' if trade.signal_type.value == 1 else 'Short',
                    'entry_time': pd.Timestamp(trade.signal_time, unit='ms'),
                    'exit_time': pd.Timestamp(trade.exit_time, unit='ms') if trade.exit_time else None,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'initial_sl': trade.stop_loss,
                    'be_triggered': trade.pnl_percent >= -0.1 if trade.pnl_percent else False,
                    'pnl': trade.pnl_percent,
                    'entry_idx': trade.candle_index,
                    'exit_idx': trade.candle_index + 10  # 추정값
                })
            
            # 15m 데이터 생성 (캔들 데이터에서)
            if hasattr(self, '_candles') and self._candles:
                df_15m = pd.DataFrame([{
                    'timestamp': pd.Timestamp(c.timestamp, unit='ms'),
                    'open': c.open,
                    'high': c.high,
                    'low': c.low,
                    'close': c.close,
                    'volume': c.volume
                } for c in self._candles])
            else:
                df_15m = pd.DataFrame()
            
            popup = TradeDetailPopup(detailed_trades, df_15m, self)
            popup.exec_()
            
        except Exception as e:
            print(f"상세 매매 표시 오류: {e}")
            import traceback
            traceback.print_exc()


# ============== 테스트 ==============
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from strategies.common.strategy_interface import SignalType
    
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background-color: #1e1e1e; }")
    
    # 더미 데이터
    trades = []
    for i in range(20):
        trades.append(TradeSignal(
            signal_type=SignalType.LONG,
            symbol="BTC/USDT",
            timeframe="15m",
            entry_price=42000 + i * 100,
            stop_loss=41000 + i * 100,
            take_profit=44000 + i * 100,
            signal_time=1701388800000 + i * 3600000,
            candle_index=50 + i * 10,
            status=TradeStatus.TP_HIT if i % 3 != 0 else TradeStatus.SL_HIT,
            exit_price=44000 + i * 100 if i % 3 != 0 else 41000 + i * 100,
            exit_time=1701388800000 + i * 3600000 + 7200000,
            pnl_percent=3.0 if i % 3 != 0 else -1.5
        ))
    
    result = BacktestResult(
        strategy_id="high_octane",
        symbol="BTC/USDT",
        timeframe="15m",
        start_time=1701388800000,
        end_time=1704067200000,
        trades=trades,
        total_trades=20,
        win_trades=14,
        lose_trades=6,
        win_rate=70.0,
        total_pnl=33.0,
        profit_factor=2.8,
        max_drawdown=8.5,
        sharpe_ratio=2.1
    )
    
    widget = BacktestResultWidget()
    widget.set_result(result)
    widget.setWindowTitle("백테스트 결과")
    widget.resize(800, 600)
    widget.show()
    
    sys.exit(app.exec_())
