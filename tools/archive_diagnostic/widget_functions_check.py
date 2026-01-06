from pathlib import Path
import re

base = Path(r'C:\매매전략')
gui_path = base / 'GUI'

print('=' * 70)
print('🔍 위젯별 기능 상세 분석')
print('=' * 70)

#############################################
# [1] Trading Dashboard - 실시간 매매 컨트롤
#############################################
print('\n' + '=' * 70)
print('📊 [1] Trading Dashboard (trading_dashboard.py)')
print('=' * 70)

dash_file = gui_path / 'trading_dashboard.py'
if dash_file.exists():
    code = dash_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n  🎯 핵심 기능:')
    features = {
        '실시간 가격 표시': r'price.*label|current.*price|실시간.*가격',
        '포지션 상태': r'position.*status|포지션.*상태|PositionStatus',
        '잔고 표시': r'balance|잔고|💰',
        'PnL 표시': r'pnl.*label|손익|수익률',
        '시작/중지 버튼': r'start.*btn|stop.*btn|시작|중지',
        '거래소 선택': r'exchange.*combo|거래소.*선택',
        '심볼 선택': r'symbol.*combo|심볼|코인.*선택',
        '프리셋 선택': r'preset.*combo|프리셋',
        '레버리지 설정': r'leverage.*input|레버리지',
        '수동 청산': r'close.*btn|청산.*버튼|manual.*close',
        '새로고침': r'refresh|새로고침',
        '거래 내역': r'trade.*history|거래.*내역|TradeHistory',
    }
    
    for name, pattern in features.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "❌"} {name}: {found}곳')
    
    print('\n  🔗 Core 연동:')
    core_integration = {
        'UnifiedBot 사용': r'UnifiedBot|unified_bot',
        'ExchangeManager': r'ExchangeManager|exchange_manager',
        'LicenseGuard': r'LicenseGuard|license',
        'save_state/load_state': r'save_state|load_state',
    }
    
    for name, pattern in core_integration.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "⚠️"} {name}: {found}곳')

#############################################
# [2] Backtest Widget - 전략 검증
#############################################
print('\n' + '=' * 70)
print('📈 [2] Backtest Widget (backtest_widget.py)')
print('=' * 70)

bt_file = gui_path / 'backtest_widget.py'
if bt_file.exists():
    code = bt_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n  🎯 핵심 기능:')
    features = {
        '기간 선택 (시작/종료)': r'from.*date|to.*date|start.*date|end.*date|기간',
        '타임프레임 선택': r'timeframe|interval|타임프레임',
        '파라미터 입력 (ATR)': r'atr.*input|atr_mult',
        '파라미터 입력 (RSI)': r'rsi.*input|rsi_threshold',
        '파라미터 입력 (Trail)': r'trail.*input|trailing',
        '실행 버튼': r'run.*btn|backtest.*btn|실행',
        '진행률 표시': r'progress|QProgressBar',
        '결과 테이블': r'result.*table|QTableWidget',
        '승률 표시': r'win.*rate|승률',
        'PnL 표시': r'total.*pnl|누적.*수익',
        '차트 표시': r'chart|plot|pyqtgraph',
        '거래 목록': r'trade.*list|거래.*목록',
    }
    
    for name, pattern in features.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "❌"} {name}: {found}곳')
    
    print('\n  🔗 전략 연동:')
    strategy_integration = {
        'AlphaX7Core 사용': r'AlphaX7|strategy_core',
        'BacktestWorker': r'BacktestWorker|QThread',
        '지표 계산': r'indicator|rsi|atr|ema',
        'Parquet 로드': r'parquet|read_parquet',
    }
    
    for name, pattern in strategy_integration.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "⚠️"} {name}: {found}곳')

#############################################
# [3] Optimization Widget - 파라미터 최적화
#############################################
print('\n' + '=' * 70)
print('⚙️ [3] Optimization Widget (optimization_widget.py)')
print('=' * 70)

opt_file = gui_path / 'optimization_widget.py'
if opt_file.exists():
    code = opt_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n  🎯 핵심 기능:')
    features = {
        '파라미터 범위 (ATR)': r'atr.*range|atr.*min|atr.*max',
        '파라미터 범위 (RSI)': r'rsi.*range|rsi.*min|rsi.*max',
        '파라미터 범위 (Trail)': r'trail.*range|trail.*min',
        '스텝 설정': r'step|간격',
        'CPU 코어 선택': r'cpu|core|thread|병렬',
        '실행 버튼': r'run.*btn|optimize.*btn|시작',
        '진행률': r'progress|QProgressBar',
        '결과 테이블': r'result.*table|QTableWidget',
        '정렬/랭킹': r'sort|rank|best',
        '결과 저장': r'save.*result|export',
        '히트맵': r'heatmap|heat.*map',
    }
    
    for name, pattern in features.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "❌"} {name}: {found}곳')
    
    print('\n  🔗 병렬 처리:')
    parallel = {
        'OptimizationWorker': r'OptimizationWorker',
        'multiprocessing': r'multiprocessing|Pool',
        'concurrent': r'concurrent|ThreadPool',
        'Grid Search': r'grid|itertools|combinations',
    }
    
    for name, pattern in parallel.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "⚠️"} {name}: {found}곳')

#############################################
# [4] Data Collector - 데이터 수집
#############################################
print('\n' + '=' * 70)
print('📥 [4] Data Collector Widget (data_collector_widget.py)')
print('=' * 70)

