"""
TwinStar Quantum - Message Dialogs
==================================

메시지 및 확인 다이얼로그
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

from .base import BaseDialog

# 디자인 시스템
try:
    from ui.design_system import Colors
except ImportError:
    class Colors:
        success = "#3fb950"
        danger = "#f85149"
        warning = "#d29922"
        info = "#58a6ff"
        text_primary = "#f0f6fc"


class MessageDialog(BaseDialog):
    """
    메시지 다이얼로그
    
    정보, 성공, 경고, 에러 메시지 표시
    
    사용법:
        MessageDialog.info("작업이 완료되었습니다.")
        MessageDialog.success("저장되었습니다!")
        MessageDialog.warning("주의가 필요합니다.")
        MessageDialog.error("오류가 발생했습니다.")
    """
    
    ICONS = {
        "info": ("ℹ️", Colors.info),
        "success": ("✅", Colors.success),
        "warning": ("⚠️", Colors.warning),
        "error": ("❌", Colors.danger),
    }
    
    def __init__(
        self, 
        message: str,
        msg_type: str = "info",
        title: str = None,
        parent=None
    ):
        icon, color = self.ICONS.get(msg_type, self.ICONS["info"])
        
        if title is None:
            title = msg_type.capitalize()
        
        super().__init__(title, parent=parent)
        
        self._build_content(message, icon, color)
        self._add_buttons()
    
    def _build_content(self, message: str, icon: str, color: str):
        """콘텐츠 구성"""
        # 아이콘
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(icon_label)
        
        # 메시지
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setStyleSheet(f"""
            font-size: 14px;
            color: {Colors.text_primary};
            padding: 10px;
        """)
        self.content_layout.addWidget(msg_label)
    
    def _add_buttons(self):
        """버튼 추가"""
        self.add_stretch()
        self.add_button("확인", variant="primary")
    
    @classmethod
    def show(cls, message: str, msg_type: str = "info", title: str = None, parent=None):
        """다이얼로그 표시"""
        dialog = cls(message, msg_type, title, parent)
        return dialog.exec_()
    
    @classmethod
    def info(cls, message: str, parent=None):
        """정보 메시지"""
        return cls.show(message, "info", "알림", parent)
    
    @classmethod
    def success(cls, message: str, parent=None):
        """성공 메시지"""
        return cls.show(message, "success", "완료", parent)
    
    @classmethod
    def warning(cls, message: str, parent=None):
        """경고 메시지"""
        return cls.show(message, "warning", "경고", parent)
    
    @classmethod
    def error(cls, message: str, parent=None):
        """에러 메시지"""
        return cls.show(message, "error", "오류", parent)


class ConfirmDialog(BaseDialog):
    """
    확인 다이얼로그
    
    예/아니오 선택
    
    사용법:
        if ConfirmDialog.ask("정말 삭제하시겠습니까?"):
            do_delete()
    """
    
    def __init__(
        self, 
        message: str,
        title: str = "확인",
        yes_text: str = "예",
        no_text: str = "아니오",
        dangerous: bool = False,
        parent=None
    ):
        super().__init__(title, parent=parent)
        
        self._result = False
        self._dangerous = dangerous
        
        self._build_content(message)
        self._add_buttons(yes_text, no_text)
    
    def _build_content(self, message: str):
        """콘텐츠 구성"""
        # 아이콘
        icon = "⚠️" if self._dangerous else "❓"
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(icon_label)
        
        # 메시지
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setStyleSheet(f"""
            font-size: 14px;
            color: {Colors.text_primary};
            padding: 10px;
        """)
        self.content_layout.addWidget(msg_label)
    
    def _add_buttons(self, yes_text: str, no_text: str):
        """버튼 추가"""
        self.add_stretch()
        
        # 아니오 버튼
        self.add_button(no_text, self._on_no, "secondary", close_on_click=False)
        
        # 예 버튼
        variant = "danger" if self._dangerous else "primary"
        self.add_button(yes_text, self._on_yes, variant, close_on_click=False)
    
    def _on_yes(self):
        """예 클릭"""
        self._result = True
        self.accept()
    
    def _on_no(self):
        """아니오 클릭"""
        self._result = False
        self.reject()
    
    def result(self) -> bool:
        """결과 반환"""
        return self._result
    
    @classmethod
    def ask(
        cls, 
        message: str, 
        title: str = "확인",
        yes_text: str = "예",
        no_text: str = "아니오",
        dangerous: bool = False,
        parent=None
    ) -> bool:
        """확인 질문"""
        dialog = cls(message, title, yes_text, no_text, dangerous, parent)
        dialog.exec_()
        return dialog.result()
    
    @classmethod
    def delete(cls, message: str = "정말 삭제하시겠습니까?", parent=None) -> bool:
        """삭제 확인 (위험 스타일)"""
        return cls.ask(message, "삭제 확인", "삭제", "취소", dangerous=True, parent=parent)
