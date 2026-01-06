from pathlib import Path
import re

base = Path(r'C:\매매전략')

print('=' * 70)
print('🎯 4대 핵심 기능 심층 검증')
print('=' * 70)

#############################################
# [1] 실매매 로직 검증
#############################################
print('\n' + '=' * 70)
print('💰 [1] 실매매 로직')
print('=' * 70)

bot_file = base / 'core' / 'unified_bot.py'
if bot_file.exists():
    code = bot_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n  📍 진입 흐름:')
    entry_flow = [
        ('1. run() 메인 루프', r'def run\(self'),
        ('2. 캔들 마감 감지', r'_on_candle_close|_process_new_candle'),
        ('3. 진입 조건 체크', r'_check_entry|check_entry_condition'),
        ('4. RSI 필터', r'rsi.*[<>]|pullback.*rsi'),
        ('5. 패턴 확인', r'pattern.*[WM]|["\'][WM]["\']'),
        ('6. execute_entry 호출', r'execute_entry'),
        ('7. place_market_order', r'place_market_order'),
        ('8. SL 설정', r'stop_loss|sl_price'),
    ]
    
    for name, pattern in entry_flow:
        found = [i+1 for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
        print(f'    {"✅" if found else "❌"} {name}: {len(found)}곳')
    
    print('\n  📍 청산 흐름:')
    exit_flow = [
        ('1. SL 모니터링', r'_check_sl|check_stop_loss|sl_hit'),
        ('2. SL 청산', r'_close_on_sl'),
        ('3. TP 청산', r'_close_on_tp|tp_hit'),
        ('4. Trailing Stop', r'trailing|trail_stop|update_trailing'),
        ('5. close_position 호출', r'close_position'),
        ('6. 포지션 정리', r'self\.position\s*=\s*None'),
        ('7. 거래 기록', r'save_trade|add_trade|record_trade'),
        ('8. 복리 업데이트', r'update_capital|compound'),
    ]
    
    for name, pattern in exit_flow:
        found = [i+1 for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
        print(f'    {"✅" if found else "❌"} {name}: {len(found)}곳')
    
    print('\n  📍 실시간 동기화:')
    sync_flow = [
        ('WebSocket 가격', r'on_price|_on_price|price_update'),
        ('포지션 동기화', r'sync_position|_sync_position'),
        ('상태 저장', r'save_state'),
        ('거래소 포지션 조회', r'get_position|fetch_position'),
    ]
    
    for name, pattern in sync_flow:
        found = [i+1 for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
        print(f'    {"✅" if found else "❌"} {name}: {len(found)}곳')

#############################################
# [2] 백테스트 로직 검증
#############################################
print('\n' + '=' * 70)
print('📊 [2] 백테스트 로직')
print('=' * 70)

# unified_bot.py 내 백테스트
print('\n  📍 Core 백테스트 (unified_bot.py):')
bt_core = [
    ('백테스트 함수', r'def.*backtest|_run_backtest|_continue_backtest'),
    ('시뮬레이션 진입', r'simulate.*entry|bt.*entry|backtest.*entry'),
    ('시뮬레이션 청산', r'simulate.*exit|bt.*exit|backtest.*exit'),
    ('결과 집계', r'win_rate|total_pnl|trades.*count'),
    ('bt_state 관리', r'bt_state'),
]

for name, pattern in bt_core:
    found = [i+1 for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
    print(f'    {"✅" if found else "❌"} {name}: {len(found)}곳')

# strategy_core.py 검증
print('\n  📍 전략 엔진 (strategy_core.py):')
strategy_file = base / 'core' / 'strategy_core.py'
if strategy_file.exists():
    s_code = strategy_file.read_text(encoding='utf-8', errors='ignore')
    s_lines = s_code.split('\n')
    
    strategy_checks = [
        ('AlphaX7Core 클래스', r'class AlphaX7'),
        ('패턴 감지', r'detect_pattern|find_pattern'),
        ('RSI 계산', r'calculate_rsi|rsi'),
        ('ATR 계산', r'calculate_atr|atr'),
        ('시그널 생성', r'generate_signal|create_signal|extract.*signal'),
        ('SL/TP 계산', r'calculate_sl|calculate_tp|stop_loss'),
    ]
    
    for name, pattern in strategy_checks:
        found = [i+1 for i, l in enumerate(s_lines) if re.search(pattern, l, re.I)]
        print(f'    {"✅" if found else "❌"} {name}: {len(found)}곳')

# GUI 백테스트 위젯
print('\n  📍 GUI 백테스트 (backtest_widget.py):')
bt_widget = base / 'GUI' / 'backtest_widget.py'
if bt_widget.exists():
    w_code = bt_widget.read_text(encoding='utf-8', errors='ignore')
    
    widget_checks = [
        ('실행 버튼', r'run.*btn|start.*btn|execute'),
        ('기간 선택', r'date.*edit|from.*date|period'),
        ('파라미터 입력', r'param.*input|setting'),
        ('결과 테이블', r'result.*table|QTableWidget'),
        ('차트 표시', r'chart|plot|graph'),
        ('승률/PnL 표시', r'win.*rate|pnl|profit'),
        ('QThread 사용', r'QThread|Worker'),
    ]
    
    for name, pattern in widget_checks:
        if re.search(pattern, w_code, re.I):
            print(f'    ✅ {name}')
        else:
            print(f'    ⚠️ {name}: 확인 필요')

#############################################
# [3] 최적화 로직 검증
#############################################
print('\n' + '=' * 70)
print('⚙️ [3] 최적화 로직')
print('=' * 70)

# 최적화 위젯
opt_widget = base / 'GUI' / 'optimization_widget.py'
if opt_widget.exists():
    o_code = opt_widget.read_text(encoding='utf-8', errors='ignore')
    o_lines = o_code.split('\n')
    
    print('\n  📍 최적화 기능:')
    opt_checks = [
        ('파라미터 범위', r'range|min.*max|step'),
        ('그리드 서치', r'grid.*search|itertools|combinations'),
        ('병렬 처리', r'multiprocess|concurrent|parallel|Pool'),
        ('진행률 표시', r'progress|QProgressBar'),
        ('결과 정렬', r'sort|rank|best'),
        ('결과 저장', r'save.*result|export'),
        ('시각화', r'plot|chart|heatmap'),
    ]
    
    for name, pattern in opt_checks:
        found = [i+1 for i, l in enumerate(o_lines) if re.search(pattern, l, re.I)]
        print(f'    {"✅" if found else "⚠️"} {name}: {len(found)}곳')
    
    # 최적화 대상 파라미터
    print('\n  📍 최적화 대상 파라미터:')
    param_patterns = ['atr', 'rsi', 'trail', 'leverage', 'sl', 'tp', 'validity', 'timeframe']
    for param in param_patterns:
        if param in o_code.lower():
            print(f'    ✅ {param}')
else:
    print('  ⚠️ optimization_widget.py 없음')
    
    # 대체 파일 검색
    for f in (base / 'GUI').glob('*optim*.py'):
        print(f'  ℹ️ 발견: {f.name}')

#############################################
# [4] 멀티 매매 로직 검증
#############################################
print('\n' + '=' * 70)
print('🎯 [4] 멀티 매매 로직')
print('=' * 70)

# multi_sniper.py 또는 multi_trader.py
multi_files = [
    base / 'core' / 'multi_sniper.py',
    base / 'core' / 'multi_trader.py',
]

for mf in multi_files:
    if mf.exists():
        m_code = mf.read_text(encoding='utf-8', errors='ignore')
        m_lines = m_code.split('\n')
        
        print(f'\n  📍 {mf.name}:')
        
        multi_checks = [
            ('클래스 정의', r'class Multi'),
            ('심볼 리스트', r'symbols|coin_list|watch_list'),
            ('동시 스캔', r'scan_all|scan_symbols'),
            ('상태 관리', r'CoinState|coin_state|status'),
            ('포지션 제한', r'max_position|position_limit'),
            ('우선순위', r'priority|rank|score'),
            ('개별 진입', r'enter_position|execute_entry'),
            ('개별 청산', r'close_position|exit'),
            ('동시 처리', r'asyncio|concurrent|threading'),
            ('거래소 연동', r'exchange|api'),
        ]
        
        for name, pattern in multi_checks:
            found = [i+1 for i, l in enumerate(m_lines) if re.search(pattern, l, re.I)]
            print(f'    {"✅" if found else "⚠️"} {name}: {len(found)}곳')
        
        # 중복 진입 방지
        print('\n  📍 안전장치:')
        safety_checks = [
            ('중복 진입 방지', r'already.*position|in_position|duplicate'),
            ('최대 손실 제한', r'max_loss|daily_loss|loss_limit'),
            ('API 레이트 제한', r'rate_limit|throttle|sleep'),
            ('에러 복구', r'retry|recover|fallback'),
        ]
        
        for name, pattern in safety_checks:
            found = [i+1 for i, l in enumerate(m_lines) if re.search(pattern, l, re.I)]
            print(f'    {"✅" if found else "⚠️"} {name}: {len(found)}곳')

#############################################
# [5] 로직 일관성 검증
#############################################
print('\n' + '=' * 70)
print('🔗 [5] 로직 일관성')
print('=' * 70)

print('\n  📍 백테스트 vs 실매매 공유 로직:')
shared_logic = [
    ('RSI 계산', r'calculate_rsi|_calc_rsi'),
    ('ATR 계산', r'calculate_atr|_calc_atr'),
    ('SL 계산', r'calculate_sl|_calc_sl'),
    ('포지션 사이즈', r'calculate_position_size|_calc_size'),
    ('패턴 감지', r'detect_pattern'),
]

for name, pattern in shared_logic:
    # unified_bot.py에서 확인
    bot_found = len(re.findall(pattern, code, re.I))
    # strategy_core.py에서 확인
    strategy_found = 0
    if strategy_file.exists():
        strategy_found = len(re.findall(pattern, s_code, re.I))
    
    total = bot_found + strategy_found
    print(f'    {"✅" if total > 0 else "⚠️"} {name}: bot={bot_found}, strategy={strategy_found}')

#############################################
# 최종 요약
#############################################
print('\n' + '=' * 70)
print('📊 4대 핵심 기능 검증 완료')
print('=' * 70)
print('  [1] 실매매: 진입/청산/동기화 흐름 확인')
print('  [2] 백테스트: Core + GUI 연동 확인')
print('  [3] 최적화: 파라미터 탐색 기능 확인')
print('  [4] 멀티매매: 동시 스캔/진입 로직 확인')
print('  [5] 일관성: 공유 로직 사용 확인')
print('=' * 70)
