"""
TwinStar Quantum - Dialog Styles
================================

다이얼로그 컴포넌트 스타일
"""

from ..tokens import Colors, Typography, Spacing, Radius


class DialogStyles:
    """
    다이얼로그 스타일 생성기
    
    사용법:
        dialog.setStyleSheet(DialogStyles.default())
        dialog.setStyleSheet(DialogStyles.compact())
    """
    
    @staticmethod
    def default() -> str:
        """기본 다이얼로그 스타일"""
        return f"""
            QDialog {{
                background-color: {Colors.bg_base};
                color: {Colors.text_primary};
            }}
            
            /* 다이얼로그 제목 */
            QDialog QLabel#dialog-title {{
                font-size: {Typography.text_xl};
                font-weight: {Typography.font_bold};
                color: {Colors.text_primary};
                margin-bottom: {Spacing.space_4};
            }}
            
            /* 다이얼로그 설명 */
            QDialog QLabel#dialog-description {{
                font-size: {Typography.text_base};
                color: {Colors.text_secondary};
                margin-bottom: {Spacing.space_4};
            }}
            
            /* 다이얼로그 버튼 영역 */
            QDialogButtonBox {{
                padding: {Spacing.space_4} 0;
            }}
            
            QDialogButtonBox QPushButton {{
                min-width: 80px;
                padding: {Spacing.space_2} {Spacing.space_4};
            }}
        """
    
    @staticmethod
    def modal() -> str:
        """모달 다이얼로그 (중앙 정렬)"""
        return f"""
            QDialog {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
            }}
            
            QDialog QLabel#modal-title {{
                font-size: {Typography.text_lg};
                font-weight: {Typography.font_semibold};
                color: {Colors.text_primary};
                padding-bottom: {Spacing.space_3};
                border-bottom: 1px solid {Colors.border_default};
            }}
            
            QDialog QLabel#modal-content {{
                font-size: {Typography.text_base};
                color: {Colors.text_secondary};
                padding: {Spacing.space_4} 0;
            }}
        """
    
    @staticmethod
    def login() -> str:
        """로그인 다이얼로그"""
        return f"""
            QDialog {{
                background-color: {Colors.bg_base};
            }}
            
            /* 로고 영역 */
            QLabel#login-logo {{
                font-size: {Typography.text_3xl};
                font-weight: {Typography.font_bold};
                color: {Colors.accent_primary};
                margin-bottom: {Spacing.space_6};
            }}
            
            /* 입력 필드 */
            QLineEdit {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_3};
                font-size: {Typography.text_base};
                color: {Colors.text_primary};
                min-height: 44px;
            }}
            
            QLineEdit:focus {{
                border: 2px solid {Colors.border_accent};
            }}
            
            /* 로그인 버튼 */
            QPushButton#login-btn {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.accent_primary}, stop:1 {Colors.accent_pressed}
                );
                color: {Colors.text_inverse};
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_3};
                font-size: {Typography.text_base};
                font-weight: {Typography.font_semibold};
                min-height: 44px;
            }}
            
            QPushButton#login-btn:hover {{
                background: {Colors.accent_hover};
            }}
            
            /* 링크 */
            QLabel#login-link {{
                color: {Colors.accent_secondary};
                font-size: {Typography.text_sm};
            }}
            
            QLabel#login-link:hover {{
                color: {Colors.accent_primary};
                text-decoration: underline;
            }}
        """
    
    @staticmethod
    def settings() -> str:
        """설정 다이얼로그"""
        return f"""
            QDialog {{
                background-color: {Colors.bg_base};
            }}
            
            /* 사이드바 */
            QListWidget#settings-sidebar {{
                background-color: {Colors.bg_surface};
                border: none;
                border-right: 1px solid {Colors.border_default};
                font-size: {Typography.text_base};
                padding: {Spacing.space_2};
            }}
            
            QListWidget#settings-sidebar::item {{
                padding: {Spacing.space_3} {Spacing.space_4};
                border-radius: {Radius.radius_sm};
                margin: {Spacing.space_1} 0;
            }}
            
            QListWidget#settings-sidebar::item:selected {{
                background-color: {Colors.accent_primary};
                color: {Colors.text_inverse};
            }}
            
            QListWidget#settings-sidebar::item:hover:!selected {{
                background-color: {Colors.bg_overlay};
            }}
            
            /* 설정 섹션 */
            QGroupBox {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_md};
                margin-top: {Spacing.space_4};
                padding: {Spacing.space_4};
            }}
            
            QGroupBox::title {{
                color: {Colors.accent_primary};
                font-weight: {Typography.font_semibold};
            }}
        """
    
    @staticmethod
    def confirm() -> str:
        """확인 다이얼로그"""
        return f"""
            QDialog {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
            }}
            
            QLabel#confirm-icon {{
                font-size: 48px;
            }}
            
            QLabel#confirm-title {{
                font-size: {Typography.text_lg};
                font-weight: {Typography.font_semibold};
                color: {Colors.text_primary};
            }}
            
            QLabel#confirm-message {{
                font-size: {Typography.text_base};
                color: {Colors.text_secondary};
            }}
            
            QPushButton#confirm-yes {{
                background: {Colors.accent_primary};
                color: {Colors.text_inverse};
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_5};
                font-weight: {Typography.font_semibold};
            }}
            
            QPushButton#confirm-no {{
                background: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_5};
            }}
        """
    
    @staticmethod
    def message_box() -> str:
        """메시지 박스 스타일"""
        return f"""
            QMessageBox {{
                background-color: {Colors.bg_surface};
            }}
            
            QMessageBox QLabel {{
                color: {Colors.text_primary};
                font-size: {Typography.text_base};
            }}
            
            QMessageBox QPushButton {{
                background: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_4};
                min-width: 80px;
            }}
            
            QMessageBox QPushButton:hover {{
                background: {Colors.bg_overlay};
            }}
            
            QMessageBox QPushButton:default {{
                background: {Colors.accent_primary};
                color: {Colors.text_inverse};
                border: none;
            }}
        """
