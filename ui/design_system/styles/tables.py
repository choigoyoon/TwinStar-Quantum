"""
TwinStar Quantum - Table Styles
===============================

테이블 컴포넌트 스타일
"""

from ..tokens import Colors, Typography, Spacing, Radius


class TableStyles:
    """
    테이블 스타일 생성기
    
    사용법:
        table.setStyleSheet(TableStyles.default())
        table.setStyleSheet(TableStyles.compact())
    """
    
    @staticmethod
    def default() -> str:
        """기본 테이블 스타일"""
        return f"""
            QTableWidget, QTableView {{
                background-color: {Colors.bg_surface};
                alternate-background-color: {Colors.bg_base};
                border: none;
                gridline-color: {Colors.border_muted};
                outline: none;
                font-size: {Typography.text_sm};
            }}
            QTableWidget::item, QTableView::item {{
                padding: {Spacing.space_2};
                border-bottom: 1px solid {Colors.border_muted};
            }}
            QTableWidget::item:selected, QTableView::item:selected {{
                background-color: {Colors.accent_primary};
                color: {Colors.text_inverse};
            }}
            QTableWidget::item:hover, QTableView::item:hover {{
                background-color: {Colors.bg_overlay};
            }}
            QHeaderView {{
                background-color: {Colors.bg_surface};
            }}
            QHeaderView::section {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_secondary};
                padding: {Spacing.space_3} {Spacing.space_2};
                border: none;
                border-bottom: 1px solid {Colors.border_default};
                font-weight: {Typography.font_semibold};
                font-size: {Typography.text_sm};
                text-transform: uppercase;
            }}
            QHeaderView::section:hover {{
                background-color: {Colors.bg_overlay};
            }}
        """
    
    @staticmethod
    def compact() -> str:
        """컴팩트 테이블 (좁은 패딩)"""
        return f"""
            QTableWidget, QTableView {{
                background-color: {Colors.bg_surface};
                alternate-background-color: {Colors.bg_base};
                border: none;
                gridline-color: {Colors.border_muted};
                outline: none;
                font-size: {Typography.text_xs};
            }}
            QTableWidget::item, QTableView::item {{
                padding: {Spacing.space_1};
                border-bottom: 1px solid {Colors.border_muted};
            }}
            QTableWidget::item:selected, QTableView::item:selected {{
                background-color: {Colors.accent_primary};
                color: {Colors.text_inverse};
            }}
            QHeaderView::section {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_secondary};
                padding: {Spacing.space_2} {Spacing.space_1};
                border: none;
                border-bottom: 1px solid {Colors.border_default};
                font-weight: {Typography.font_semibold};
                font-size: {Typography.text_xs};
            }}
        """
    
    @staticmethod
    def striped() -> str:
        """줄무늬 테이블"""
        return f"""
            QTableWidget, QTableView {{
                background-color: {Colors.bg_surface};
                alternate-background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_md};
                gridline-color: transparent;
                outline: none;
                font-size: {Typography.text_sm};
            }}
            QTableWidget::item, QTableView::item {{
                padding: {Spacing.space_3};
            }}
            QTableWidget::item:selected, QTableView::item:selected {{
                background-color: {Colors.accent_primary};
                color: {Colors.text_inverse};
            }}
            QHeaderView::section {{
                background-color: {Colors.bg_base};
                color: {Colors.text_secondary};
                padding: {Spacing.space_3};
                border: none;
                border-bottom: 2px solid {Colors.border_default};
                font-weight: {Typography.font_bold};
                font-size: {Typography.text_sm};
            }}
        """
    
    @staticmethod
    def borderless() -> str:
        """테두리 없는 테이블"""
        return f"""
            QTableWidget, QTableView {{
                background-color: transparent;
                border: none;
                gridline-color: transparent;
                outline: none;
                font-size: {Typography.text_sm};
            }}
            QTableWidget::item, QTableView::item {{
                padding: {Spacing.space_2};
                border-bottom: 1px solid {Colors.border_muted};
            }}
            QTableWidget::item:selected, QTableView::item:selected {{
                background-color: rgba(0, 212, 170, 0.2);
                color: {Colors.text_primary};
            }}
            QHeaderView {{
                background-color: transparent;
            }}
            QHeaderView::section {{
                background-color: transparent;
                color: {Colors.text_secondary};
                padding: {Spacing.space_2};
                border: none;
                border-bottom: 1px solid {Colors.border_default};
                font-weight: {Typography.font_semibold};
                font-size: {Typography.text_xs};
                text-transform: uppercase;
            }}
        """
    
    @staticmethod
    def pnl_cell(is_profit: bool) -> str:
        """PnL 셀 스타일 (수익/손실)"""
        color = Colors.success if is_profit else Colors.danger
        return f"""
            QTableWidgetItem {{
                color: {color};
                font-weight: {Typography.font_bold};
            }}
        """
