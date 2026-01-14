"""
help_popup.py - TwinStar Quantum 도움말 팝업
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QTextBrowser, QPushButton)


class HelpPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TwinStar Quantum - 종합 사용 설명서")
        self.setMinimumSize(800, 700)
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: white; }
            QTabWidget::pane { border: 1px solid #30363d; border-radius: 8px; }
            QTabBar::tab { 
                background: #21262d; color: #888; 
                padding: 10px 15px; margin-right: 2px; 
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected { background: #30363d; color: #58a6ff; }
            QTextBrowser { 
                background: #161b22; color: #c9d1d9; 
                border: none; padding: 15px; 
                font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            }
            QPushButton {
                background: #21262d; color: white;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #30363d; border-color: #8b949e; }
        """)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        tabs = QTabWidget()
        tabs.addTab(self._create_workflow_tab(), "🚀 워크플로우")
        tabs.addTab(self._create_trade_tab(), "🏠 매매 & 보드")
        tabs.addTab(self._create_settings_tab(), "⚙️ 설정 & API")
        tabs.addTab(self._create_data_tab(), "💾 수집 & 캐시")
        tabs.addTab(self._create_backtest_tab(), "📊 백테스트")
        tabs.addTab(self._create_optimize_tab(), "🔬 최적화")
        tabs.addTab(self._create_history_tab(), "📈 결과 & 기록")
        tabs.addTab(self._create_faq_tab(), "❓ FAQ & 에러")
        
        layout.addWidget(tabs)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("확인 및 닫기")
        close_btn.setFixedWidth(150)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    
    def _create_workflow_tab(self):
        text = QTextBrowser()
        text.setHtml("""
        <h2 style='color: #58a6ff;'>🔄 프로그램 운영 표준 순서 (Workflow)</h2>
        <div style='background: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #30363d;'>
            <p><b>1. API 설정 (설정 탭)</b><br>
            &nbsp;&nbsp;&nbsp;ㄴ 거래소 API 키 등록 및 연결 확인</p>
            <p style='margin-left: 20px;'>↓</p>
            <p><b>2. 데이터 수집 (수집 탭)</b><br>
            &nbsp;&nbsp;&nbsp;ㄴ 전략 검증을 위한 과거 캔들 데이터 다운로드</p>
            <p style='margin-left: 20px;'>↓</p>
            <p><b>3. 백테스트 (백테스트 탭)</b><br>
            &nbsp;&nbsp;&nbsp;ㄴ 수집된 데이터로 전략의 과거 성과 검정</p>
            <p style='margin-left: 20px;'>↓</p>
            <p><b>4. 최적화 (최적화 탭)</b><br>
            &nbsp;&nbsp;&nbsp;ㄴ 해당 코인에 가장 잘 맞는 필터/지표 값 찾기</p>
            <p style='margin-left: 20px;'>↓</p>
            <p><b>5. 프리셋 적용 (최적화/백테스트)</b><br>
            &nbsp;&nbsp;&nbsp;ㄴ 검증된 설정값을 '프리셋'으로 저장 및 선택</p>
            <p style='margin-left: 20px;'>↓</p>
            <p><b>6. 실매매 시작 (매매 탭)</b><br>
            &nbsp;&nbsp;&nbsp;ㄴ 봇을 실행하여 실시간 시그널 매매 시작</p>
        </div>
        <p style='color: #8b949e; margin-top: 10px;'>※ 초기 1회 설정 후에는 6번(매매 시작)만 수행하면 됩니다.</p>
        """)
        return text

    def _create_trade_tab(self):
        text = QTextBrowser()
        text.setHtml("""
        <h2 style='color: #58a6ff;'>🏠 매매 대시보드 이용 가이드</h2>
        <h3>✅ 주요 기능</h3>
        <p>• <b>봇 시작/정지:</b> [Start Bots] 클릭 시 선택된 모든 코인의 봇이 가동됩니다.<br>
        • <b>실시간 모니터링:</b> 봇의 현재 상태(상태, 진입가, 수익률)를 실시간으로 확인합니다.<br>
        • <b>시그널 탐색:</b> 우측 '익스플로러'에서 전 코인의 실시간 패턴 발생 여부를 체크합니다.</p>
        
        <h3>💡 팁</h3>
        <p>• <b>멀티코인:</b> 여러 코인을 체크박스로 선택하여 동시에 관리할 수 있습니다.<br>
        • <b>잔고 확인:</b> 상단에 현재 거래소의 총 잔고(USDT/KRW)가 표시됩니다.</p>
        """)
        return text

    def _create_settings_tab(self):
        text = QTextBrowser()
        text.setHtml("""
        <h2 style='color: #58a6ff;'>⚙️ 설정 및 API 등록</h2>
        <h3>🔑 API 등록 절차</h3>
        <p>1. 거래소 홈페이지에서 API Key 및 Secret Key 발급<br>
        2. [설정] 탭에서 해당 거래소 선택 후 키 입력<br>
        3. <b>[연결 테스트]</b> 버튼 클릭하여 연동 확인</p>
        
        <h3>⚠️ 주의사항</h3>
        <p>• <b>주문 권한:</b> API 설정 시 'Spot' 및 'Futures' 거래 권한이 반드시 체크되어야 합니다.<br>
        • <b>IP 화이트리스트:</b> (특히 업비트) 고정 IP 등록이 필요할 수 있습니다.<br>
        • <b>보안:</b> 입력된 키는 로컬 PC에 암호화되어 안전하게 저장됩니다.</p>
        """)
        return text

    def _create_data_tab(self):
        text = QTextBrowser()
        text.setHtml("""
        <h2 style='color: #58a6ff;'>💾 데이터 수집 및 캐시 관리</h2>
        <h3>📥 데이터 다운로드</h3>
        <p>• 백테스트와 최적화를 위해서는 과거 캔들 데이터가 로컬에 있어야 합니다.<br>
        • [수집] 탭에서 심볼/시간봉 선택 후 '수집 시작'을 클릭하세요.</p>
        
        <h3>🧹 캐시 관리</h3>
        <p>• 중복 데이터나 오래된 데이터는 [캐시 관리] 탭에서 삭제하여 용량을 확보할 수 있습니다.<br>
        • 데이터가 꼬인 경우 전체 삭제 후 다시 수집하는 것을 권장합니다.</p>
        """)
        return text

    def _create_backtest_tab(self):
        text = QTextBrowser()
        text.setHtml("""
        <h2 style='color: #58a6ff;'>📊 백테스트 실행 및 해석</h2>
        <h3>📝 실행 방법</h3>
        <p>1. 프리셋(검증할 설정값)을 선택합니다.<br>
        2. 기간과 레버리지를 설정합니다.<br>
        3. <b>[백테스트 실행]</b>을 클릭합니다.</p>
        
        <h3>📉 결과 지표 설명</h3>
        <p>• <b>수익률 (Return):</b> 투자 원금 대비 최종 수익 비율입니다.<br>
        • <b>MDD:</b> 최대 낙폭 수치로, 자산이 고점 대비 가장 많이 하락했던 비율입니다 (낮을수록 안전).<br>
        • <b>승률 (WinRate):</b> 전체 매매 중 익절로 종료된 비율입니다.</p>
        """)
        return text

    def _create_optimize_tab(self):
        text = QTextBrowser()
        text.setHtml("""
        <h2 style='color: #58a6ff;'>🔬 파라미터 최적화</h2>
        <h3>🎯 최적화란?</h3>
        <p>수천 가지 파라미터 조합을 대조하여, 과거 데이터 상에서 가장 수익률이 높고 안정적인 값을 자동으로 찾아주는 기능입니다.</p>
        
        <h3>⚡ 검색 모드</h3>
        <p>• <b>빠른:</b> 핵심 조합 위주로 신속하게 검색합니다.<br>
        • <b>표준:</b> 권장되는 밸런스 있는 검색 모드입니다.<br>
        • <b>심층:</b> 매우 정밀하게 최적의 값을 탐색합니다 (시간 소요).</p>
        
        <p>✅ 결과 테이블에서 원하는 행을 <b>더블클릭</b>하면 해당 값이 프리셋으로 자동 적용됩니다.</p>
        """)
        return text

    def _create_history_tab(self):
        text = QTextBrowser()
        text.setHtml("""
        <h2 style='color: #58a6ff;'>📈 결과 확인 및 기록</h2>
        <h3>🔍 상세 차트 보기</h3>
        <p>백테스트 결과나 거래 내역에서 행을 선택하면, 차트상에서 정확히 <b>어디서 진입하고 청산했는지</b> 화살표로 시각화됩니다.</p>
        
        <h3>📒 거래 기록</h3>
        <p>실제 봇이 수행한 모든 매매 기록은 [거래 내역] 탭에 누적됩니다. 손익 분석과 전략 튜닝을 위한 기초 데이터로 활용하세요.</p>
        """)
        return text

    def _create_faq_tab(self):
        text = QTextBrowser()
        text.setHtml("""
        <h2 style='color: #ff5252;'>❓ FAQ & 오류 해결</h2>
        <h3>Q. 봇이 매매를 시작하지 않아요.</h3>
        <p>A. [수집] 탭에서 데이터를 먼저 받아야 합니다. 데이터가 로드되면 'Alpha-X7 Core Loaded' 메시지가 출력됩니다.</p>
        
        <h3>Q. API 연동에 실패합니다.</h3>
        <p>A. 키 입력 시 앞뒤 공백이 없는지, 거래소에서 API를 생성할 때 'Trading' 권한을 주었는지 확인하세요.</p>
        
        <h3>❌ 주요 오류 메시지</h3>
        <p>• <b>Insufficient Balance:</b> 거래소 계좌에 USDT(또는 KRW)가 부족합니다.<br>
        • <b>Invalid Signature:</b> API 키 또는 시크릿 키가 부정확합니다.<br>
        • <b>Connectivity Error:</b> 인터넷 또는 거래소 서버 상태가 불안정합니다.</p>
        """)
        return text



if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    popup = HelpPopup()
    popup.show()
    sys.exit(app.exec())
