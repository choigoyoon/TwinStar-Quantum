# cache_manager_widget.py

from locales.lang_manager import t
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)

# Logging
import logging
logger = logging.getLogger(__name__)
import os

from GUI.data_cache import DataManager


class CacheManagerWidget(QWidget):
    """캐시 관리 위젯"""
    
    def __init__(self):
        super().__init__()
        self.dm = DataManager()
        self.init_ui()
        self.load_cache_list()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 1. 헤더 및 통계
        header_layout = QHBoxLayout()
        self.lbl_total_size = QLabel("총 용량: 0 MB")
        self.lbl_total_size.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffd700;")
        
        self.btn_refresh = QPushButton("🔄 새로고침")
        self.btn_refresh.clicked.connect(self.load_cache_list)
        
        header_layout.addWidget(self.lbl_total_size)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)
        
        # 2. 캐시 목록 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "거래소", "코인", "시간봉", "기간", "개수", "용량 (MB)", "액션"
        ])
        
        # 헤더 스타일
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Symbol
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Range
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117;
                gridline-color: #30363d;
            }
            QHeaderView::section {
                background-color: #161b22;
                padding: 5px;
                border: 1px solid #30363d;
            }
        """)
        
        layout.addWidget(self.table)
        
        # 3. 하단 버튼
        btn_layout = QHBoxLayout()
        
        self.btn_delete_all = QPushButton("🗑️ 전체 캐시 삭제")
        self.btn_delete_all.setStyleSheet("background-color: #da3633; color: white;")
        self.btn_delete_all.clicked.connect(self.delete_all_caches)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_delete_all)
        layout.addLayout(btn_layout)
        
    def load_cache_list(self):
        """캐시 목록 로드"""
        self.table.setRowCount(0)
        caches = self.dm.get_all_cache_list()
        
        total_size = 0
        
        for i, info in enumerate(caches):
            self.table.insertRow(i)
            
            # Exchange
            self.table.setItem(i, 0, QTableWidgetItem(info.get('exchange', '-')))
            
            # Symbol
            self.table.setItem(i, 1, QTableWidgetItem(info.get('symbol', '-')))
            
            # Timeframe
            self.table.setItem(i, 2, QTableWidgetItem(info.get('timeframe', '-')))
            
            # Range
            range_str = f"{info.get('first_date', '-')} ~ {info.get('last_date', '-')}"
            self.table.setItem(i, 3, QTableWidgetItem(range_str))
            
            # Count
            count = info.get('count', 0)
            self.table.setItem(i, 4, QTableWidgetItem(f"{count:,}"))
            
            # Size
            size = info.get('file_size', 0)
            total_size += size
            self.table.setItem(i, 5, QTableWidgetItem(f"{size:.2f} MB"))
            
            # Action (Delete Button)
            btn_del = QPushButton("🗑️")
            btn_del.setFixedWidth(40)
            btn_del.setStyleSheet("background-color: #da3633; color: white; border-radius: 4px;")
            # 클로저 문제 해결을 위해 별도 메서드 연결 또는 lambda with default arg 사용
            btn_del.clicked.connect(lambda checked, row=i, fname=info.get('filename'): self.delete_cache(row, fname))
            
            # 셀 위젯으로 추가
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.addWidget(btn_del)
            self.table.setCellWidget(i, 6, container)
            
        self.lbl_total_size.setText(f"Total Size: {total_size:.2f} MB")
        
    def delete_cache(self, row, filename):
        """개별 캐시 삭제"""
        reply = QMessageBox.question(
            self, '삭제 확인',
            f"{filename} 파일을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                path = self.dm.CACHE_DIR / filename
                if path.exists():
                    os.remove(path)
                    logger.info(f"Deleted {filename}")
                    self.load_cache_list() # 목록 갱신
            except Exception as e:
                QMessageBox.critical(self, t("common.error"), f"Failed to delete: {e}")
                
    def delete_all_caches(self):
        """전체 캐시 삭제"""
        reply = QMessageBox.question(
            self, 'Confirm Delete All',
            "Are you sure you want to delete ALL cache files?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for cache_file in self.dm.CACHE_DIR.glob("*.parquet"):
                    os.remove(cache_file)
                
                QMessageBox.information(self, t("common.success"), "All cache files deleted.")
                self.load_cache_list()
            except Exception as e:
                QMessageBox.critical(self, t("common.error"), f"Failed to delete all: {e}")

# 테스트
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = CacheManagerWidget()
    window.setWindowTitle("Cache Manager")
    window.resize(800, 500)
    window.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
    window.show()
    
    sys.exit(app.exec())
