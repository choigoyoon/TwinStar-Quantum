# settings_widget.py - Exchange Settings Widget (v3 - Simplified)

# Logging
import logging
logger = logging.getLogger(__name__)
# API key settings only (Trading settings handled in trading_dashboard.py)

import sys
import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QGridLayout, QMessageBox, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

# Path setup
if not getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Module imports
try:
    from constants import EXCHANGE_INFO, SPOT_EXCHANGES, KRW_EXCHANGES
except ImportError:
    try:
        from GUI.constants import EXCHANGE_INFO, SPOT_EXCHANGES, KRW_EXCHANGES
    except ImportError:
        EXCHANGE_INFO = {
            'bybit': {'type': 'CEX', 'icon': '🟡', 'testnet': True, 'maker_fee': 0.02, 'taker_fee': 0.055},
            'binance': {'type': 'CEX', 'icon': '🟠', 'testnet': True, 'maker_fee': 0.02, 'taker_fee': 0.04},
            'okx': {'type': 'CEX', 'icon': '⚪', 'passphrase': True, 'maker_fee': 0.02, 'taker_fee': 0.05},
            'bitget': {'type': 'CEX', 'icon': '🔵', 'passphrase': True, 'maker_fee': 0.02, 'taker_fee': 0.06},
            'upbit': {'type': 'CEX', 'icon': '🟣', 'ip_required': True, 'market': 'KRW'},
            'bithumb': {'type': 'CEX', 'icon': '🟤', 'ip_required': True, 'market': 'KRW'},
        }
        SPOT_EXCHANGES = ['upbit', 'bithumb']
        KRW_EXCHANGES = ['upbit', 'bithumb']

try:
    from crypto_manager import load_api_keys, save_api_keys
except ImportError:
    try:
        from GUI.crypto_manager import load_api_keys, save_api_keys
    except ImportError:
        def load_api_keys():
            return {}
        def save_api_keys(config):
            pass

try:
    from locales import t, set_language, get_lang_manager
    from locales.lang_manager import t, set_language
except ImportError:
    def t(key, default=None):
        return default if default else key.split('.')[-1]
    def set_language(l): pass

try:
    from exchanges.exchange_manager import connect_exchange, get_exchange, test_connection
except ImportError:
    def connect_exchange(*args, **kwargs):
        return (False, "exchange_manager module load failed")
    def get_exchange(name):
        return None
    def test_connection(*args, **kwargs):
        return False
    def set_language(lang): pass
    def get_lang_manager(): return None

# License Guard
try:
    from core.license_guard import get_license_guard
    HAS_LICENSE_GUARD = True
except ImportError:
    HAS_LICENSE_GUARD = False
    get_license_guard = None

import webbrowser



class ConnectionWorker(QThread):
    finished = pyqtSignal(bool, str, object)  # success, msg, balance_data

    def __init__(self, exchange_name, api_key, secret, testnet):
        super().__init__()
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret = secret
        self.testnet = testnet

    def run(self):
        try:
            # Exchange Manager의 connect_exchange 호출
            result = connect_exchange(
                self.exchange_name,
                self.api_key,
                self.secret,
                self.testnet
            )
            
            # 결과 처리 (Tuple or Bool)
            if isinstance(result, tuple):
                success, error_msg = result
                if not error_msg and not success:
                    error_msg = "Connection failed (unknown error)"
            else:
                success = bool(result)
                error_msg = "Return type error" if not success else ""

            balance_data = None
            if success:
                # 연결 성공 시 잔고 조회까지 백그라운드에서 수행
                exchange = get_exchange(self.exchange_name)
                if exchange:
                    from utils.helpers import safe_float
                    
                    # [FIX] 거래소 이름 기반 통화 결정 (pyupbit/pybithumb는 quote_currency 속성 없음)
                    if self.exchange_name.lower() in ('upbit', 'bithumb'):
                        quote = 'KRW'
                    else:
                        quote = getattr(exchange, 'quote_currency', 'USDT')
                    
                    # get_quote_balance 메서드가 있으면 사용, 없으면 폴백
                    if hasattr(exchange, 'get_quote_balance'):
                        balance = safe_float(exchange.get_quote_balance())
                    elif hasattr(exchange, 'get_balance'):
                        # pyupbit/pybithumb: get_balance("KRW")
                        if self.exchange_name.lower() in ('upbit', 'bithumb'):
                            balance = safe_float(exchange.get_balance("KRW"))
                        else:
                            balance = safe_float(exchange.get_balance())
                    else:
                        # ccxt 직접 사용 시 fetch_balance 호출
                        try:
                            bal = exchange.fetch_balance()
                            if quote in bal and isinstance(bal[quote], dict):
                                balance = safe_float(bal[quote].get('free', bal[quote].get('total', 0)))
                            elif 'total' in bal and isinstance(bal['total'], dict):
                                balance = safe_float(bal['total'].get(quote, 0))
                            else:
                                balance = 0.0
                        except Exception:

                            balance = 0.0
                    
                    balance_data = {quote: balance}

            self.finished.emit(success, error_msg, balance_data)

        except Exception as e:
            self.finished.emit(False, str(e), None)


