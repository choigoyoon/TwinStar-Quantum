from pathlib import Path
import re

base = Path(__file__).parent
gui_path = base / 'GUI'

print('=' * 70)
print('🖥️ Phase 3: GUI 기능 점검')
print('=' * 70)

#############################################
# [1] GUI 파일 구조
#############################################
print('\n📁 [1] GUI 파일 구조')
print('-' * 70)

if gui_path.exists():
    py_files = list(gui_path.glob('*.py'))
    for f in py_files:
        try:
            lines = len(f.read_text(encoding='utf-8', errors='ignore').split('\n'))
            print(f'  📄 {f.name} ({lines:,}줄)')
        except Exception:

            pass
else:
    print('  ❌ GUI 폴더 없음')

#############################################
# [2] 메인 윈도우 (staru_main.py)
#############################################
print('\n🏠 [2] 메인 윈도우')
print('-' * 70)

main_file = gui_path / 'staru_main.py'
if main_file.exists():
    code = main_file.read_text(encoding='utf-8', errors='ignore')
    
    main_features = {
        '탭 구성': r'addTab|QTabWidget',
        '등급 표시': r'tier.*label|등급|days.*label',
        '업그레이드 버튼': r'upgrade.*btn|업그레이드',
        '시작/중지 버튼': r'start.*btn|stop.*btn|시작|중지',
        '설정 저장': r'save.*settings|settings.*save',
        '테마 적용': r'theme|stylesheet|setStyleSheet',
    }
    
    for feat, pattern in main_features.items():
        if re.search(pattern, code, re.I):
            print(f'  ✅ {feat}')
        else:
            print(f'  ❌ {feat}')

#############################################
# [3] 대시보드 (trading_dashboard.py)
#############################################
print('\n📊 [3] 대시보드')
print('-' * 70)

dash_file = gui_path / 'trading_dashboard.py'
if dash_file.exists():
    code = dash_file.read_text(encoding='utf-8', errors='ignore')
    
    dash_features = {
        '실시간 가격': r'price.*label|current.*price|실시간',
        '포지션 표시': r'position.*label|포지션',
        '잔고 표시': r'balance.*label|잔고|💰',
        'PnL 표시': r'pnl.*label|손익|수익',
        '거래소 선택': r'exchange.*combo|거래소.*선택',
        '새로고침 버튼': r'refresh|새로고침',
        'QThread 사용': r'QThread|Worker|moveToThread',
        '백그라운드 로딩': r'background|조회중',
    }
    
    for feat, pattern in dash_features.items():
        if re.search(pattern, code, re.I):
            print(f'  ✅ {feat}')
        else:
            print(f'  ❌ {feat}')

#############################################
# [4] 백테스트 위젯
#############################################
print('\n📈 [4] 백테스트 위젯')
print('-' * 70)

bt_file = gui_path / 'backtest_widget.py'
if bt_file.exists():
    code = bt_file.read_text(encoding='utf-8', errors='ignore')
    
    bt_features = {
        '기간 선택': r'date.*edit|from.*date|to.*date|기간',
        '파라미터 입력': r'param.*input|atr|rsi.*input',
        '실행 버튼': r'run.*btn|backtest.*btn|실행',
        '결과 테이블': r'result.*table|QTableWidget',
        '차트 표시': r'chart|plot|matplotlib|pyqtgraph',
        '승률 표시': r'win.*rate|승률',
        'PnL 표시': r'total.*pnl|누적.*수익',
    }
    
    for feat, pattern in bt_features.items():
        if re.search(pattern, code, re.I):
            print(f'  ✅ {feat}')
        else:
            print(f'  ❌ {feat}')
else:
    print('  ❌ backtest_widget.py 없음')

#############################################
# [5] 설정 위젯
#############################################
print('\n⚙️ [5] 설정 위젯')
print('-' * 70)

settings_file = gui_path / 'settings_widget.py'
if settings_file.exists():
    code = settings_file.read_text(encoding='utf-8', errors='ignore')
    
    settings_features = {
        'API 키 입력': r'api.*key|secret.*key|API',
        '거래소 설정': r'exchange.*setting|거래소',
        '레버리지 설정': r'leverage.*input|레버리지',
        '알림 설정': r'telegram|notification|알림',
        '저장 버튼': r'save.*btn|저장',
        '암호화 저장': r'encrypt|fernet|crypto',
    }
    
    for feat, pattern in settings_features.items():
        if re.search(pattern, code, re.I):
            print(f'  ✅ {feat}')
        else:
            print(f'  ❌ {feat}')
else:
    print('  ❌ settings_widget.py 없음')

#############################################
# [6] 데이터 수집기
#############################################
print('\n📥 [6] 데이터 수집기')
print('-' * 70)

data_file = gui_path / 'data_collector_widget.py'
if data_file.exists():
    code = data_file.read_text(encoding='utf-8', errors='ignore')
    
    data_features = {
        '심볼 선택': r'symbol.*input|심볼|코인',
        '타임프레임 선택': r'timeframe|interval|타임프레임',
        '다운로드 버튼': r'download.*btn|다운로드',
        '진행률 표시': r'progress|QProgressBar|진행',
        'Parquet 저장': r'parquet|\.parquet',
    }
    
    for feat, pattern in data_features.items():
        if re.search(pattern, code, re.I):
            print(f'  ✅ {feat}')
        else:
            print(f'  ❌ {feat}')
else:
    print('  ❌ data_collector_widget.py 없음')

#############################################
# [7] 시그널-슬롯 연결
#############################################
print('\n🔗 [7] 시그널-슬롯 연결')
print('-' * 70)

total_connects = 0
signals_found = set()

for f in gui_path.glob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        connects = len(re.findall(r'\.connect\(', code))
        total_connects += connects
        
        # 주요 시그널 찾기
        for sig in ['backtest_finished', 'download_finished', 'settings_applied', 
                    'position_updated', 'order_filled', 'error_occurred']:
            if sig in code:
                signals_found.add(sig)
    except Exception:

        pass

print(f'  📡 총 .connect() 호출: {total_connects}개')
print(f'  📡 주요 시그널: {", ".join(signals_found) if signals_found else "없음"}')

#############################################
# [8] UI 프리징 방지
#############################################
print('\n⏱️ [8] UI 프리징 방지')
print('-' * 70)

threading_patterns = {
    'QThread 사용': r'QThread',
    'Worker 클래스': r'class.*Worker|Worker\(',
    'moveToThread': r'moveToThread',
    'threading.Thread': r'threading\.Thread',
    'QTimer': r'QTimer',
}

for f in gui_path.glob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        found = []
        for name, pattern in threading_patterns.items():
            if re.search(pattern, code):
                found.append(name)
        if found:
            print(f'  {f.name}: {", ".join(found)}')
    except Exception:

        pass

print('\n' + '=' * 70)
