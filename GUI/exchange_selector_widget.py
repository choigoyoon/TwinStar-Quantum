# exchange_selector_widget.py
"""Exchange Selector Widget - Exchange/Market/Symbol Selection"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QRadioButton, QButtonGroup, QCompleter, QFrame
)

# Logging
import logging
logger = logging.getLogger(__name__)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel

from exchanges.exchange_manager import ExchangeManager


class ExchangeSelectorWidget(QWidget):
    """Exchange selection widget with market type and symbol selector"""
    
    # Signal: (exchange_id, market_type, symbol)
    symbol_changed = pyqtSignal(str, str, str)
    
    def __init__(self, exchange_manager: ExchangeManager | None = None):
        super().__init__()
        self.em = exchange_manager if exchange_manager else ExchangeManager()
        
        # Current selection state
        self.current_exchange = 'binance'
        self.current_market_type = 'usdt_futures'
        self.current_symbol = 'BTC/USDT:USDT'
        
        self.init_ui()
        self.load_exchanges()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 1. Exchange selector
        ex_layout = QHBoxLayout()
        lbl_ex = QLabel("Exchange:")
        lbl_ex.setFixedWidth(70)
        self.combo_exchange = QComboBox()
        self.combo_exchange.currentIndexChanged.connect(self.on_exchange_changed)
        ex_layout.addWidget(lbl_ex)
        ex_layout.addWidget(self.combo_exchange)
        layout.addLayout(ex_layout)
        
        # 2. Market type (Spot / USDT Futures / Coin Futures)
        type_layout = QHBoxLayout()
        lbl_type = QLabel("Market:")
        lbl_type.setFixedWidth(70)
        type_layout.addWidget(lbl_type)
        
        self.bg_type = QButtonGroup(self)
        
        self.rb_spot = QRadioButton("Spot")
        self.rb_usdt = QRadioButton("USDT-M")
        self.rb_coin = QRadioButton("Coin-M")
        
        self.bg_type.addButton(self.rb_spot, 1)
        self.bg_type.addButton(self.rb_usdt, 2)
        self.bg_type.addButton(self.rb_coin, 3)
        
        self.rb_usdt.setChecked(True)  # Default
        
        self.bg_type.buttonClicked.connect(self.on_type_changed)
        
        type_layout.addWidget(self.rb_spot)
        type_layout.addWidget(self.rb_usdt)
        type_layout.addWidget(self.rb_coin)
        layout.addLayout(type_layout)
        
        # 3. Symbol selector (with search)
        sym_layout = QHBoxLayout()
        lbl_sym = QLabel("Symbol:")
        lbl_sym.setFixedWidth(70)
        self.combo_symbol = QComboBox()
        self.combo_symbol.setEditable(True)
        self.combo_symbol.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_symbol.currentIndexChanged.connect(self.on_symbol_changed)
        
        # Auto-complete
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.combo_symbol.setCompleter(self.completer)
        
        sym_layout.addWidget(lbl_sym)
        sym_layout.addWidget(self.combo_symbol)
        layout.addLayout(sym_layout)
        
        # 4. Info panel (optional)
        self.info_frame = QFrame()
        self.info_frame.setStyleSheet("background-color: #161b22; border-radius: 4px; padding: 5px;")
        info_layout = QHBoxLayout(self.info_frame)
        info_layout.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_price = QLabel("Price: -")
        self.lbl_change = QLabel("24h: -")
        
        info_layout.addWidget(self.lbl_price)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_change)
        
        layout.addWidget(self.info_frame)
        
    def load_exchanges(self):
        """Load available exchanges"""
        self.combo_exchange.blockSignals(True)
        self.combo_exchange.clear()
        
        # Overseas exchanges
        tier1 = ['okx', 'bingx', 'bitget']
        for ex in self.em.get_overseas_exchanges():
            prefix = "[Direct API]" if ex.id in tier1 else "[Global]"
            self.combo_exchange.addItem(f"{prefix} {ex.name}", ex.id)
            
        # Domestic exchanges
        for ex in self.em.get_domestic_exchanges():
            self.combo_exchange.addItem(f"[Korea] {ex.name}", ex.id)
            
        self.combo_exchange.blockSignals(False)
        
        # Default: Binance
        idx = self.combo_exchange.findData('binance')
        if idx >= 0:
            self.combo_exchange.setCurrentIndex(idx)
        else:
            self.on_exchange_changed(0)
            
    def on_exchange_changed(self, index):
        """Handle exchange change"""
        exchange_id = self.combo_exchange.currentData()
        self.current_exchange = exchange_id
        logger.info(f"[DEBUG] Exchange changed to: {exchange_id}")
        
        # Update market type buttons based on exchange capabilities
        config = self.em.get_supported_exchanges().get(exchange_id)
        if config:
            self.rb_spot.setEnabled(config.spot)
            self.rb_usdt.setEnabled(config.futures)
            self.rb_coin.setEnabled(config.futures)
            
            # Auto-switch if current type not supported
            if self.rb_usdt.isChecked() and not config.futures:
                self.rb_spot.setChecked(True)
                self.current_market_type = 'spot'
            elif self.rb_spot.isChecked() and not config.spot:
                self.rb_usdt.setChecked(True)
                self.current_market_type = 'usdt_futures'
                
        self.load_symbols()
        
    def on_type_changed(self, button):
        """Handle market type change"""
        if button == self.rb_spot:
            self.current_market_type = 'spot'
        elif button == self.rb_usdt:
            self.current_market_type = 'usdt_futures'
        elif button == self.rb_coin:
            self.current_market_type = 'coin_futures'
            
        logger.info(f"[DEBUG] Market type changed to: {self.current_market_type}")
        self.load_symbols()
        
    def load_symbols(self):
        """Load symbols for current exchange and market type"""
        self.combo_symbol.blockSignals(True)
        self.combo_symbol.clear()
        
        logger.info(f"[DEBUG] Loading symbols for {self.current_exchange} ({self.current_market_type})...")
        symbols = self.em.get_symbols(self.current_exchange, self.current_market_type)
        
        symbol_names = []
        for s in symbols:
            name = s['symbol']
            self.combo_symbol.addItem(name)
            symbol_names.append(name)
            
        # Update completer model
        model = QStringListModel(symbol_names)
        self.completer.setModel(model)
        
        self.combo_symbol.blockSignals(False)
        
        if symbols:
            self.combo_symbol.setCurrentIndex(0)
            self.on_symbol_changed(0)
        else:
            self.lbl_price.setText("Price: -")
            self.lbl_change.setText("24h: -")
            
    def on_symbol_changed(self, index):
        """Handle symbol change"""
        symbol = self.combo_symbol.currentText()
        if not symbol:
            return
            
        self.current_symbol = symbol
        logger.info(f"[DEBUG] Symbol selected: {symbol}")
        
        # Emit signal
        self.symbol_changed.emit(self.current_exchange, self.current_market_type, symbol)
        
        # Update ticker info
        self.update_ticker()
        
    def update_ticker(self):
        """Update price and 24h change display"""
        ticker = self.em.get_ticker(self.current_exchange, self.current_symbol)
        if ticker:
            price = ticker.get('price')
            change = ticker.get('change_24h')
            
            if price is not None:
                self.lbl_price.setText(f"Price: {float(price):,.4f}")
            else:
                self.lbl_price.setText("Price: -")
            
            if change is not None:
                change = float(change)
                color = "#ff4d4d" if change < 0 else "#00cc00" if change > 0 else "#c9d1d9"
                sign = "+" if change > 0 else ""
                self.lbl_change.setText(f"24h: {sign}{change:.2f}%")
                self.lbl_change.setStyleSheet(f"color: {color}; font-weight: bold;")
            else:
                self.lbl_change.setText("24h: -")
                self.lbl_change.setStyleSheet("color: #c9d1d9;")
        else:
            self.lbl_price.setText("Price: -")
            self.lbl_change.setText("24h: -")
            self.lbl_change.setStyleSheet("color: #c9d1d9;")


# Test code
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Set style
    app.setStyle('Fusion')
    
    window = QWidget()
    layout = QVBoxLayout(window)
    window.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
    
    # Create ExchangeManager (mock)
    em = ExchangeManager()
    
    widget = ExchangeSelectorWidget(em)
    layout.addWidget(widget)
    
    # Result label
    lbl_result = QLabel("Selected: -")
    layout.addWidget(lbl_result)
    
    def on_change(ex, mk, sym):
        lbl_result.setText(f"Selected: {ex} | {mk} | {sym}")
        
    widget.symbol_changed.connect(on_change)
    
    window.resize(400, 200)
    window.show()
    
    sys.exit(app.exec())