class TelegramCard(QFrame):
    """Telegram notification settings card"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_config()
    
    def _init_ui(self):
        self.setStyleSheet("""
            TelegramCard {
                background: #1e2330;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        self.setMinimumHeight(220)
        self.setMaximumHeight(280)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("텔레그램 알림")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)
        
        # Fields
        fields_layout = QGridLayout()
        fields_layout.setSpacing(6)
        
        fields_layout.addWidget(QLabel("Bot Token:"), 0, 0)
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setPlaceholderText("1234567890:ABC...")
        self.token_input.setToolTip("텔레그램 봇 토큰\n@BotFather에서 발급받은 토큰")
        fields_layout.addWidget(self.token_input, 0, 1)
        
        fields_layout.addWidget(QLabel("Chat ID:"), 1, 0)
        self.chat_id_input = QLineEdit()
        self.chat_id_input.setPlaceholderText("-1001234567890")
        self.chat_id_input.setToolTip("텔레그램 Chat ID\n개인 또는 그룹 채팅 ID")
        fields_layout.addWidget(self.chat_id_input, 1, 1)
        
        self.enabled_check = QCheckBox("Enable Notifications")
        self.enabled_check.setToolTip("텔레그램 알림 활성화\n체크 시 매매 알림 수신")
        fields_layout.addWidget(self.enabled_check, 2, 0, 1, 2)
        
        layout.addLayout(fields_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        test_btn = QPushButton("Test Message")
        test_btn.setToolTip("테스트 메시지 전송\n설정이 올바른지 확인")
        test_btn.clicked.connect(self._test_message)
        btn_layout.addWidget(test_btn)
        layout.addLayout(btn_layout)
        
        # Apply styles
        for widget in self.findChildren(QLabel):
            widget.setStyleSheet("color: #787b86;")
        for widget in self.findChildren(QLineEdit):
            widget.setStyleSheet("background: #131722; color: white; border: 1px solid #2a2e3b; border-radius: 4px; padding: 8px;")
        for widget in self.findChildren(QCheckBox):
            widget.setStyleSheet("color: white;")
        for widget in self.findChildren(QPushButton):
            widget.setStyleSheet("background: #1e2330; color: white; padding: 8px 15px; border: 1px solid #2a2e3b; border-radius: 5px;")
    
    def _load_config(self):
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(base_dir, 'config', 'telegram.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.token_input.setText(config.get('token', ''))
                    self.chat_id_input.setText(config.get('chat_id', ''))
                    self.enabled_check.setChecked(config.get('enabled', False))
        except (json.JSONDecodeError, IOError):
            pass
    
    def save_config(self):
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(__file__))
            config_dir = os.path.join(base_dir, 'config')
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, 'telegram.json')
            config = {
                'token': self.token_input.text(),
                'chat_id': self.chat_id_input.text(),
                'enabled': self.enabled_check.isChecked()
            }
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.info(f"Telegram config save error: {e}")
    
    def _test_message(self):
        try:
            import requests
            token = self.token_input.text()
            chat_id = self.chat_id_input.text()
            if not token or not chat_id:
                QMessageBox.warning(self, t("common.error"), "Enter Token and Chat ID")
                return
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(url, json={"chat_id": chat_id, "text": "StarU Connection Test Success!"})
            if resp.ok:
                QMessageBox.information(self, t("common.success"), "Test message sent!")
            else:
                QMessageBox.warning(self, t("common.error"), f"Send failed: {resp.text}")
        except Exception as e:
            QMessageBox.critical(self, t("common.error"), f"Error: {e}")


