# E:/trading/gui/strategy_selector_widget.py
"""
전략 선택 위젯
- 전략 목록 표시
- 티어별 필터링
- 전략 정보 카드
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFrame, QGridLayout,
    QGroupBox, QScrollArea
)

# Logging
import logging
logger = logging.getLogger(__name__)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.strategy_loader import StrategyLoader, StrategyInfo


class StrategyCard(QFrame):
    """전략 정보 카드"""
    
    selected = pyqtSignal(str)  # strategy_id
    
    def __init__(self, strategy_info: StrategyInfo, strategy_config=None):
        super().__init__()
        self._info = strategy_info
        self._config = strategy_config
        self._is_selected = False
        self._init_ui()
    
    def _init_ui(self):
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setStyleSheet("""
            StrategyCard {
                background-color: #2d2d2d;
                border: 2px solid #404040;
                border-radius: 8px;
                padding: 10px;
            }
            StrategyCard:hover {
                border-color: #4CAF50;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 전략명 + 버전
        header = QHBoxLayout()
        
        name_label = QLabel(self._info.name)
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        name_label.setStyleSheet("color: #ffffff;")
        header.addWidget(name_label)
        
        version_label = QLabel(f"v{self._info.version}")
        version_label.setStyleSheet("color: #888888;")
        header.addWidget(version_label)
        header.addStretch()
        
        # 티어 배지
        tier_label = QLabel(self._info.tier_required.upper())
        tier_colors = {
            "free": "#4CAF50",
            "basic": "#2196F3",
            "pro": "#FF9800",
            "vip": "#9C27B0"
        }
        tier_color = tier_colors.get(self._info.tier_required, "#666666")
        tier_label.setStyleSheet(f"""
            background-color: {tier_color};
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
        """)
        header.addWidget(tier_label)
        
        layout.addLayout(header)
        
        # 성능 지표 (config에서 가져옴)
        if self._config:
            stats_layout = QGridLayout()
            stats_layout.setSpacing(4)
            
            stats = [
                ("승률", f"{self._config.win_rate}%"),
                ("TF", self._config.timeframe),
                ("MDD", f"{self._config.max_drawdown}%"),
                ("PF", f"{self._config.profit_factor}")
            ]
            
            for i, (label, value) in enumerate(stats):
                lbl = QLabel(label)
                lbl.setStyleSheet("color: #888888; font-size: 11px;")
                val = QLabel(value)
                val.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: bold;")
                
                stats_layout.addWidget(lbl, i // 2, (i % 2) * 2)
                stats_layout.addWidget(val, i // 2, (i % 2) * 2 + 1)
            
            layout.addLayout(stats_layout)
        
        # 설명
        if self._config and self._config.description:
            desc = QLabel(self._config.description[:50] + "...")
            desc.setStyleSheet("color: #aaaaaa; font-size: 10px;")
            desc.setWordWrap(True)
            layout.addWidget(desc)
    
    def mousePressEvent(self, event):
        self.selected.emit(self._info.id)
        super().mousePressEvent(event)
    
    def set_selected(self, selected: bool):
        self._is_selected = selected
        if selected:
            self.setStyleSheet("""
                StrategyCard {
                    background-color: #1e3a1e;
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                StrategyCard {
                    background-color: #2d2d2d;
                    border: 2px solid #404040;
                    border-radius: 8px;
                }
                StrategyCard:hover {
                    border-color: #4CAF50;
                }
            """)


class StrategySelectorWidget(QWidget):
    """전략 선택 위젯"""
    
    strategy_selected = pyqtSignal(str, object)  # strategy_id, strategy_instance
    
    def __init__(self, user_tier: str = "basic"):
        super().__init__()
        self._user_tier = user_tier
        self._loader = StrategyLoader()
        self._cards: dict = {}
        self._selected_id: str = None
        self._selected_strategy = None
        self._init_ui()
        self._load_strategies()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 헤더
        header = QHBoxLayout()
        
        title = QLabel("📊 전략 선택")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        
        header.addStretch()
        
        # 티어 필터
        header.addWidget(QLabel("티어:"))
        self._tier_combo = QComboBox()
        self._tier_combo.addItems(["전체", "Free", "Basic", "Pro", "VIP"])
        self._tier_combo.setCurrentText(self._user_tier.capitalize())
        self._tier_combo.currentTextChanged.connect(self._filter_strategies)
        self._tier_combo.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                padding: 5px;
                border-radius: 4px;
            }
        """)
        header.addWidget(self._tier_combo)
        
        layout.addLayout(header)
        
        # 전략 카드 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setSpacing(10)
        self._cards_layout.addStretch()
        
        scroll.setWidget(self._cards_widget)
        layout.addWidget(scroll)
        
        # 선택된 전략 정보
        self._info_group = QGroupBox("선택된 전략")
        self._info_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        info_layout = QVBoxLayout(self._info_group)
        
        self._selected_label = QLabel("전략을 선택하세요")
        self._selected_label.setStyleSheet("color: #aaaaaa;")
        info_layout.addWidget(self._selected_label)
        
        layout.addWidget(self._info_group)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        self._load_btn = QPushButton("✅ 전략 로드")
        self._load_btn.setEnabled(False)
        self._load_btn.clicked.connect(self._load_selected_strategy)
        self._load_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(self._load_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_strategies(self):
        """전략 목록 로드"""
        strategies = []
        for sid in self._loader.list_all():
            info = self._loader.get_strategy_info(sid)
            if info:
                strategies.append(info)
        
        for info in strategies:
            # 전략 인스턴스 로드하여 config 가져오기
            strategy = self._loader.load_strategy(info.strategy_id)
            config = strategy.get_config() if strategy else None
            
            card = StrategyCard(info, config)
            card.selected.connect(self._on_card_selected)
            
            self._cards[info.strategy_id] = card
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
    
    def _filter_strategies(self, tier_text: str):
        """티어 필터링"""
        filter_tier = tier_text.lower() if tier_text != "전체" else None
        
        for strategy_id, card in self._cards.items():
            info = self._loader.get_strategy_info(strategy_id)
            if filter_tier is None:
                card.show()
            elif info.tier_required == filter_tier:
                card.show()
            else:
                card.hide()
    
    def _on_card_selected(self, strategy_id: str):
        """카드 선택"""
        # 이전 선택 해제
        if self._selected_id and self._selected_id in self._cards:
            self._cards[self._selected_id].set_selected(False)
        
        # 새 선택
        self._selected_id = strategy_id
        self._cards[strategy_id].set_selected(True)
        
        # 정보 업데이트
        info = self._loader.get_strategy_info(strategy_id)
        self._selected_label.setText(f"✅ {info.name} (v{info.version})")
        self._selected_label.setStyleSheet("color: #4CAF50;")
        
        self._load_btn.setEnabled(True)
    
    def _load_selected_strategy(self):
        """선택된 전략 로드"""
        if not self._selected_id:
            return
        
        strategy = self._loader.load_strategy(self._selected_id)
        if strategy:
            self._selected_strategy = strategy
            self.strategy_selected.emit(self._selected_id, strategy)
    
    def get_selected_strategy(self):
        """현재 선택된 전략 반환"""
        return self._selected_strategy
    
    def set_user_tier(self, tier: str):
        """유저 티어 설정"""
        self._user_tier = tier
        self._tier_combo.setCurrentText(tier.capitalize())


# ============== 테스트 ==============
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 다크 테마
    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
        }
    """)
    
    widget = StrategySelectorWidget(user_tier="basic")
    widget.setWindowTitle("전략 선택")
    widget.resize(400, 500)
    
    def on_strategy_selected(sid, strategy):
        logger.info(f"선택됨: {sid}")
        config = strategy.get_config()
        logger.info(f"  - 이름: {config.name}")
        logger.info(f"  - TF: {config.timeframe}")
        logger.info(f"  - 승률: {config.win_rate}%")
    
    widget.strategy_selected.connect(on_strategy_selected)
    widget.show()
    
    sys.exit(app.exec_())
