"""
GPU 설정 탭
===========

GPU 가속 설정 UI

기능:
    - GPU 가속 on/off
    - 렌더링 백엔드 선택 (Direct3D 11/12, Vulkan, OpenGL)
    - 최대 FPS 설정
    - 차트 스로틀링 on/off
    - GPU 정보 표시

작성: Claude Sonnet 4.5
날짜: 2026-01-15
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QRadioButton, QButtonGroup, QComboBox,
    QPushButton, QGroupBox, QFormLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ui.design_system.tokens import Colors, Typography, Spacing, Radius
from config.gpu_settings import (
    GPUSettingsManager,
    GPUSettings,
    GPUInfo,
    RenderingBackend,
    PowerMode,
    detect_gpu_info,
)


class GPUInfoCard(QFrame):
    """GPU 정보 카드"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.gpu_info: Optional[GPUInfo] = None
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_lg};
                padding: {Spacing.space_4};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.i_space_2)

        # 타이틀
        title = QLabel("🎮 GPU 정보")
        title.setStyleSheet(f"""
            color: {Colors.text_primary};
            font-size: {Typography.text_lg};
            font-weight: {Typography.font_bold};
        """)
        layout.addWidget(title)

        # 정보 라벨들
        self.vendor_label = self._create_info_label("Vendor: Unknown")
        self.model_label = self._create_info_label("Model: Unknown")
        self.driver_label = self._create_info_label("Driver: Unknown")
        self.opengl_label = self._create_info_label("OpenGL: Unknown")
        self.vulkan_label = self._create_info_label("Vulkan: Unknown")
        self.d3d12_label = self._create_info_label("Direct3D 12: Unknown")

        layout.addWidget(self.vendor_label)
        layout.addWidget(self.model_label)
        layout.addWidget(self.driver_label)
        layout.addWidget(self.opengl_label)
        layout.addWidget(self.vulkan_label)
        layout.addWidget(self.d3d12_label)

        # 새로고침 버튼
        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.setStyleSheet(self._get_button_style())
        refresh_btn.clicked.connect(self.refresh_info)
        layout.addWidget(refresh_btn)

    def _create_info_label(self, text: str) -> QLabel:
        """정보 라벨 생성"""
        label = QLabel(text)
        label.setStyleSheet(f"""
            color: {Colors.text_secondary};
            font-size: {Typography.text_sm};
            padding: {Spacing.space_1};
        """)
        return label

    def _get_button_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {Colors.bg_overlay};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_2} {Spacing.space_3};
                color: {Colors.text_primary};
                font-size: {Typography.text_sm};
            }}
            QPushButton:hover {{
                background-color: {Colors.bg_elevated};
                border-color: {Colors.accent_primary};
            }}
        """

    def refresh_info(self):
        """GPU 정보 새로고침"""
        self.gpu_info = detect_gpu_info()
        self.update_display()

    def update_display(self):
        """표시 업데이트"""
        if self.gpu_info is None:
            return

        self.vendor_label.setText(f"Vendor: {self.gpu_info.vendor}")
        self.model_label.setText(f"Model: {self.gpu_info.model}")
        self.driver_label.setText(f"Driver: {self.gpu_info.driver}")
        self.opengl_label.setText(f"OpenGL: {self.gpu_info.opengl_version}")
        self.vulkan_label.setText(
            f"Vulkan: {'✅ 지원' if self.gpu_info.supports_vulkan else '❌ 미지원'}"
        )
        self.d3d12_label.setText(
            f"Direct3D 12: {'✅ 지원' if self.gpu_info.supports_d3d12 else '❌ 미지원'}"
        )


class GPUSettingsTab(QWidget):
    """
    GPU 설정 탭

    시그널:
        settings_changed: 설정 변경 시 발생
    """

    settings_changed = pyqtSignal(GPUSettings)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.manager = GPUSettingsManager()
        self.settings = self.manager.load()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.i_space_4)
        layout.setContentsMargins(
            Spacing.i_space_4, Spacing.i_space_4,
            Spacing.i_space_4, Spacing.i_space_4
        )

        # GPU 가속 활성화
        self.gpu_enabled_checkbox = QCheckBox("✨ GPU 가속 활성화")
        self.gpu_enabled_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.text_primary};
                font-size: {Typography.text_base};
                font-weight: {Typography.font_semibold};
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
            }}
        """)
        self.gpu_enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self.gpu_enabled_checkbox)

        # 렌더링 백엔드 그룹
        backend_group = QGroupBox("렌더링 백엔드")
        backend_group.setStyleSheet(f"""
            QGroupBox {{
                color: {Colors.text_primary};
                font-size: {Typography.text_base};
                font-weight: {Typography.font_semibold};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_4};
                margin-top: {Spacing.space_3};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.space_3};
                padding: 0 {Spacing.space_2};
            }}
        """)

        backend_layout = QVBoxLayout()
        backend_layout.setSpacing(Spacing.i_space_2)

        self.backend_group = QButtonGroup(self)
        backends = [
            (RenderingBackend.D3D11, "🪟 Direct3D 11 (권장 - Windows)"),
            (RenderingBackend.D3D12, "🪟 Direct3D 12 (Windows 10+)"),
            (RenderingBackend.VULKAN, "🌋 Vulkan (크로스 플랫폼)"),
            (RenderingBackend.OPENGL, "🔷 OpenGL (레거시)"),
            (RenderingBackend.SOFTWARE, "💻 소프트웨어 렌더링 (CPU)"),
        ]

        for backend, label in backends:
            radio = QRadioButton(label)
            radio.setProperty("backend", backend.value)
            radio.setStyleSheet(f"""
                QRadioButton {{
                    color: {Colors.text_primary};
                    font-size: {Typography.text_sm};
                    padding: {Spacing.space_1};
                }}
            """)
            self.backend_group.addButton(radio)
            backend_layout.addWidget(radio)

        backend_group.setLayout(backend_layout)
        layout.addWidget(backend_group)

        # 성능 설정 그룹
        perf_group = QGroupBox("성능 설정")
        perf_group.setStyleSheet(backend_group.styleSheet())

        perf_layout = QFormLayout()
        perf_layout.setSpacing(Spacing.i_space_3)

        # FPS 제한
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["20", "30", "40", "60", "무제한"])
        self.fps_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_2} {Spacing.space_3};
                color: {Colors.text_primary};
                font-size: {Typography.text_sm};
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {Colors.accent_primary};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                selection-background-color: {Colors.accent_primary};
            }}
        """)

        fps_label = QLabel("최대 FPS:")
        fps_label.setStyleSheet(f"color: {Colors.text_secondary}; font-size: {Typography.text_sm};")
        perf_layout.addRow(fps_label, self.fps_combo)

        # 전력 모드
        self.power_combo = QComboBox()
        self.power_combo.addItem("🔋 절전 (30 FPS)", PowerMode.POWER_SAVER.value)
        self.power_combo.addItem("⚖️ 균형 (60 FPS)", PowerMode.BALANCED.value)
        self.power_combo.addItem("⚡ 고성능 (120 FPS)", PowerMode.HIGH_PERFORMANCE.value)
        self.power_combo.setStyleSheet(self.fps_combo.styleSheet())

        power_label = QLabel("전력 모드:")
        power_label.setStyleSheet(fps_label.styleSheet())
        perf_layout.addRow(power_label, self.power_combo)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        # 차트 설정
        self.chart_throttle_checkbox = QCheckBox("📊 차트 스로틀링 활성화 (CPU 부하 감소)")
        self.chart_throttle_checkbox.setStyleSheet(self.gpu_enabled_checkbox.styleSheet())
        layout.addWidget(self.chart_throttle_checkbox)

        self.pyqtgraph_opengl_checkbox = QCheckBox("🔬 PyQtGraph OpenGL 가속 (실험적)")
        self.pyqtgraph_opengl_checkbox.setStyleSheet(self.gpu_enabled_checkbox.styleSheet())
        layout.addWidget(self.pyqtgraph_opengl_checkbox)

        # GPU 정보 카드
        self.gpu_info_card = GPUInfoCard()
        self.gpu_info_card.refresh_info()
        layout.addWidget(self.gpu_info_card)

        # 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.setSpacing(Spacing.i_space_3)

        # 적용 버튼
        self.apply_btn = QPushButton("✅ 적용")
        self.apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.accent_primary};
                border: none;
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_3} {Spacing.space_5};
                color: {Colors.text_primary};
                font-size: {Typography.text_base};
                font-weight: {Typography.font_semibold};
            }}
            QPushButton:hover {{
                background-color: {Colors.accent_secondary};
            }}
            QPushButton:pressed {{
                background-color: {Colors.accent_primary};
            }}
        """)
        self.apply_btn.clicked.connect(self._on_apply)
        button_layout.addWidget(self.apply_btn)

        # 기본값 복원 버튼
        reset_btn = QPushButton("🔄 기본값 복원")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_3} {Spacing.space_5};
                color: {Colors.text_primary};
                font-size: {Typography.text_base};
            }}
            QPushButton:hover {{
                background-color: {Colors.bg_overlay};
                border-color: {Colors.accent_primary};
            }}
        """)
        reset_btn.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addStretch()

    def _load_settings(self):
        """설정 불러오기"""
        self.gpu_enabled_checkbox.setChecked(self.settings.enabled)

        # 백엔드 선택
        for button in self.backend_group.buttons():
            if button.property("backend") == self.settings.backend:
                button.setChecked(True)
                break

        # FPS
        if self.settings.max_fps == 0:
            self.fps_combo.setCurrentText("무제한")
        else:
            self.fps_combo.setCurrentText(str(self.settings.max_fps))

        # 전력 모드
        for i in range(self.power_combo.count()):
            if self.power_combo.itemData(i) == self.settings.power_mode:
                self.power_combo.setCurrentIndex(i)
                break

        # 차트 설정
        self.chart_throttle_checkbox.setChecked(self.settings.chart_throttle)
        self.pyqtgraph_opengl_checkbox.setChecked(self.settings.opengl_for_pyqtgraph)

        self._update_ui_enabled()

    def _on_enabled_changed(self, state: int):
        """GPU 가속 on/off 변경"""
        self._update_ui_enabled()

    def _update_ui_enabled(self):
        """UI 활성화 상태 업데이트"""
        enabled = self.gpu_enabled_checkbox.isChecked()

        for button in self.backend_group.buttons():
            button.setEnabled(enabled)

        self.fps_combo.setEnabled(enabled)
        self.power_combo.setEnabled(enabled)
        self.chart_throttle_checkbox.setEnabled(enabled)
        self.pyqtgraph_opengl_checkbox.setEnabled(enabled)

    def _on_apply(self):
        """적용 버튼 클릭"""
        # 설정 수집
        self.settings.enabled = self.gpu_enabled_checkbox.isChecked()

        # 백엔드
        for button in self.backend_group.buttons():
            if button.isChecked():
                self.settings.backend = button.property("backend")
                break

        # FPS
        fps_text = self.fps_combo.currentText()
        if fps_text == "무제한":
            self.settings.max_fps = 0
        else:
            self.settings.max_fps = int(fps_text)

        # 전력 모드
        self.settings.power_mode = self.power_combo.currentData()

        # 차트 설정
        self.settings.chart_throttle = self.chart_throttle_checkbox.isChecked()
        self.settings.opengl_for_pyqtgraph = self.pyqtgraph_opengl_checkbox.isChecked()

        # 저장
        self.manager.settings = self.settings
        self.manager.save()

        # 환경 변수 적용
        self.manager.apply_to_environment()

        # 시그널 발생
        self.settings_changed.emit(self.settings)

        print("✅ GPU 설정 적용 완료!")
        print(f"  - 백엔드: {self.settings.backend}")
        print(f"  - FPS: {self.settings.max_fps or '무제한'}")

    def _on_reset(self):
        """기본값 복원"""
        self.settings = GPUSettings()
        self.manager._set_defaults()
        self.settings = self.manager.settings
        self._load_settings()
        print("🔄 GPU 설정 기본값 복원 완료!")


# ==================== 테스트 코드 ====================
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    from ui.design_system.theme import ThemeGenerator

    app = QApplication(sys.argv)
    app.setStyleSheet(ThemeGenerator.generate())

    tab = GPUSettingsTab()
    tab.resize(600, 800)
    tab.show()

    sys.exit(app.exec())