class ExchangeCard(QFrame):
    """Exchange API settings card (simplified version)"""
    
    def __init__(self, exchange_name: str, config: dict, parent=None):
        super().__init__(parent)
        self.exchange_name = exchange_name
        self.config = config
        self._init_ui()
        self._load_config()
    
    def _init_ui(self):
        self.setStyleSheet("""
            ExchangeCard {
                background: #1e2330;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        self.setMaximumHeight(280)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        info = EXCHANGE_INFO.get(self.exchange_name, {})
        
        icon = info.get("icon", "🔷")
        ex_type = info.get("type", "CEX")
        market = info.get("market", "")
        maker = info.get("maker_fee", 0)
        taker = info.get("taker_fee", 0)
        
        title = QLabel(f"{icon} {self.exchange_name.upper()} ({ex_type} {market})")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)
        
        fee_label = QLabel(f"Fee:{maker}/{taker}%")
        fee_label.setStyleSheet("color: #ffd700; font-size: 10px;")
        header_layout.addWidget(fee_label)
        
        if info.get("ip_required"):
            ip_warn = QLabel("IP Required")
            ip_warn.setStyleSheet("color: #ef5350; font-size: 10px; font-weight: bold;")
            header_layout.addWidget(ip_warn)
        
        if info.get("passphrase"):
            pass_warn = QLabel("Pass")
            pass_warn.setStyleSheet("color: #ff9800; font-size: 10px;")
            header_layout.addWidget(pass_warn)
        
        if info.get("testnet"):
            net_label = QLabel("Testnet")
            net_label.setStyleSheet("color: #26a69a; font-size: 10px;")
            header_layout.addWidget(net_label)
        
        header_layout.addStretch()
        
        self.status_label = QLabel("연결 안됨")
        self.status_label.setStyleSheet("color: #787b86;")
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)
        
        # Auth Fields
        fields_layout = QGridLayout()
        fields_layout.setSpacing(6)
        row = 0
        
        self.fields = {}
        
        # CEX: API Key + Secret
        if info.get("type") == "CEX":
            fields_layout.addWidget(QLabel("API Key:"), row, 0)
            self.fields['api_key'] = QLineEdit()
            self.fields['api_key'].setEchoMode(QLineEdit.Password)
            self.fields['api_key'].setPlaceholderText("Enter API Key")
            self.fields['api_key'].setToolTip("거래소 API Key\n거래소에서 발급받은 공개키")
            fields_layout.addWidget(self.fields['api_key'], row, 1)
            row += 1
            
            fields_layout.addWidget(QLabel("Secret:"), row, 0)
            self.fields['api_secret'] = QLineEdit()
            self.fields['api_secret'].setEchoMode(QLineEdit.Password)
            self.fields['api_secret'].setPlaceholderText("Enter API Secret")
            self.fields['api_secret'].setToolTip("거래소 API Secret\n⚠️ 절대 타인에게 공개하지 마세요!")
            fields_layout.addWidget(self.fields['api_secret'], row, 1)
            row += 1
            
            if info.get("passphrase"):
                fields_layout.addWidget(QLabel("Passphrase:"), row, 0)
                self.fields['password'] = QLineEdit()
                self.fields['password'].setEchoMode(QLineEdit.Password)
                self.fields['password'].setPlaceholderText("Passphrase (Required)")
                self.fields['password'].setToolTip("API Passphrase\nOKX/Bitget 등 일부 거래소에서 필수")
                fields_layout.addWidget(self.fields['password'], row, 1)
                row += 1
            
            if info.get("testnet"):
                self.fields['testnet'] = QCheckBox("Testnet Mode")
                self.fields['testnet'].setToolTip("테스트넷 모드\n체크 시 가상 자금으로 테스트")
                fields_layout.addWidget(self.fields['testnet'], row, 0, 1, 2)
                row += 1
        
        # DEX: Private Key
        elif info.get("type") == "DEX":
            fields_layout.addWidget(QLabel("Private Key:"), row, 0)
            self.fields['private_key'] = QLineEdit()
            self.fields['private_key'].setEchoMode(QLineEdit.Password)
            self.fields['private_key'].setPlaceholderText("0x...")
            fields_layout.addWidget(self.fields['private_key'], row, 1)
            row += 1
            
            if self.exchange_name == "lighter":
                fields_layout.addWidget(QLabel("Account/Key:"), row, 0)
                idx_layout = QHBoxLayout()
                self.fields['account_index'] = QSpinBox()
                self.fields['account_index'].setRange(0, 99)
                self.fields['account_index'].setValue(1)
                idx_layout.addWidget(self.fields['account_index'])
                self.fields['key_index'] = QSpinBox()
                self.fields['key_index'].setRange(0, 9)
                self.fields['key_index'].setValue(2)
                idx_layout.addWidget(self.fields['key_index'])
                fields_layout.addLayout(idx_layout, row, 1)
                row += 1
        
        layout.addLayout(fields_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        test_btn = QPushButton("연결 테스트")
        test_btn.setStyleSheet("""
            QPushButton {
                background: #26a69a;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1e8770; }
        """)
        test_btn.setToolTip("연결 테스트\nAPI 키가 유효한지 확인")
        test_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(test_btn)
        
        help_btn = QPushButton("API Guide")
        help_btn.setStyleSheet("""
            QPushButton {
                background: #7c4dff20;
                color: #7c4dff;
                padding: 10px 15px;
                border: 1px solid #7c4dff40;
                border-radius: 5px;
            }
            QPushButton:hover { background: #7c4dff40; }
        """)
        help_btn.setToolTip("API 발급 가이드\n거래소별 API 설정 방법")
        help_btn.clicked.connect(self._show_api_guide)
        btn_layout.addWidget(help_btn)
        
        layout.addLayout(btn_layout)
        
        # Apply styles
        for widget in self.findChildren(QLabel):
            if widget != self.status_label:
                widget.setStyleSheet("color: #787b86;")
        for widget in self.findChildren(QLineEdit):
            widget.setStyleSheet("background: #131722; color: white; border: 1px solid #2a2e3b; border-radius: 4px; padding: 8px;")
        for widget in self.findChildren(QSpinBox):
            widget.setStyleSheet("background: #131722; color: white; border: 1px solid #2a2e3b; border-radius: 4px; padding: 6px;")
        for widget in self.findChildren(QCheckBox):
            widget.setStyleSheet("color: white;")
    
    def _load_config(self):
        """Load config"""
        config = self.config.get(self.exchange_name, {})
        
        for key, widget in self.fields.items():
            val = config.get(key)
            if val is None:
                continue
            if isinstance(widget, QLineEdit):
                widget.setText(str(val))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(val))
    
    def get_config(self):
        """Return current config"""
        config = {}
        for key, widget in self.fields.items():
            if isinstance(widget, QLineEdit):
                config[key] = widget.text()
            elif isinstance(widget, QCheckBox):
                config[key] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                config[key] = widget.value()
        return config
    

    def _test_connection(self):
        """Test connection (Async)"""
        config = self.get_config()
        
        api_key = config.get('api_key') or config.get('private_key')
        secret = config.get('api_secret', '')
        
        if not api_key:
            QMessageBox.warning(self, t("common.error"), "Enter API key")
            return
            
        # UI 잠금 및 상태 표시
        btn = self.sender()
        if isinstance(btn, QPushButton):
            btn.setEnabled(False)
            original_text = btn.text()
            btn.setText("Connecting...")
            
        self.status_label.setText("연결 시도 중...")
        self.status_label.setStyleSheet("color: orange;")
        
        # 워커 생성 및 시작
        self.worker = ConnectionWorker(
            self.exchange_name,
            api_key,
            secret,
            config.get('testnet', False)
        )
        
        def on_finished(success, error_msg, balance_data):
            if isinstance(btn, QPushButton):
                btn.setEnabled(True)
                btn.setText(original_text)
            
            if success:
                msg = f"{self.exchange_name.upper()} connected!"
                if balance_data:
                    if "KRW" in balance_data:
                        msg += f"\n\nKRW Balance: {balance_data['KRW']:,.0f}"
                    elif "USDT" in balance_data:
                        msg += f"\n\nUSDT Balance: ${balance_data['USDT']:,.2f}"
                
                QMessageBox.information(self, "Connection Success", msg)
                self.status_label.setText("연결됨")
                self.status_label.setStyleSheet("color: #26a69a;")
            else:
                QMessageBox.warning(self, "Connection Failed", 
                    f"Check API keys\n\nError: {error_msg}")
                self.status_label.setText("연결 실패")
                self.status_label.setStyleSheet("color: #ef5350;")
                
            # 워커 정리
            self.worker.deleteLater()
            self.worker = None

        self.worker.finished.connect(on_finished)
        self.worker.start()
    
    def _show_api_guide(self):
        """API guide - 거래소별 상세 가이드"""
        info = EXCHANGE_INFO.get(self.exchange_name, {})
        api_url = info.get('api_url', '#')
        
        # 공통 헤더
        header_html = f"""
            <h2>{info.get('icon', '')} {self.exchange_name.upper()} API 올바른 설정법</h2>
            <p style='margin-left: 15px;'>
            <a href='{api_url}' style='color: #2196f3;'>{api_url}</a>
            <br><span style='color: #787b86;'>위 링크를 클릭하여 설정 페이지로 이동하세요.</span>
            </p>
        """
        
        # 거래소별 권한 가이드
        if self.exchange_name == 'bybit':
            perm_html = """
            <h3>✅ 권한 설정 (Permissions)</h3>
            <p style='margin-left: 15px; background: #2a2e3b; padding: 10px; border-radius: 5px;'>
            <b>1. API Key Permissions</b><br>
            ⭕ <b>Read-Write</b> <span style='color: #26a69a;'>[필수]</span><br>
            ❌ Read-Only <span style='color: #ef5350;'>[선택 금지]</span><br>
            <br>
            <b>2. 세부 권한 (Account Type별)</b><br>
            - <b>Unified Trading</b>(UTA): <b>Orders</b>, <b>Positions</b> 체크<br>
            - <b>Standard Account</b>: <b>Contract</b> > <b>Orders</b>, <b>Positions</b> 체크<br>
            </p>
            """
            
        elif self.exchange_name == 'binance':
            perm_html = """
            <h3>✅ 권한 설정 (Permissions)</h3>
            <p style='margin-left: 15px; background: #2a2e3b; padding: 10px; border-radius: 5px;'>
            <b>API Restrictions</b><br>
            ⭕ <b>Enable Reading</b> <span style='color: #26a69a;'>[기본]</span><br>
            ⭕ <b>Enable Futures</b> <span style='color: #26a69a;'>[필수]</span> (선물 거래용)<br>
            ⭕ <b>Enable Spot & Margin Trading</b> (현물 거래 시)<br>
            ❌ <b>Enable Withdrawals</b> <span style='color: #ef5350;'>[절대 금지]</span><br>
            <br>
            ※ 'Edit Restrictions' 버튼을 눌러야 체크 가능합니다.<br>
            </p>
            """

        elif self.exchange_name == 'okx':
            perm_html = """
            <h3>✅ 권한 설정 (Permissions)</h3>
            <p style='margin-left: 15px; background: #2a2e3b; padding: 10px; border-radius: 5px;'>
            <b>Permission</b><br>
            ⭕ <b>Read</b> <span style='color: #26a69a;'>[필수]</span><br>
            ⭕ <b>Trade</b> <span style='color: #26a69a;'>[필수]</span><br>
            ❌ <b>Withdraw</b> <span style='color: #ef5350;'>[절대 금지]</span><br>
            <br>
            <b>⚠️ Passphrase 주의</b><br>
            API 생성 시 입력한 <b>Passphrase</b>를 반드시 기억해두세요.<br>
            앱 설정 시 비밀번호와 함께 입력해야 합니다.<br>
            </p>
            """

        elif self.exchange_name == 'bitget':
            perm_html = """
            <h3>✅ 권한 설정 (Permissions)</h3>
            <p style='margin-left: 15px; background: #2a2e3b; padding: 10px; border-radius: 5px;'>
            <b>Permissions</b><br>
            ⭕ <b>Read-Write</b> <span style='color: #26a69a;'>[필수]</span><br>
            ⭕ <b>Futures - Orders</b> <span style='color: #26a69a;'>[필수]</span><br>
            ⭕ <b>Spot - Orders</b> (현물 사용 시)<br>
            <br>
            <b>⚠️ Passphrase 주의</b><br>
            Bitget은 API 생성 시 Passphrase 설정이 필수입니다.<br>
            </p>
            """

        elif self.exchange_name in ['upbit', 'bithumb']:
            perm_html = """
            <h3>✅ 권한 설정 (Permissions)</h3>
            <p style='margin-left: 15px; background: #2a2e3b; padding: 10px; border-radius: 5px;'>
            <b>권한 관리</b><br>
            ⭕ <b>자산조회</b> <span style='color: #26a69a;'>[필수]</span><br>
            ⭕ <b>주문조회</b> <span style='color: #26a69a;'>[필수]</span><br>
            ⭕ <b>주문하기</b> (또는 매수/매도) <span style='color: #26a69a;'>[필수]</span><br>
            ❌ <b>출금(Withdraw)</b> <span style='color: #ef5350;'>[체크 해제]</span><br>
            <br>
            <b>⚠️ IP 제한 권장</b><br>
            보안을 위해 사용하시는 PC의 IP 주소만 허용하는 것을 권장합니다.<br>
            </p>
            """
            
        else: # 기본
            perm_html = f"""
            <h3>✅ 권한 설정</h3>
            <ul style='margin-left: 15px;'>
            {''.join(f"<li>{p}</li>" for p in info.get('permissions', ['Read', 'Trade']))}
            </ul>
            """

        # 공통 하단 (키 저장)
        footer_html = """
        <h3>📝 키 저장 (Save Keys)</h3>
        <ul style='margin-left: 15px;'>
        <li>발급된 <b>API Key</b>와 <b>Secret Key</b>를 복사하세요.</li>
        <li>Secret Key는 창을 닫으면 다시 볼 수 없습니다.</li>
        <li>이 앱의 설정 화면에 정확히 붙여넣어 주세요.</li>
        </ul>
        """

        guide = header_html + perm_html + footer_html
        
        msg = QMessageBox(self)
        msg.setWindowTitle(f"API Guide - {self.exchange_name.upper()}")
        msg.setTextFormat(Qt.RichText)
        msg.setText(guide)
        msg.setMinimumWidth(500)
        msg.exec_()


class SettingsWidget(QWidget):
    """Settings Widget (Simplified version)"""
    
    def __init__(self):
        super().__init__()
        self.config = load_api_keys()
        self.exchange_cards = {}
        self.current_tier = 'FREE'  # 기본 등급
        self._load_license_info()
        self._init_ui()
    
    def _load_license_info(self):
        """라이선스 정보 로드"""
        try:
            if HAS_LICENSE_GUARD and get_license_guard:
                guard = get_license_guard()
                if guard:
                    self.current_tier = getattr(guard, 'tier', 'FREE').upper()
        except Exception as e:
            logger.debug(f"License info load failed: {e}")
            self.current_tier = 'FREE'
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("API Settings")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)
        
        desc = QLabel("Configure exchange API keys. Trading settings are in the Trading tab.")
        desc.setStyleSheet("color: #787b86; font-size: 12px;")
        layout.addWidget(desc)
        
        # ========== 라이선스 검증 섹션 (ADMIN 전용) ==========
        self._create_license_section(layout)
        
        # [HIDDEN] Telegram card - 나중에 다시 활성화 가능
        # self.telegram_card = TelegramCard()
        # self.telegram_card.setStyleSheet("""
        #     TelegramCard {
        #         background: #1a237e;
        #         border: 2px solid #5c6bc0;
        #         border-radius: 10px;
        #         padding: 15px;
        #     }
        # """)
        # self.telegram_card.setMinimumHeight(180)
        # layout.addWidget(self.telegram_card)
        self.telegram_card = None  # 비활성화

        # Language note (moved to header bar)
        lang_note = QLabel("💡 언어 설정은 상단 바에서 변경할 수 있습니다 / Language can be changed in the header bar")
        lang_note.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(lang_note)

        # Exchange selection
        exchange_select = QGroupBox(t("settings.exchanges", "Exchange Selection"))
        exchange_select.setStyleSheet("QGroupBox { color: white; border: 1px solid #2a2e3b; border-radius: 5px; padding: 10px; }")
        exchange_layout = QHBoxLayout(exchange_select)
        
        self.exchange_toggles = {}
        # 거래소 순서: Bybit (기준) 먼저, 나머지 알파벳순
        exchange_order = ['bybit'] + sorted([e for e in EXCHANGE_INFO.keys() if e != 'bybit'])
        
        for exchange in exchange_order:
            info = EXCHANGE_INFO[exchange]
            # Bybit은 "기준" 표시, 등록된 거래소는 ✓ 표시
            is_registered = exchange in self.config and self.config[exchange].get('api_key')
            
            if exchange.lower() == 'bybit':
                label = f"{info.get('icon', '')} BYBIT (Primary)"
            else:
                label = f"{info.get('icon', '')} {exchange.upper()}"
            
            if is_registered:
                label = f"✓ {label}"
            
            btn = QCheckBox(label)
            btn.setStyleSheet(f"color: {'#26a69a' if is_registered else '#787b86'}; font-weight: {'bold' if exchange.lower() == 'bybit' else 'normal'};")
            btn.toggled.connect(lambda checked, ex=exchange: self._toggle_exchange(ex, checked))
            exchange_layout.addWidget(btn)
            self.exchange_toggles[exchange] = btn
        
        layout.addWidget(exchange_select)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(15)
        
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)
        
        # Save button
        save_btn = QPushButton("Save All Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #26a69a;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #1e8770; }
        """)
        save_btn.clicked.connect(self._save_all)
        layout.addWidget(save_btn)
        
        # Restore existing config
        for exchange in self.config.keys():
            if exchange in self.exchange_toggles:
                self.exchange_toggles[exchange].setChecked(True)
    
    def _toggle_exchange(self, exchange, checked):
        """Toggle exchange card display"""
        if checked:
            if exchange not in self.exchange_cards:
                card = ExchangeCard(exchange, self.config)
                self.exchange_cards[exchange] = card
            self._relayout_cards()
        else:
            if exchange in self.exchange_cards:
                self.exchange_cards[exchange].hide()
            self._relayout_cards()
    
    def _relayout_cards(self):
        """Relayout cards"""
        # Remove existing widgets
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Add visible cards
        visible = []
        for exchange, card in self.exchange_cards.items():
            toggle = self.exchange_toggles.get(exchange)
            if toggle and toggle.isChecked():
                visible.append(card)
        
        for i, card in enumerate(visible):
            row, col = divmod(i, 2)
            self.cards_layout.addWidget(card, row, col)
            card.show()
    
    def _save_all(self):
        """Save all settings"""
        if self.telegram_card:
            self.telegram_card.save_config()
        
        # Preserve unchecked exchange configs
        config = load_api_keys() or {}
        
        for exchange, card in self.exchange_cards.items():
            toggle = self.exchange_toggles.get(exchange)
            if toggle and toggle.isChecked():
                config[exchange] = card.get_config()
        
        try:
            save_api_keys(config)
            QMessageBox.information(self, t("common.success", t("common.success")), t("message.save_success", "All settings saved!"))
        except Exception as e:
            QMessageBox.critical(self, t("common.error", t("common.error")), f"Save failed: {e}")
    
    def _on_language_changed(self, index):
        """언어 변경 핸들러"""
        # [FIX] lang_combo 미정의 시 안전 체크
        if not hasattr(self, 'lang_combo'):
            return
        lang_code = self.lang_combo.currentData()
        if lang_code:
            set_language(lang_code)
            
            # 재시작 안내
            QMessageBox.information(
                self,
                t("common.success", t("common.success")),
                "Language changed. Please restart the application.\n언어가 변경되었습니다. 프로그램을 재시작해주세요."
            )
    
    # ==================== 라이선스 검증 섹션 (ADMIN 전용) ====================
    
    def _create_license_section(self, layout):
        """라이선스 검증 섹션 생성 - ADMIN 등급에서만 표시"""
        # ADMIN 등급이 아니면 표시하지 않음
        if self.current_tier != 'ADMIN':
            return
        
        # 라이선스 검증 그룹박스
        license_group = QGroupBox("👑 관리자 전용 - 라이선스 검증")
        license_group.setStyleSheet("""
            QGroupBox {
                color: #e91e63;
                border: 2px solid #e91e63;
                border-radius: 8px;
                padding: 15px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)
        
        group_layout = QVBoxLayout(license_group)
        group_layout.setSpacing(10)
        
        # 설명
        desc = QLabel("사용자 라이선스 코드를 검증하고 등급을 부여합니다.")
        desc.setStyleSheet("color: #787b86; font-size: 11px;")
        group_layout.addWidget(desc)
        
        # 입력 영역
        input_layout = QHBoxLayout()
        
        # 검증 코드 입력
        self.license_code_input = QLineEdit()
        self.license_code_input.setPlaceholderText("검증할 라이선스 코드 입력...")
        self.license_code_input.setStyleSheet("""
            QLineEdit {
                background: #131722;
                color: white;
                border: 1px solid #e91e63;
                border-radius: 5px;
                padding: 10px;
                font-family: monospace;
            }
            QLineEdit:focus {
                border: 2px solid #e91e63;
            }
        """)
        input_layout.addWidget(self.license_code_input, stretch=3)
        
        # 등급 선택
        self.tier_combo = QComboBox()
        self.tier_combo.addItems(['TRIAL', 'BASIC', 'STANDARD', 'PREMIUM', 'ADMIN'])
        self.tier_combo.setCurrentText('BASIC')
        self.tier_combo.setStyleSheet("""
            QComboBox {
                background: #131722;
                color: white;
                border: 1px solid #2a2e3b;
                border-radius: 5px;
                padding: 8px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #1e2330;
                color: white;
                selection-background-color: #e91e63;
            }
        """)
        input_layout.addWidget(self.tier_combo, stretch=1)
        
        # 검증 버튼
        verify_btn = QPushButton("🔐 검증 및 등급 부여")
        verify_btn.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #e91e63, #9c27b0);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #c2185b, #7b1fa2);
            }
            QPushButton:pressed {
                background: #880e4f;
            }
        """)
        verify_btn.clicked.connect(self._verify_license_code)
        input_layout.addWidget(verify_btn)
        
        group_layout.addLayout(input_layout)
        
        # 결과 표시 영역
        self.license_result_label = QLabel("")
        self.license_result_label.setStyleSheet("color: #787b86; padding: 5px;")
        self.license_result_label.setWordWrap(True)
        group_layout.addWidget(self.license_result_label)
        
        # 최근 검증 내역 (간단히)
        history_label = QLabel("💡 검증된 코드는 서버에 기록되며, 해당 사용자에게 등급이 자동 적용됩니다.")
        history_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        group_layout.addWidget(history_label)
        
        layout.addWidget(license_group)
    
    def _verify_license_code(self):
        """라이선스 코드 검증 및 등급 부여"""
        code = self.license_code_input.text().strip()
        tier = self.tier_combo.currentText()
        
        if not code:
            QMessageBox.warning(self, "입력 오류", "검증할 라이선스 코드를 입력하세요.")
            return
        
        # 코드 형식 검증 (예: 16자 이상의 영숫자)
        if len(code) < 8:
            QMessageBox.warning(self, "형식 오류", "라이선스 코드는 최소 8자 이상이어야 합니다.")
            return
        
        try:
            # 실제 검증 로직 (서버 API 호출)
            result = self._call_license_api(code, tier)
            
            if result.get('success'):
                self.license_result_label.setText(
                    f"✅ 검증 성공!\n"
                    f"코드: {code[:8]}...{code[-4:]}\n"
                    f"부여 등급: {tier}\n"
                    f"처리 시간: {result.get('timestamp', 'N/A')}"
                )
                self.license_result_label.setStyleSheet("color: #26a69a; padding: 5px; background: #1a2e2a; border-radius: 5px;")
                
                QMessageBox.information(
                    self, 
                    "검증 완료", 
                    f"라이선스 코드가 성공적으로 검증되었습니다.\n\n"
                    f"코드: {code[:8]}***\n"
                    f"등급: {tier}\n\n"
                    f"해당 사용자에게 등급이 적용됩니다."
                )
                
                # 입력 필드 초기화
                self.license_code_input.clear()
            else:
                error_msg = result.get('error', '알 수 없는 오류')
                self.license_result_label.setText(f"❌ 검증 실패: {error_msg}")
                self.license_result_label.setStyleSheet("color: #ef5350; padding: 5px;")
                QMessageBox.warning(self, "검증 실패", f"라이선스 검증에 실패했습니다.\n\n오류: {error_msg}")
                
        except Exception as e:
            self.license_result_label.setText(f"❌ 오류 발생: {str(e)}")
            self.license_result_label.setStyleSheet("color: #ef5350; padding: 5px;")
            QMessageBox.critical(self, "오류", f"검증 중 오류가 발생했습니다.\n\n{str(e)}")
    
    def _call_license_api(self, code: str, tier: str) -> dict:
        """라이선스 서버 API 호출"""
        import datetime
        
        try:
            # 실제 서버 연동 시 여기에 API 호출 코드 작성
            # 현재는 로컬 시뮬레이션
            
            if HAS_LICENSE_GUARD and get_license_guard:
                guard = get_license_guard()
                if guard and hasattr(guard, 'verify_admin_code'):
                    return guard.verify_admin_code(code, tier)
            
            # 시뮬레이션 응답 (실제 서버 연동 전)
            # 테스트용: 'ADMIN' 또는 'TEST'로 시작하는 코드는 성공
            if code.upper().startswith(('ADMIN', 'TEST', 'VALID')):
                return {
                    'success': True,
                    'code': code,
                    'tier': tier,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'등급 {tier} 부여 완료'
                }
            else:
                return {
                    'success': False,
                    'error': '유효하지 않은 라이선스 코드입니다.'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _show_tier_comparison(self):
        """등급 비교표 다이얼로그 표시"""
        try:
            from license_tiers import LICENSE_TIERS
            
            # 비교표 다이얼로그 생성
            from PyQt5.QtWidgets import QDialog, QTextEdit
            dlg = QDialog(self)
            dlg.setWindowTitle("📊 등급 비교표")
            dlg.setMinimumSize(600, 500)
            dlg.setStyleSheet("background: #1a1a2e; color: white;")
            
            layout = QVBoxLayout(dlg)
            
            # 등급 정보 텍스트
            info_text = QTextEdit()
            info_text.setReadOnly(True)
            info_text.setStyleSheet("""
                QTextEdit {
                    background: #0d1117; 
                    color: #d1d4dc; 
                    border: 1px solid #333; 
                    border-radius: 5px;
                    font-family: 'Consolas', 'Malgun Gothic', monospace;
                    font-size: 12px;
                    padding: 10px;
                }
            """)
            
            # 비교표 생성
            html = """
            <style>
                table { border-collapse: collapse; width: 100%; }
                th { background: #2962ff; color: white; padding: 10px; }
                td { padding: 8px; border-bottom: 1px solid #333; }
                .tier-free { color: #888; }
                .tier-basic { color: #4fc3f7; }
                .tier-standard { color: #66bb6a; }
                .tier-premium { color: #ffd54f; }
            </style>
            <h2>🏷️ TwinStar Quantum 등급표</h2>
            <table>
                <tr>
                    <th>등급</th>
                    <th>라이선스비</th>
                    <th>월 구독료</th>
                    <th>코인</th>
                    <th>거래소</th>
                    <th>동시 포지션</th>
                </tr>
            """
            
            for key, tier in LICENSE_TIERS.items():
                html += f"""
                <tr>
                    <td class="tier-{key}"><b>{tier.name}</b></td>
                    <td>${tier.license_fee}</td>
                    <td>${tier.price_monthly}/월</td>
                    <td>{len(tier.coins) if '*' not in tier.coins else '무제한'}개</td>
                    <td>{len(tier.exchanges) if '*' not in tier.exchanges else '전체'}개</td>
                    <td>{tier.max_positions}개</td>
                </tr>
                """
            
            html += "</table>"
            html += "<br><h3>💡 등급별 특징</h3><ul>"
            
            for key, tier in LICENSE_TIERS.items():
                html += f"<li><b>{tier.name}</b>: {tier.description}<br>"
                html += f"<small>코인: {', '.join(tier.coins[:5])}{'...' if len(tier.coins) > 5 else ''}</small></li>"
            
            html += "</ul>"
            
            info_text.setHtml(html)
            layout.addWidget(info_text)
            
            # 닫기 버튼
            close_btn = QPushButton("닫기")
            close_btn.setStyleSheet("background: #424242; color: white; padding: 10px; border: none; border-radius: 5px;")
            close_btn.clicked.connect(dlg.accept)
            layout.addWidget(close_btn)
            
            dlg.exec_()
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"등급 비교표 로드 실패: {e}")
    
    def _show_payment_dialog(self):
        """결제 다이얼로그 표시 - License Guard 사용"""
        try:
            # [NEW] License Guard로 업그레이드 세션 생성
            if HAS_LICENSE_GUARD and get_license_guard:
                guard = get_license_guard()
                result = guard.create_upgrade_session()
                
                if result.get('success'):
                    url = result.get('url')
                    webbrowser.open(url)
                    
                    QMessageBox.information(
                        self,
                        "업그레이드",
                        "웹 브라우저에서 결제를 완료한 후\n"
                        "프로그램을 재시작해주세요.\n\n"
                        f"URL: {url[:50]}..."
                    )
                else:
                    error = result.get('error', '세션 생성 실패')
                    QMessageBox.warning(self, "오류", f"업그레이드 실패: {error}")
            else:
                # Fallback: 기존 PaymentDialog 사용
                from license_manager import get_license_manager
                try:
                    from GUI.payment_dialog import PaymentDialog
                except ImportError:
                    from payment_dialog import PaymentDialog
                
                lm = get_license_manager()
                dlg = PaymentDialog(lm, self)
                dlg.exec_()
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"결제 다이얼로그 오류: {e}")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background: #0d1117; }")
    
    w = SettingsWidget()
    w.resize(800, 600)
    w.show()
    sys.exit(app.exec_())
