"""프리미엄 상태 카드 컴포넌트 (Glassmorphism + Animation)"""

from typing import Optional
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup
from ui.design_system.tokens import Colors, Radius, Shadow, Typography

class StatusCard(QFrame):
    """상태 표시 카드 - 글래스모피즘 스타일 및 박동 애니메이션 지원"""
    
    def __init__(self, title: str, value: str = "-", icon: str = ""):
        super().__init__()
        self.setObjectName("statusCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)
        
        # 타이틀
        self.title_label = QLabel(f"{icon} {title}" if icon else title)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setStyleSheet(f"color: {Colors.text_secondary}; font-size: {Typography.text_sm}; font-weight: 500;")
        
        # 값
        self.value_label = QLabel(value)
        self.value_label.setObjectName("valueLabel")
        self.value_label.setStyleSheet(f"color: {Colors.text_primary}; font-size: {Typography.text_2xl}; font-weight: 700; font-family: {Typography.font_sans};")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        
        self._apply_glass_style()
        self._setup_animations()

    def _apply_glass_style(self):
        """글래스모피즘 스타일 적용"""
        self.setStyleSheet(f"""
            QFrame#statusCard {{
                background-color: rgba(33, 38, 45, 0.6);
                border: 1px solid rgba(48, 54, 61, 0.8);
                border-radius: {Radius.radius_lg};
            }}
            QFrame#statusCard:hover {{
                background-color: rgba(48, 54, 61, 0.7);
                border: 1px solid {Colors.accent_primary};
            }}
        """)
        
        # 그림자 효과 (글로우 느낌)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def _setup_animations(self):
        """애니메이션 초기 설정"""
        self.pulse_anim = QSequentialAnimationGroup(self)
        
        # 점점 밝아지기
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(1000)
        fade_in.setStartValue(0.7)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # 점점 어두워지기
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(1000)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.7)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self.pulse_anim.addAnimation(fade_in)
        self.pulse_anim.addAnimation(fade_out)
        self.pulse_anim.setLoopCount(-1) # 무한 반복

    def start_pulse(self):
        """박동 애니메이션 시작"""
        if self.pulse_anim.state() != QSequentialAnimationGroup.State.Running:
            self.pulse_anim.start()

    def stop_pulse(self):
        """박동 애니메이션 중지"""
        self.pulse_anim.stop()
        self.setWindowOpacity(1.0)
    
    def set_value(self, value: str, color: Optional[str] = None):
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color}; font-size: {Typography.text_2xl}; font-weight: 700;")
    
    def set_positive(self, value: str):
        """녹색(이익) 상태로 값 설정"""
        self.set_value(value, Colors.accent_primary)

    def set_negative(self, value: str):
        """빨강(손실) 상태로 값 설정"""
        self.set_value(value, Colors.danger)

    def set_neutral(self, value: str):
        """회색(중립) 상태로 값 설정"""
        self.set_value(value, Colors.text_secondary)

    def update_value(self, value: str):
        """값만 업데이트 (색상 유지)"""
        self.value_label.setText(value)
