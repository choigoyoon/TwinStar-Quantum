# E:/trading/gui/trade_chart_dialog.py
"""
거래 상세 차트 다이얼로그 (TradingView 스타일)
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime

# 한글 폰트 설정
import matplotlib

# Logging
import logging
logger = logging.getLogger(__name__)
matplotlib.rcParams['font.family'] = 'Malgun Gothic'  # 맑은 고딕
matplotlib.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.common.strategy_interface import TradeSignal, Candle
from typing import List


class TradeChartDialog(QDialog):
    """거래 상세 차트 다이얼로그"""
    
    def __init__(self, trade: TradeSignal, candles: List[Candle], parent=None):
        super().__init__(parent)
        self._trade = trade
        self._candles = candles
        self._init_ui()
        self._plot_chart()
    
    def _init_ui(self):
        self.setWindowTitle("거래 상세")
        self.setModal(False)
        self.resize(1200, 700)
        
        layout = QVBoxLayout(self)
        
        # 정보 헤더
        info_text = f"📊 {self._trade.symbol} | {self._trade.signal_type.value.upper()} | "
        info_text += f"진입: ${self._trade.entry_price:,.2f} → "
        info_text += f"청산: ${self._trade.exit_price:,.2f} ({self._trade.pnl_percent:+.2f}%)"
        
        header_layout = QHBoxLayout()
        
        info_label = QLabel(info_text)
        info_label.setFont(QFont("Arial", 11, QFont.Bold))
        info_label.setStyleSheet("color: #ffffff; padding: 10px; background-color: #2d2d2d; border-radius: 4px;")
        header_layout.addWidget(info_label)
        
        # 저장 버튼
        save_btn = QPushButton("💾 이미지로 저장")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        save_btn.clicked.connect(self._save_image)
        header_layout.addWidget(save_btn)
        
        layout.addLayout(header_layout)
        
        # Matplotlib 차트
        self._figure = Figure(figsize=(12, 7), facecolor='#1e1e1e')
        self._canvas = FigureCanvas(self._figure)
        layout.addWidget(self._canvas)
    
    def _save_image(self):
        """차트를 이미지로 저장"""
        from datetime import datetime
        
        # 파일 저장 다이얼로그
        default_name = f"trade_chart_{self._trade.symbol.replace('/', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "차트 이미지 저장",
            default_name,
            "PNG Files (*.png);;JPG Files (*.jpg);;All Files (*)"
        )
        
        if filename:
            # 이미지 저장
            self._figure.savefig(
                filename,
                dpi=150,
                facecolor='#1e1e1e',
                edgecolor='none',
                bbox_inches='tight'
            )
            logger.info(f"✅ 차트 이미지 저장: {filename}")
    
    def _plot_chart(self):
        """TradingView 스타일 차트 그리기"""
        # 진입 인덱스 기준으로 전후 캔들 추출
        entry_idx = self._trade.candle_index
        
        # 진입 전 50봉 + 진입 후 100봉 (청산까지)
        start_idx = max(0, entry_idx - 50)
        end_idx = min(len(self._candles), entry_idx + 100)
        
        plot_candles = self._candles[start_idx:end_idx]
        
        if len(plot_candles) == 0:
            return
        
        # 데이터 준비
        times = [datetime.fromtimestamp(c.timestamp / 1000) for c in plot_candles]
        opens = [c.open for c in plot_candles]
        highs = [c.high for c in plot_candles]
        lows = [c.low for c in plot_candles]
        closes = [c.close for c in plot_candles]
        
        # 진입/청산 인덱스 (plot_candles 기준으로 재계산)
        entry_plot_idx = entry_idx - start_idx
        
        # 차트 그리기
        ax = self._figure.add_subplot(111)
        ax.set_facecolor('#0d0d0d')
        self._figure.patch.set_facecolor('#1e1e1e')
        
        # 캔들스틱 그리기 (TradingView 스타일)
        width = 0.6 / 24  # 시간 단위로 조정
        
        for i in range(len(plot_candles)):
            color = '#26a69a' if closes[i] >= opens[i] else '#ef5350'  # TradingView 색상
            
            # 캔들 몸통
            ax.add_patch(plt.Rectangle(
                (mdates.date2num(times[i]) - width/2, min(opens[i], closes[i])),
                width,
                abs(closes[i] - opens[i]),
                facecolor=color,
                edgecolor=color,
                linewidth=0
            ))
            
            # 캔들 심지
            ax.plot([mdates.date2num(times[i]), mdates.date2num(times[i])],
                   [lows[i], highs[i]], color=color, linewidth=1)
        
        # 추세선 그리기 (저점 2개 연결 - 진입 근거)
        # 진입 전 저점 2개 찾기
        if entry_plot_idx >= 20:
            past_lows = [(i, lows[i]) for i in range(max(0, entry_plot_idx - 40), entry_plot_idx - 5)]
            if len(past_lows) >= 2:
                # 가장 낮은 2개 저점 찾기
                past_lows_sorted = sorted(past_lows, key=lambda x: x[1])
                pivot1_idx, pivot1_price = past_lows_sorted[0]
                pivot2_idx, pivot2_price = past_lows_sorted[1]
                
                # 시간순 정렬
                if pivot1_idx > pivot2_idx:
                    pivot1_idx, pivot2_idx = pivot2_idx, pivot1_idx
                    pivot1_price, pivot2_price = pivot2_price, pivot1_price
                
                # 추세선 연장
                slope = (pivot2_price - pivot1_price) / (pivot2_idx - pivot1_idx) if pivot2_idx != pivot1_idx else 0
                
                # 추세선 그리기 (pivot1 부터 진입 지점 + 10까지)
                tl_start_idx = pivot1_idx
                tl_end_idx = min(entry_plot_idx + 10, len(times) - 1)
                
                tl_times = [mdates.date2num(times[i]) for i in range(tl_start_idx, tl_end_idx + 1)]
                tl_prices = [pivot1_price + slope * (i - pivot1_idx) for i in range(tl_start_idx, tl_end_idx + 1)]
                
                ax.plot(tl_times, tl_prices, color='#ffeb3b', linestyle='-', linewidth=2, 
                       label='추세선 (지지)', alpha=0.7, zorder=3)
                
                # 피벗 포인트 표시
                ax.plot(mdates.date2num(times[pivot1_idx]), pivot1_price, 
                       marker='o', markersize=8, color='#ffeb3b', zorder=4)
                ax.plot(mdates.date2num(times[pivot2_idx]), pivot2_price, 
                       marker='o', markersize=8, color='#ffeb3b', zorder=4)
        
        # 진입가 라인 (하늘색)
        ax.axhline(y=self._trade.entry_price, color='#2196f3', linestyle='--', linewidth=2, 
                  label=f'진입가: ${self._trade.entry_price:,.2f}', alpha=0.8, zorder=2)
        
        # TP 라인 (녹색)
        ax.axhline(y=self._trade.take_profit, color='#26a69a', linestyle='--', linewidth=2, 
                  label=f'TP: ${self._trade.take_profit:,.2f}', alpha=0.8, zorder=2)
        
        # SL 라인 (빨간색)
        ax.axhline(y=self._trade.stop_loss, color='#ef5350', linestyle='--', linewidth=2, 
                  label=f'SL: ${self._trade.stop_loss:,.2f}', alpha=0.8, zorder=2)
        
        # 청산가 라인 (주황색) - 제거 (청산 마커로 충분)
        # ax.axhline(y=self._trade.exit_price, color='#ff9800', linestyle='-', linewidth=2, label=f'청산: ${self._trade.exit_price:,.2f}', alpha=0.9)
        
        # 진입 마커 (큰 삼각형)
        if entry_plot_idx < len(times):
            marker_color = '#4caf50' if self._trade.signal_type.value == 'long' else '#f44336'
            marker = '^' if self._trade.signal_type.value == 'long' else 'v'
            ax.plot(mdates.date2num(times[entry_plot_idx]), self._trade.entry_price, 
                   marker=marker, markersize=15, color=marker_color, label='Entry', zorder=5,
                   markeredgecolor='white', markeredgewidth=1.5)
        
        # 청산 마커 - TP/SL에 실제로 닿은 지점 찾기
        exit_plot_idx = None
        exit_reason = ""
        
        # 진입 이후 캔들에서 TP/SL 도달 여부 확인
        for i in range(entry_plot_idx + 1, len(plot_candles)):
            # SL 체크 (Long의 경우 저가가 SL보다 낮으면)
            if self._trade.signal_type.value == 'long':
                if lows[i] <= self._trade.stop_loss:
                    exit_plot_idx = i
                    exit_reason = "SL 손절"
                    break
                # TP 체크
                if highs[i] >= self._trade.take_profit:
                    exit_plot_idx = i
                    exit_reason = "TP 익절"
                    break
        
        if exit_plot_idx is not None and exit_plot_idx < len(times):
            exit_color = '#26a69a' if 'TP' in exit_reason else '#ef5350'
            exit_marker = 'TP' if 'TP' in exit_reason else 'SL'
            
            # 청산 마커 (큰 X)
            ax.plot(mdates.date2num(times[exit_plot_idx]), self._trade.exit_price,
                   marker='X', markersize=18, color=exit_color, label=f'Exit ({exit_reason})', zorder=5,
                   markeredgecolor='white', markeredgewidth=1.5)
            
            # 청산 가격에 텍스트 주석
            ax.annotate(f'{exit_marker}\n${self._trade.exit_price:,.0f}',
                       xy=(mdates.date2num(times[exit_plot_idx]), self._trade.exit_price),
                       xytext=(10, 20), textcoords='offset points',
                       color=exit_color, fontsize=11, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='#2d2d2d', edgecolor=exit_color, alpha=0.8),
                       arrowprops=dict(arrowstyle='->', color=exit_color, lw=1.5))
        
        # 스타일 설정
        ax.set_xlabel('시간', color='#888888', fontsize=10)
        ax.set_ylabel('가격 ($)', color='#888888', fontsize=10)
        ax.tick_params(colors='#888888')
        ax.spines['bottom'].set_color('#333333')
        ax.spines['top'].set_color('#333333')
        ax.spines['left'].set_color('#333333')
        ax.spines['right'].set_color('#333333')
        ax.grid(True, color='#2d2d2d', linestyle='--', linewidth=0.5, alpha=0.3)
        
        # X축 시간 포맷
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 범례
        legend = ax.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#404040', fontsize=9)
        plt.setp(legend.get_texts(), color='#ffffff')
        
        # 타이틀
        pnl_color = '#26a69a' if self._trade.pnl_percent > 0 else '#ef5350'
        ax.set_title(f'{self._trade.symbol} | {self._trade.signal_type.value.upper()} | 수익: {self._trade.pnl_percent:+.2f}%',
                    color=pnl_color, fontsize=12, fontweight='bold', pad=15)
        
        # 타이트 레이아웃 (간격 조정)
        self._figure.tight_layout(rect=[0, 0.03, 1, 0.97])  # 위아래 여백 확보
        
        self._canvas.draw()


# ============== 테스트 ==============
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    from strategies.common.strategy_interface import SignalType, TradeStatus
    import random
    
    app = QApplication(sys.argv)
    
    # 더미 캔들 데이터 생성
    candles = []
    price = 42000
    base_time = int(datetime(2024, 1, 15, 10, 0).timestamp() * 1000)
    
    for i in range(200):
        trend = random.uniform(-50, 100)
        open_p = price
        close_p = price + trend
        high_p = max(open_p, close_p) + random.uniform(0, 50)
        low_p = min(open_p, close_p) - random.uniform(0, 50)
        
        candles.append(Candle(
            timestamp=base_time + i * 900000,  # 15분봉
            open=open_p,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=random.uniform(100, 1000)
        ))
        price = close_p
    
    # 더미 거래
    entry_idx = 100
    entry_price = candles[entry_idx].close
    
    trade = TradeSignal(
        signal_type=SignalType.LONG,
        symbol="BTC/USDT",
        timeframe="15m",
        entry_price=entry_price,
        stop_loss=entry_price * 0.985,
        take_profit=entry_price * 1.03,
        signal_time=candles[entry_idx].timestamp,
        candle_index=entry_idx,
        status=TradeStatus.TP_HIT,
        exit_price=entry_price * 1.03,
        exit_time=candles[entry_idx + 20].timestamp if entry_idx + 20 < len(candles) else None,
        pnl_percent=3.0
    )
    
    dialog = TradeChartDialog(trade, candles)
    dialog.show()
    
    sys.exit(app.exec())
