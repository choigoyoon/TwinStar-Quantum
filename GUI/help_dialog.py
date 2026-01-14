"""
통합 도움말 다이얼로그
- 사용법
- 거래소별 매매법
- 레퍼럴 링크
- FAQ
"""

import sys
import os
import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QTextBrowser, QScrollArea, QGroupBox
)
from PyQt6.QtCore import Qt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class HelpDialog(QDialog):
    """통합 도움말 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle("📚 TwinStar Quantum 도움말")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog { background: #131722; }
            QLabel { color: white; }
            QTabWidget::pane { background: #131722; border: 1px solid #2a2e3b; }
            QTabBar::tab { 
                background: #1e2330; 
                color: white; 
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected { background: #2962FF; }
            QTextBrowser { 
                background: #1e2330; 
                color: #d1d4dc; 
                border: none; 
                padding: 15px;
                font-family: 'Malgun Gothic', 'Arial';
            }
            QPushButton {
                background: #2962FF;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background: #1e88e5; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 탭 위젯
        tabs = QTabWidget()
        
        # 1. 빠른 시작
        tabs.addTab(self._create_quick_start_tab(), "🚀 빠른 시작")
        
        # 2. 거래소별 매매법
        tabs.addTab(self._create_trading_methods_tab(), "📈 매매법")
        
        # 3. 레퍼럴
        tabs.addTab(self._create_referral_tab(), "🎁 가입 혜택")
        
        # 4. FAQ
        tabs.addTab(self._create_faq_tab(), "❓ FAQ")
        
        layout.addWidget(tabs)
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def _create_quick_start_tab(self) -> QWidget:
        """빠른 시작 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        try:
            from user_guide import get_quick_start
            content = get_quick_start()
        except ImportError:
            content = "사용법 정보를 불러올 수 없습니다."
        
        browser = QTextBrowser()
        browser.setText(content)
        layout.addWidget(browser)
        
        return widget
    
    def _create_trading_methods_tab(self) -> QWidget:
        """매매법 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 선물/현물 선택 버튼
        btn_layout = QHBoxLayout()
        
        futures_btn = QPushButton("📊 선물 매매 (Bybit/Binance)")
        futures_btn.clicked.connect(lambda: self._show_method("futures"))
        btn_layout.addWidget(futures_btn)
        
        spot_btn = QPushButton("🇰🇷 현물 매매 (업비트/빗썸)")
        spot_btn.setStyleSheet("background: #26a69a;")
        spot_btn.clicked.connect(lambda: self._show_method("spot"))
        btn_layout.addWidget(spot_btn)
        
        layout.addLayout(btn_layout)
        
        # 내용
        self.method_browser = QTextBrowser()
        
        try:
            from user_guide import get_trading_method
            content = get_trading_method("futures").get("strategy", "")
        except ImportError:
            content = "매매법 정보를 불러올 수 없습니다."
        
        self.method_browser.setText(content)
        layout.addWidget(self.method_browser)
        
        return widget
    
    def _show_method(self, method_type: str):
        """매매법 표시"""
        try:
            from user_guide import get_trading_method
            content = get_trading_method(method_type).get("strategy", "")
            self.method_browser.setText(content)
        except Exception as e:
            self.method_browser.setText(f"오류: {e}")
    
    def _create_referral_tab(self) -> QWidget:
        """레퍼럴 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        try:
            from referral_links import REFERRAL_LINKS
            
            for exchange, info in REFERRAL_LINKS.items():
                group = QGroupBox(f"{info.get('guide', exchange).split(chr(10))[0]}")
                group.setStyleSheet("""
                    QGroupBox {
                        color: white;
                        font-weight: bold;
                        border: 1px solid #2a2e3b;
                        border-radius: 8px;
                        margin-top: 15px;
                        padding: 15px;
                    }
                """)
                group_layout = QVBoxLayout(group)
                
                # 혜택
                benefits = info.get("benefits", [])
                benefits_text = "\n".join([f"✅ {b}" for b in benefits])
                benefits_label = QLabel(benefits_text)
                benefits_label.setStyleSheet("color: #26a69a;")
                group_layout.addWidget(benefits_label)
                
                # 가이드
                guide = info.get("guide", "")
                guide_label = QLabel(guide)
                guide_label.setWordWrap(True)
                guide_label.setStyleSheet("color: #d1d4dc; font-size: 12px;")
                group_layout.addWidget(guide_label)
                
                # 링크 버튼
                link = info.get("link", "")
                if link and "YOUR_REF_CODE" not in link:
                    link_btn = QPushButton(f"🔗 {exchange.upper()} 가입하기")
                    link_btn.clicked.connect(lambda checked, url=link: webbrowser.open(url))
                    group_layout.addWidget(link_btn)
                
                scroll_layout.addWidget(group)
            
        except Exception as e:
            error_label = QLabel(f"레퍼럴 정보를 불러올 수 없습니다: {e}")
            scroll_layout.addWidget(error_label)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_faq_tab(self) -> QWidget:
        """FAQ 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        try:
            from user_guide import get_faq
            content = get_faq()
        except ImportError:
            content = "FAQ 정보를 불러올 수 없습니다."
        
        browser = QTextBrowser()
        browser.setText(content)
        layout.addWidget(browser)
        
        return widget


# 테스트
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = HelpDialog()
    dialog.show()
    sys.exit(app.exec())
