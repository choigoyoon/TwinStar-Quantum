"""
트레이딩 용어집 팝업
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QScrollArea, QWidget, QFrame
)
from PyQt5.QtCore import Qt


class GlossaryPopup(QDialog):
    """트레이딩 용어집"""
    
    GLOSSARY = {
        "ATR": {
            "full": "Average True Range",
            "ko": "평균 진정 범위. 변동성 측정 지표",
            "en": "Average True Range. Volatility indicator"
        },
        "MDD": {
            "full": "Maximum Drawdown",
            "ko": "최대 낙폭. 고점 대비 최대 손실률",
            "en": "Maximum Drawdown. Largest peak-to-trough decline"
        },
        "RSI": {
            "full": "Relative Strength Index",
            "ko": "상대강도지수. 과매수/과매도 판단 (0~100)",
            "en": "Relative Strength Index. Overbought/oversold indicator"
        },
        "SL": {
            "full": "Stop Loss",
            "ko": "손절가. 손실 제한 가격",
            "en": "Stop Loss. Price to limit losses"
        },
        "TP": {
            "full": "Take Profit",
            "ko": "익절가. 이익 실현 가격",
            "en": "Take Profit. Price to realize profits"
        },
        "Leverage": {
            "full": "Leverage",
            "ko": "레버리지. 증거금 대비 거래 배수",
            "en": "Leverage. Trading multiplier against margin"
        },
        "Win Rate": {
            "full": "Win Rate",
            "ko": "승률. 수익 거래 비율 (%)",
            "en": "Win Rate. Percentage of profitable trades"
        },
        "PnL": {
            "full": "Profit and Loss",
            "ko": "손익. 수익/손실 금액",
            "en": "Profit and Loss. Net gains or losses"
        },
        "Sharpe": {
            "full": "Sharpe Ratio",
            "ko": "샤프 비율. 위험 대비 수익률",
            "en": "Sharpe Ratio. Risk-adjusted return"
        },
        "Trailing Stop": {
            "full": "Trailing Stop",
            "ko": "트레일링 스탑. 가격 따라 움직이는 손절",
            "en": "Trailing Stop. Stop-loss that follows price"
        },
        "Entry": {
            "full": "Entry",
            "ko": "진입. 포지션 시작 지점",
            "en": "Entry. Position opening point"
        },
        "Exit": {
            "full": "Exit",
            "ko": "청산. 포지션 종료 지점",
            "en": "Exit. Position closing point"
        },
        "Long": {
            "full": "Long Position",
            "ko": "롱 포지션. 가격 상승에 베팅",
            "en": "Long Position. Betting on price increase"
        },
        "Short": {
            "full": "Short Position",
            "ko": "숏 포지션. 가격 하락에 베팅",
            "en": "Short Position. Betting on price decrease"
        },
        "Backtest": {
            "full": "Backtesting",
            "ko": "백테스트. 과거 데이터로 전략 검증",
            "en": "Backtesting. Testing strategy with historical data"
        },
        "Slippage": {
            "full": "Slippage",
            "ko": "슬리피지. 주문가와 체결가 차이",
            "en": "Slippage. Difference between expected and executed price"
        },
        "Timeframe": {
            "full": "Timeframe",
            "ko": "타임프레임. 캔들 시간 단위 (1m, 15m, 1h 등)",
            "en": "Timeframe. Candle time unit (1m, 15m, 1h, etc.)"
        },
        "W Pattern": {
            "full": "W Pattern (Double Bottom)",
            "ko": "W 패턴. 더블 바텀. 상승 반전 신호",
            "en": "W Pattern. Double Bottom. Bullish reversal signal"
        },
        "M Pattern": {
            "full": "M Pattern (Double Top)",
            "ko": "M 패턴. 더블 탑. 하락 반전 신호",
            "en": "M Pattern. Double Top. Bearish reversal signal"
        },
        "MACD": {
            "full": "Moving Average Convergence Divergence",
            "ko": "이동평균 수렴확산. 추세 및 모멘텀 지표",
            "en": "Moving Average Convergence Divergence. Trend/momentum indicator"
        },
        "Pending": {
            "full": "Pending Signal",
            "ko": "대기 시그널. 조건 충족 대기 중인 진입 신호",
            "en": "Pending Signal. Entry signal waiting for conditions"
        }
    }
    
    def __init__(self, parent=None, lang='ko'):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle("📖 트레이딩 용어집" if lang == 'ko' else "📖 Trading Glossary")
        self.setFixedSize(500, 600)
        self.setStyleSheet("""
            QDialog { background: #1a1a2e; color: white; }
            QLineEdit { 
                background: #2a2a3e; color: white; 
                border: 1px solid #444; border-radius: 5px; padding: 8px;
            }
            QScrollArea { border: none; background: transparent; }
        """)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 검색창
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 18px;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색어 입력..." if self.lang == 'ko' else "Search...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(8)
        
        self._populate_glossary()
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
    
    def _populate_glossary(self, filter_text=""):
        # 기존 위젯 제거
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 용어 추가
        for term, data in sorted(self.GLOSSARY.items()):
            if filter_text and filter_text.lower() not in term.lower():
                continue
            
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background: rgba(255,255,255,0.05);
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setSpacing(3)
            frame_layout.setContentsMargins(12, 10, 12, 10)
            
            # 용어명
            title = QLabel(f"<b>{term}</b> <span style='color:#888'>({data['full']})</span>")
            title.setStyleSheet("color: #4CAF50; font-size: 14px;")
            frame_layout.addWidget(title)
            
            # 설명
            desc = QLabel(data[self.lang])
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #ccc; font-size: 12px;")
            frame_layout.addWidget(desc)
            
            self.content_layout.addWidget(frame)
        
        self.content_layout.addStretch()
    
    def _on_search(self, text):
        self._populate_glossary(text)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    popup = GlossaryPopup(lang='ko')
    popup.show()
    sys.exit(app.exec_())
