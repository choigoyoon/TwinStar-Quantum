"""
실시간 포지션 상태 위젯
- 현재 포지션 표시
- 실시간 PnL 업데이트
- 손절선 표시
"""

import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QProgressBar
)

# Logging
import logging
logger = logging.getLogger(__name__)
from PyQt5.QtCore import Qt, pyqtSignal
from locales.lang_manager import t

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class PositionCard(QFrame):
    """개별 포지션 카드"""
    
    close_clicked = pyqtSignal(str)  # symbol
    
    def __init__(self, symbol: str, side: str, entry_price: float,
                 current_price: float, stop_loss: float, size: float):
        super().__init__()
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.size = size
        self._init_ui(current_price)
    
    def _init_ui(self, current_price: float):
        # 수익 계산
        if self.side == "LONG":
            pnl_pct = (current_price / self.entry_price - 1) * 100
        else:
            pnl_pct = (1 - current_price / self.entry_price) * 100
        
        color = "#26a69a" if pnl_pct >= 0 else "#ef5350"
        side_color = "#26a69a" if self.side == "LONG" else "#ef5350"
        
        self.setStyleSheet(f"""
            PositionCard {{
                border: 1px solid {color}40;
                border-left: 4px solid {side_color};
                border-radius: 8px;
            }}
        """) # Removed hardcoded background #1e2330
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)
        
        # 헤더: 심볼 + 방향
        header = QHBoxLayout()
        
        symbol_label = QLabel(f"💎 {self.symbol}")
        symbol_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        header.addWidget(symbol_label)
        
        side_label = QLabel(self.side)
        side_label.setStyleSheet(f"color: {side_color}; font-weight: bold;")
        header.addWidget(side_label)
        
        header.addStretch()
        
        # 청산 버튼
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #ef535020;
                color: #ef5350;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #ef535060; }
        """)
        close_btn.setToolTip(t("dashboard.close_position_tip", "포지션 청산"))
        close_btn.clicked.connect(lambda: self.close_clicked.emit(self.symbol))
        header.addWidget(close_btn)
        
        layout.addLayout(header)
        
        # 가격 정보
        price_layout = QGridLayout()
        price_layout.setSpacing(5)
        
        labels = [
            (t("dashboard.entry_price", "진입가"), f"${self.entry_price:,.2f}"),
            (t("dashboard.current_price", "현재가"), f"${current_price:,.2f}"),
            (t("dashboard.stop_loss_price", "손절가"), f"${self.stop_loss:,.2f}"),
            (t("dashboard.quantity", "수량"), f"{self.size:.4f}"),
        ]
        
        for i, (label, value) in enumerate(labels):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #787b86; font-size: 11px;")
            price_layout.addWidget(lbl, i // 2, (i % 2) * 2)
            
            val = QLabel(value)
            val.setStyleSheet("color: #d1d4dc; font-size: 12px;")
            price_layout.addWidget(val, i // 2, (i % 2) * 2 + 1)
        
        layout.addLayout(price_layout)
        
        # PnL 표시
        self.pnl_label = QLabel(f"{pnl_pct:+.2f}%")
        self.pnl_label.setStyleSheet(f"""
            color: {color};
            font-size: 24px;
            font-weight: bold;
        """)
        self.pnl_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.pnl_label)
        
        # 손절까지 거리 프로그레스바
        sl_distance = abs(current_price - self.stop_loss) / current_price * 100
        
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(min(int(sl_distance * 10), 100))  # 10% = 100%
        progress.setTextVisible(False)
        progress.setFixedHeight(6)
        progress.setStyleSheet(f"""
            QProgressBar {{
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 3px;
            }}
        """) # Removed background: #131722
        layout.addWidget(progress)
        
        sl_label = QLabel(t("dashboard.distance_to_sl", "손절까지 {0}%").format(f"{sl_distance:.2f}"))
        sl_label.setStyleSheet("color: #787b86; font-size: 10px;")
        sl_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(sl_label)
    
    def update_price(self, current_price: float):
        """가격 업데이트"""
        if self.side == "LONG":
            pnl_pct = (current_price / self.entry_price - 1) * 100
        else:
            pnl_pct = (1 - current_price / self.entry_price) * 100
        
        color = "#26a69a" if pnl_pct >= 0 else "#ef5350"
        self.pnl_label.setText(f"{pnl_pct:+.2f}%")
        self.pnl_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")


class PositionStatusWidget(QFrame):
    """포지션 상태 위젯"""
    
    def __init__(self):
        super().__init__()
        self.positions = {}  # symbol -> PositionCard
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            PositionStatusWidget {
                border: 1px solid #2a2e3b;
                border-radius: 12px;
            }
        """) # Removed background: #131722
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 헤더
        header = QHBoxLayout()
        
        title = QLabel(t("dashboard.active_positions_title", "📊 현재 포지션"))
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.status_label = QLabel(t("common.waiting", "대기 중"))
        self.status_label.setStyleSheet("color: #787b86; font-size: 12px;")
        header.addWidget(self.status_label)
        
        layout.addLayout(header)
        
        # 포지션 컨테이너
        self.positions_layout = QVBoxLayout()
        self.positions_layout.setSpacing(10)
        layout.addLayout(self.positions_layout)
        
        # 빈 상태 표시
        self.empty_label = QLabel(t("dashboard.no_positions", "🔍 포지션 없음\n\n신호 대기 중..."))
        self.empty_label.setStyleSheet("color: #787b86; font-size: 13px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.positions_layout.addWidget(self.empty_label)
        
        layout.addStretch()
    
    def add_position(self, symbol: str, side: str, entry_price: float,
                     current_price: float, stop_loss: float, size: float):
        """포지션 추가"""
        if symbol in self.positions:
            self.positions[symbol].update_price(current_price)
            return
        
        self.empty_label.hide()
        
        card = PositionCard(symbol, side, entry_price, current_price, stop_loss, size)
        card.close_clicked.connect(self._on_close_position)
        
        self.positions[symbol] = card
        self.positions_layout.addWidget(card)
        
        self._update_status()
    
    def remove_position(self, symbol: str):
        """포지션 제거"""
        if symbol in self.positions:
            card = self.positions.pop(symbol)
            card.deleteLater()
        
        if not self.positions:
            self.empty_label.show()
        
        self._update_status()
    
    def update_position(self, symbol: str, current_price: float):
        """포지션 가격 업데이트"""
        if symbol in self.positions:
            self.positions[symbol].update_price(current_price)
    
    def _on_close_position(self, symbol: str):
        """포지션 청산 요청"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, t("dashboard.close_position_title", "포지션 청산"),
            t("dashboard.close_position_ask", "{0} 포지션을 청산하시겠습니까?").format(symbol),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # 실제 청산 로직 연결
            try:
                from exchanges.exchange_manager import get_exchange_manager
                em = get_exchange_manager()
                
                from exchanges.bybit_exchange import BybitExchange
                from exchanges.binance_exchange import BinanceExchange
                from exchanges.okx_exchange import OkxExchange
                from exchanges.bitget_exchange import BitgetExchange
                
                wrapper_map = {
                    'bybit': BybitExchange,
                    'binance': BinanceExchange,
                    'okx': OkxExchange,
                    'bitget': BitgetExchange
                }
                
                closed = False
                
                # 연결된 거래소 찾기
                for exchange_name in ['bybit', 'binance', 'okx', 'bitget']:
                    config = em.configs.get(exchange_name)
                    if not config:
                        continue
                        
                    # Wrapper 클래스 확인
                    WrapperClass = wrapper_map.get(exchange_name)
                    if not WrapperClass:
                        continue
                        
                    # Wrapper 인스턴스 생성
                    wrapper_config = {
                        'api_key': config.api_key,
                        'api_secret': config.api_secret,
                        'testnet': config.testnet,
                        'passphrase': config.passphrase,
                        'symbol': symbol # 심볼 설정
                    }
                    wrapper = WrapperClass(wrapper_config)
                    
                    if not wrapper.connect():
                        continue
                        
                    try:
                        # 청산 시도
                        if wrapper.close_position():
                            QMessageBox.information(self, t("common.success", "청산 완료"), f"{exchange_name}: {symbol} " + t("dashboard.close_success", "청산 성공!"))
                            closed = True
                            break
                    except Exception as e:
                        logger.info(f"청산 시도 실패 ({exchange_name}): {e}")
                        
                if not closed:
                    QMessageBox.warning(self, t("common.error", "청산 실패"), f"{symbol} " + t("dashboard.close_fail_no_exchange", "청산에 실패했습니다 (연결된 거래소 없음)"))
                    
            except Exception as e:
                QMessageBox.critical(self, t("common.error", "오류"), t("dashboard.close_error", "청산 오류") + f": {e}")
            except ImportError:
                logger.info(f"[Close] {symbol} 청산 요청 (exchange_manager 미사용)")
            
            self.remove_position(symbol)
    
    def _update_status(self):
        """상태 업데이트"""
        count = len(self.positions)
        if count == 0:
            self.status_label.setText("대기 중")
            self.status_label.setStyleSheet("color: #787b86; font-size: 12px;")
        else:
            self.status_label.setText(f"📊 {count}개 보유 중")
            self.status_label.setStyleSheet("color: #26a69a; font-size: 12px;")


# 테스트
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    widget = PositionStatusWidget()
    widget.setStyleSheet("background: #0b0e14;")
    widget.resize(350, 400)
    
    # 테스트 포지션 추가
    widget.add_position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=98000,
        current_price=99500,
        stop_loss=96500,
        size=0.05
    )
    
    widget.show()
    sys.exit(app.exec_())
