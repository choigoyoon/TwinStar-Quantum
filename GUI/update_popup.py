"""
업데이트 확인 팝업 (Silent Install 방식)
Setup.exe 다운로드 후 자동 설치
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QMessageBox, QApplication
)
from PyQt6.QtCore import QThread, pyqtSignal


class DownloadWorker(QThread):
    """다운로드 작업 스레드 (UI 프리즈 방지)"""
    progress = pyqtSignal(int, int)   # (다운로드된 바이트, 전체 바이트)
    finished = pyqtSignal(object)     # 다운로드된 파일 경로 (Path)
    error = pyqtSignal(str)           # 에러 메시지
    
    def __init__(self, updater, url):
        super().__init__()
        self.updater = updater
        self.url = url
    
    def run(self):
        try:
            def on_progress(downloaded, total):
                self.progress.emit(downloaded, total)
            
            path = self.updater.download_installer(self.url, on_progress)
            if path is None:
                self.error.emit("다운로드 실패: 서버 응답 오류")
            else:
                self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class UpdatePopup(QDialog):
    """업데이트 확인 팝업 (Silent Install 방식)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔄 소프트웨어 업데이트")
        self.setFixedSize(450, 350)
        self._pending_url = None
        self._pending_version = None
        self._download_worker = None
        self.setStyleSheet("""
            QDialog { background: #1a1a2e; color: white; }
            QProgressBar {
                border: 1px solid #444; border-radius: 5px;
                background: #2a2a3e; text-align: center;
            }
            QProgressBar::chunk { background: #4CAF50; border-radius: 4px; }
            QPushButton {
                background: #2a2a3e; color: white;
                border: 1px solid #444; border-radius: 5px; padding: 10px 20px;
            }
            QPushButton:hover { background: #3a3a4e; }
            QPushButton:disabled { background: #222; color: #666; }
        """)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # 현재 버전
        try:
            from core.updater import get_updater
            updater = get_updater()
            version = updater.current_version
        except ImportError:
            version = "1.1.7"
        
        self.version_label = QLabel(f"현재 버전: v{version}")
        self.version_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50;")
        layout.addWidget(self.version_label)
        
        # 상태
        self.status_label = QLabel("업데이트를 확인하려면 아래 버튼을 클릭하세요.")
        self.status_label.setStyleSheet("color: #aaa; font-size: 13px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # 진행률
        self.progress = QProgressBar()
        self.progress.setFixedHeight(25)
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # 다운로드 크기 표시
        self.size_label = QLabel("")
        self.size_label.setStyleSheet("color: #888; font-size: 11px;")
        self.size_label.hide()
        layout.addWidget(self.size_label)
        
        # 변경사항
        self.changelog_label = QLabel("")
        self.changelog_label.setWordWrap(True)
        self.changelog_label.setStyleSheet("color: #8BC34A; font-size: 12px;")
        layout.addWidget(self.changelog_label)
        
        layout.addStretch()
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.check_btn = QPushButton("🔍 업데이트 확인")
        self.check_btn.setFixedWidth(150)
        self.check_btn.clicked.connect(self._on_check)
        btn_layout.addWidget(self.check_btn)
        
        self.update_btn = QPushButton("⬇️ 업데이트 설치")
        self.update_btn.setFixedWidth(140)
        self.update_btn.clicked.connect(self._on_update)
        self.update_btn.hide()
        btn_layout.addWidget(self.update_btn)
        
        self.close_btn = QPushButton("닫기")
        self.close_btn.setFixedWidth(80)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _on_check(self):
        """업데이트 확인 버튼 클릭"""
        self.check_btn.setEnabled(False)
        self.check_btn.setText("확인 중...")
        self.status_label.setText("서버에서 버전 확인 중...")
        self.changelog_label.setText("")
        
        QApplication.processEvents()
        
        try:
            from core.updater import get_updater
            updater = get_updater()
            result = updater.check_update()
            
            if not result.get('success'):
                self.status_label.setText(f"❌ 확인 실패: {result.get('error', '서버 연결 오류')}")
            elif result.get('has_update'):
                latest = result.get('latest_version')
                current = result.get('current_version')
                self.version_label.setText(f"현재: v{current} → 최신: v{latest}")
                self.status_label.setText("✨ 새 버전을 사용할 수 있습니다!")
                
                # 다운로드 크기 표시
                size = result.get('download_size', '')
                if size:
                    self.size_label.setText(f"📦 다운로드 크기: {size}")
                    self.size_label.show()
                
                changelog = result.get('changelog', [])
                if changelog:
                    self.changelog_label.setText("📋 변경사항:\n• " + "\n• ".join(changelog[:5]))
                
                self._pending_url = result.get('download_url')
                self._pending_version = latest
                self.update_btn.show()
            else:
                self.status_label.setText("✅ 최신 버전입니다. 업데이트가 필요 없습니다.")
        except Exception as e:
            self.status_label.setText(f"❌ 오류: {e}")
        
        self.check_btn.setEnabled(True)
        self.check_btn.setText("🔍 업데이트 확인")
    
    def _on_update(self):
        """업데이트 설치 버튼 클릭"""
        if not self._pending_url:
            QMessageBox.warning(self, "오류", "다운로드 URL이 없습니다.")
            return
        
        reply = QMessageBox.question(
            self, "업데이트 설치",
            f"v{self._pending_version} 업데이트를 다운로드하고 설치합니다.\n\n"
            "⚠️ 설치 중 프로그램이 자동으로 종료되고\n"
            "설치 완료 후 다시 시작됩니다.\n\n"
            "계속할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # UI 상태 변경
        self.update_btn.setEnabled(False)
        self.update_btn.setText("다운로드 중...")
        self.check_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.progress.show()
        self.progress.setValue(0)
        self.progress.setMaximum(100)
        self.status_label.setText("⬇️ 다운로드 시작...")
        
        # 다운로드 시작
        try:
            from core.updater import get_updater
            updater = get_updater()
            
            self._download_worker = DownloadWorker(updater, self._pending_url)
            self._download_worker.progress.connect(self._on_download_progress)
            self._download_worker.finished.connect(self._on_download_finished)
            self._download_worker.error.connect(self._on_download_error)
            self._download_worker.start()
        except Exception as e:
            self._on_download_error(str(e))
    
    def _on_download_progress(self, downloaded: int, total: int):
        """다운로드 진행률 업데이트"""
        if total > 0:
            percent = int(downloaded / total * 100)
            self.progress.setValue(percent)
            
            # 크기 표시 (MB 단위)
            dl_mb = downloaded / 1024 / 1024
            total_mb = total / 1024 / 1024
            self.status_label.setText(f"⬇️ 다운로드 중... {dl_mb:.1f}MB / {total_mb:.1f}MB ({percent}%)")
            self.update_btn.setText(f"{percent}%")
    
    def _on_download_finished(self, installer_path):
        """다운로드 완료 → 인스톨러 실행"""
        self.progress.setValue(100)
        self.status_label.setText("🔧 설치 시작... 프로그램이 곧 재시작됩니다.")
        self.update_btn.setText("설치 중...")
        
        QApplication.processEvents()
        
        # 인스톨러 실행 (현재 앱 종료됨)
        try:
            from core.updater import get_updater
            updater = get_updater()
            updater.run_installer_and_exit(installer_path)
        except Exception as e:
            self._on_download_error(f"인스톨러 실행 실패: {e}")
    
    def _on_download_error(self, msg: str):
        """다운로드/설치 오류"""
        self.status_label.setText(f"❌ 오류: {msg}")
        QMessageBox.critical(self, "업데이트 오류", f"업데이트 실패:\n{msg}")
        self._reset_ui()
    
    def _reset_ui(self):
        """UI 상태 리셋"""
        self.progress.hide()
        self.update_btn.setEnabled(True)
        self.update_btn.setText("⬇️ 업데이트 설치")
        self.check_btn.setEnabled(True)
        self.close_btn.setEnabled(True)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    popup = UpdatePopup()
    popup.show()
    sys.exit(app.exec())