dc_file = gui_path / 'data_collector_widget.py'
if dc_file.exists():
    code = dc_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n  🎯 핵심 기능:')
    features = {
        '거래소 선택': r'exchange.*combo|거래소',
        '심볼 입력': r'symbol.*input|심볼',
        '타임프레임 선택': r'timeframe|interval',
        '기간 선택': r'date.*edit|기간',
        '다운로드 버튼': r'download.*btn|다운로드',
        '진행률': r'progress|QProgressBar',
        'Top 10 스캔': r'top.*10|top10',
        'Gainers 스캔': r'gainer|상승',
        'Losers 스캔': r'loser|하락',
        'Parquet 저장': r'parquet|\.parquet',
        '캐시 관리': r'cache|캐시',
    }
    
    for name, pattern in features.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "❌"} {name}: {found}곳')
    
    print('\n  🔗 비동기 처리:')
    async_check = {
        'DownloadThread': r'DownloadThread',
        'ScannerWorker': r'ScannerWorker',
        'QThread': r'QThread',
    }
    
    for name, pattern in async_check.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "⚠️"} {name}: {found}곳')

#############################################
# [5] Settings Widget - 설정
#############################################
print('\n' + '=' * 70)
print('⚙️ [5] Settings Widget (settings_widget.py)')
print('=' * 70)

sw_file = gui_path / 'settings_widget.py'
if sw_file.exists():
    code = sw_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n  🎯 핵심 기능:')
    features = {
        'API Key 입력': r'api.*key|API.*Key',
        'Secret Key 입력': r'secret.*key|Secret',
        '거래소 선택': r'exchange.*combo|거래소',
        '연결 테스트': r'test.*connection|연결.*테스트',
        '저장 버튼': r'save.*btn|저장',
        '암호화 저장': r'encrypt|fernet|crypto',
        '텔레그램 설정': r'telegram|텔레그램',
        '알림 설정': r'notification|알림',
    }
    
    for name, pattern in features.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "❌"} {name}: {found}곳')
    
    print('\n  🔗 비동기 처리:')
    async_check = {
        'ConnectionWorker': r'ConnectionWorker',
        'QThread': r'QThread',
    }
    
    for name, pattern in async_check.items():
        found = len([l for l in lines if re.search(pattern, l, re.I)])
        print(f'    {"✅" if found else "⚠️"} {name}: {found}곳')

#############################################
# [6] 멀티 매매 관련 GUI
#############################################
print('\n' + '=' * 70)
print('🎯 [6] Multi Trading GUI')
print('=' * 70)

# multi 관련 위젯 찾기
multi_widgets = list(gui_path.glob('*multi*.py')) + list(gui_path.glob('*sniper*.py'))

if multi_widgets:
    for mw in multi_widgets:
        code = mw.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        
        print(f'\n  📄 {mw.name}:')
        features = {
            '심볼 리스트': r'symbol.*list|watch.*list|코인.*목록',
            '동시 진입 수': r'max.*position|동시.*진입',
            '스캔 시작/중지': r'start.*scan|stop.*scan|스캔',
            '상태 표시': r'status|상태',
            '개별 PnL': r'pnl|손익',
        }
        
        for name, pattern in features.items():
            found = len([l for l in lines if re.search(pattern, l, re.I)])
            print(f'    {"✅" if found else "❌"} {name}: {found}곳')
else:
    print('  ℹ️ Multi Trading 전용 위젯 없음')
    print('  → Trading Dashboard에서 통합 관리 가능성 확인 필요')

#############################################
# [7] 방향성 검증 - 우리가 원하는 기능
#############################################
print('\n' + '=' * 70)
print('🎯 [7] 방향성 검증 - 목표 기능 매칭')
print('=' * 70)

goals = {
    '실매매': {
        '자동 진입 (패턴 감지)': ('trading_dashboard.py', r'auto|자동.*진입|pattern'),
        '자동 청산 (SL/TP)': ('trading_dashboard.py', r'auto.*close|sl.*hit|tp.*hit'),
        '실시간 PnL': ('trading_dashboard.py', r'realtime.*pnl|실시간.*손익'),
        '포지션 동기화': ('trading_dashboard.py', r'sync.*position|동기화'),
    },
    '백테스트': {
        '과거 데이터 검증': ('backtest_widget.py', r'historical|과거'),
        '전략 파라미터 테스트': ('backtest_widget.py', r'param|parameter'),
        '결과 시각화': ('backtest_widget.py', r'chart|plot|시각화'),
        '승률/PnL 통계': ('backtest_widget.py', r'win.*rate|pnl|통계'),
    },
    '최적화': {
        '파라미터 범위 탐색': ('optimization_widget.py', r'range|범위'),
        '최적값 찾기': ('optimization_widget.py', r'best|optimal|최적'),
        '병렬 처리': ('optimization_widget.py', r'parallel|병렬|multi'),
    },
    '멀티 매매': {
        '다중 심볼 스캔': ('trading_dashboard.py', r'multi|다중|scan'),
        '동시 포지션 관리': ('trading_dashboard.py', r'position.*list|포지션.*목록'),
        '개별 PnL 추적': ('trading_dashboard.py', r'each.*pnl|개별'),
    },
}

for category, checks in goals.items():
    print(f'\n  📍 {category}:')
    for goal, (filename, pattern) in checks.items():
        f = gui_path / filename
        if f.exists():
            code = f.read_text(encoding='utf-8', errors='ignore')
            found = bool(re.search(pattern, code, re.I))
            print(f'    {"✅" if found else "⚠️"} {goal}')
        else:
            print(f'    ❌ {goal} (파일 없음)')

#############################################
# 최종 요약
#############################################
print('\n' + '=' * 70)
print('📊 위젯 기능 분석 완료')
print('=' * 70)
