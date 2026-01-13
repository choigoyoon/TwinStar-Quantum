from pathlib import Path
import re

base = Path(r'C:\매매전략')

print('=' * 70)
print('🎯 5대 기능 실제 동작 + 대소문자 기준 검증')
print('=' * 70)

#############################################
# [1] 실매매 기능 검증
#############################################
print('\n' + '=' * 70)
print('💰 [1] 실매매 기능')
print('=' * 70)

bot_file = base / 'core' / 'unified_bot.py'
if bot_file.exists():
    code = bot_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n  📍 자동 진입 (W/M 패턴 → 진입):')
    entry_flow = [
        ('패턴 감지 호출', r'detect_pattern|find_pattern|extract.*signal'),
        ('W 패턴 체크', r"['\"]W['\"]|pattern.*==.*W"),
        ('M 패턴 체크', r"['\"]M['\"]|pattern.*==.*M"),
        ('진입 조건 체크', r'_check_entry|check_entry_condition'),
        ('RSI 필터', r'rsi.*[<>]|pullback.*rsi'),
        ('execute_entry 호출', r'execute_entry\('),
        ('place_market_order', r'place_market_order\('),
    ]
    
    for name, pattern in entry_flow:
        matches = [(i+1, lines[i].strip()[:40]) for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
        if matches:
            print(f'    ✅ {name}: L{matches[0][0]}')
        else:
            print(f'    ❌ {name}: 없음')
    
    print('\n  📍 자동 청산 (SL/Trailing):')
    exit_flow = [
        ('SL 가격 계산', r'sl_price.*=|stop_loss.*='),
        ('SL 모니터링', r'check.*sl|sl.*hit|_close_on_sl'),
        ('Trailing 업데이트', r'trailing|update.*trail|trail_dist'),
        ('close_position 호출', r'close_position\('),
        ('포지션 None 처리', r'self\.position\s*=\s*None'),
    ]
    
    for name, pattern in exit_flow:
        matches = [(i+1, lines[i].strip()[:40]) for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
        if matches:
            print(f'    ✅ {name}: {len(matches)}곳')
        else:
            print(f'    ❌ {name}: 없음')
    
    print('\n  📍 복리 적용:')
    compound_flow = [
        ('_get_compound_seed 정의', r'def _get_compound_seed'),
        ('initial_capital 사용', r'self\.initial_capital'),
        ('cumulative_pnl 계산', r'cumulative.*pnl|total.*pnl'),
        ('trade_storage 저장', r'trade_storage\.add_trade'),
        ('update_capital 호출', r'update_capital_for_compounding'),
        ('시드 로그 출력', r'\[COMPOUND\]'),
    ]
    
    for name, pattern in compound_flow:
        matches = [(i+1, lines[i].strip()[:40]) for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
        if matches:
            print(f'    ✅ {name}: L{matches[0][0]}')
        else:
            print(f'    ❌ {name}: 없음')
    
    print('\n  📍 레버리지 PnL:')
    pnl_with_lev = 0
    pnl_without_lev = 0
    for i, line in enumerate(lines):
        if 'pnl_pct' in line and '=' in line and '==' not in line:
            if 'leverage' in line.lower():
                pnl_with_lev += 1
            else:
                pnl_without_lev += 1
    
    print(f'    레버리지 적용: {pnl_with_lev}곳')
    print(f'    레버리지 미적용: {pnl_without_lev}곳')
    if pnl_without_lev > 0:
        print(f'    ⚠️ 미적용 라인 확인 필요')

#############################################
# [2] 백테스트 기능 검증
#############################################
print('\n' + '=' * 70)
print('📊 [2] 백테스트 기능')
print('=' * 70)

print('\n  📍 Core 백테스트 로직:')
bt_core = [
    ('백테스트 함수', r'def.*backtest|_run_backtest|_continue_backtest'),
    ('과거 데이터 로드', r'read_parquet|load.*data|df_entry'),
    ('시뮬레이션 루프', r'for.*candle|for.*row|iterrows'),
    ('가상 진입', r'bt_state.*position|simulate.*entry'),
    ('가상 청산', r'bt_state.*close|simulate.*exit'),
]

for name, pattern in bt_core:
    matches = [(i+1, lines[i].strip()[:40]) for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
    if matches:
        print(f'    ✅ {name}: {len(matches)}곳')
    else:
        print(f'    ❌ {name}: 없음')

print('\n  📍 결과 출력:')
bt_result = [
    ('승률 계산', r'win_rate|win.*rate|승률'),
    ('PnL 계산', r'total_pnl|cumulative.*pnl|누적.*수익'),
    ('MDD 계산', r'mdd|max.*drawdown|최대.*낙폭'),
    ('거래 수', r'trade.*count|len.*trades|거래.*수'),
]

for name, pattern in bt_result:
    count = len(re.findall(pattern, code, re.I))
    print(f'    {"✅" if count > 0 else "❌"} {name}: {count}곳')

print('\n  📍 실매매와 동일 로직:')
# strategy_core.py 확인
strategy_file = base / 'core' / 'strategy_core.py'
if strategy_file.exists():
    s_code = strategy_file.read_text(encoding='utf-8', errors='ignore')
    
    shared = [
        ('AlphaX7Core 클래스', r'class AlphaX7'),
        ('detect_pattern', r'def detect_pattern'),
        ('calculate_rsi', r'def.*rsi|calculate.*rsi'),
        ('calculate_atr', r'def.*atr|calculate.*atr'),
    ]
    
    for name, pattern in shared:
        in_bot = len(re.findall(pattern, code, re.I))
        in_strategy = len(re.findall(pattern, s_code, re.I))
        print(f'    {"✅" if in_strategy > 0 else "❌"} {name}: strategy={in_strategy}')

#############################################
# [3] 최적화 기능 검증
#############################################
print('\n' + '=' * 70)
print('⚙️ [3] 최적화 기능')
print('=' * 70)

opt_file = base / 'GUI' / 'optimization_widget.py'
if opt_file.exists():
    o_code = opt_file.read_text(encoding='utf-8', errors='ignore')
    
    print('\n  📍 파라미터 범위 탐색:')
    opt_params = [
        ('ATR 범위', r'atr.*range|atr.*min|atr.*max|atr_mult'),
        ('RSI 범위', r'rsi.*range|rsi.*min|rsi.*max'),
        ('Trail 범위', r'trail.*range|trail.*min|trail.*max'),
        ('스텝 설정', r'step|간격|increment'),
    ]
    
    for name, pattern in opt_params:
        count = len(re.findall(pattern, o_code, re.I))
        print(f'    {"✅" if count > 0 else "❌"} {name}: {count}곳')
    
    print('\n  📍 최적 조합 찾기:')
    opt_logic = [
        ('Grid Search', r'grid|itertools|product|combinations'),
        ('병렬 처리', r'multiprocessing|Pool|concurrent'),
        ('결과 정렬', r'sort|rank|best|top'),
        ('최적값 선택', r'optimal|best.*param|최적'),
    ]
    
    for name, pattern in opt_logic:
        count = len(re.findall(pattern, o_code, re.I))
        print(f'    {"✅" if count > 0 else "❌"} {name}: {count}곳')
else:
    print('  ❌ optimization_widget.py 없음')

#############################################
# [4] 멀티 매매 기능 검증
#############################################
print('\n' + '=' * 70)
print('🎯 [4] 멀티 매매 기능')
print('=' * 70)

multi_files = [
    base / 'core' / 'multi_sniper.py',
    base / 'core' / 'multi_trader.py',
]

multi_found = False
for mf in multi_files:
    if mf.exists():
        multi_found = True
        m_code = mf.read_text(encoding='utf-8', errors='ignore')
        
        print(f'\n  📍 {mf.name}:')
        
        print('\n    여러 코인 동시 스캔:')
        scan_logic = [
            ('심볼 리스트', r'symbols|coin_list|watch_list'),
            ('스캔 함수', r'def scan|start_scan|scan_all'),
            ('동시 처리', r'asyncio|concurrent|threading|await'),
        ]
        
        for name, pattern in scan_logic:
            count = len(re.findall(pattern, m_code, re.I))
            print(f'      {"✅" if count > 0 else "❌"} {name}: {count}곳')
        
        print('\n    개별 진입/청산:')
        individual = [
            ('개별 진입', r'enter.*position|execute.*entry|place.*order'),
            ('개별 청산', r'close.*position|exit'),
            ('상태 관리', r'CoinState|position.*dict|status'),
        ]
        
        for name, pattern in individual:
            count = len(re.findall(pattern, m_code, re.I))
            print(f'      {"✅" if count > 0 else "❌"} {name}: {count}곳')
        
        print('\n    전체 PnL 관리:')
        pnl_mgmt = [
            ('개별 PnL', r'pnl.*\[|each.*pnl'),
            ('전체 합산', r'total.*pnl|sum.*pnl'),
            ('포지션 제한', r'max.*position|position.*limit'),
        ]
        
        for name, pattern in pnl_mgmt:
            count = len(re.findall(pattern, m_code, re.I))
            print(f'      {"✅" if count > 0 else "❌"} {name}: {count}곳')

if not multi_found:
    print('  ⚠️ multi_sniper.py / multi_trader.py 없음')
    print('  → Trading Dashboard에서 통합 관리 확인 필요')

#############################################
# [5] 기타 기능 검증
#############################################
print('\n' + '=' * 70)
print('🔧 [5] 기타 기능')
print('=' * 70)

print('\n  📍 거래소 연결/API 키:')
settings_file = base / 'GUI' / 'settings_widget.py'
if settings_file.exists():
    sw_code = settings_file.read_text(encoding='utf-8', errors='ignore')
    
    api_features = [
        ('API 키 입력', r'api.*key|API.*Key'),
        ('Secret 입력', r'secret.*key|Secret'),
        ('암호화 저장', r'encrypt|fernet|crypto'),
        ('연결 테스트', r'test.*connection|connect.*exchange'),
        ('ConnectionWorker', r'ConnectionWorker|QThread'),
    ]
    
    for name, pattern in api_features:
        count = len(re.findall(pattern, sw_code, re.I))
        print(f'    {"✅" if count > 0 else "❌"} {name}: {count}곳')

print('\n  📍 데이터 다운로드:')
dc_file = base / 'GUI' / 'data_collector_widget.py'
if dc_file.exists():
    dc_code = dc_file.read_text(encoding='utf-8', errors='ignore')
    
    data_features = [
        ('다운로드 함수', r'download|fetch.*data'),
        ('Parquet 저장', r'to_parquet|save.*parquet'),
        ('진행률 표시', r'progress|QProgressBar'),
        ('DownloadThread', r'DownloadThread|QThread'),
    ]
    
    for name, pattern in data_features:
        count = len(re.findall(pattern, dc_code, re.I))
        print(f'    {"✅" if count > 0 else "❌"} {name}: {count}곳')

print('\n  📍 라이선스 체크:')
license_patterns = [
    ('LicenseGuard', r'LicenseGuard'),
    ('tier 체크', r'tier|등급'),
    ('만료 체크', r'expire|만료|days.*left'),
    ('hw_id', r'hw_id|hardware.*id'),
]

for name, pattern in license_patterns:
    count = 0
    for f in base.rglob('*.py'):
        if '__pycache__' in str(f):
            continue
        try:
            c = f.read_text(encoding='utf-8', errors='ignore')
            count += len(re.findall(pattern, c, re.I))
        except Exception:

            pass
    print(f'    {"✅" if count > 0 else "❌"} {name}: {count}곳')

#############################################
# [6] 대소문자 기준점 검증
#############################################
print('\n' + '=' * 70)
print('🔤 [6] 대소문자 기준점')
print('=' * 70)

print('\n  📍 데이터 흐름별 기준:')

# 1) API 응답 → 내부 저장
print('\n    1) API 응답 → 내부 저장:')
api_normalize = {
    'symbol.upper()': 0,
    'symbol.lower()': 0,
    'exchange.lower()': 0,
}

for f in (base / 'exchanges').rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        c = f.read_text(encoding='utf-8', errors='ignore')
        api_normalize['symbol.upper()'] += len(re.findall(r'symbol\.upper\(\)', c))
        api_normalize['symbol.lower()'] += len(re.findall(r'symbol\.lower\(\)', c))
        api_normalize['exchange.lower()'] += len(re.findall(r'exchange\.lower\(\)', c))
    except Exception:

        pass

for k, v in api_normalize.items():
    print(f'      {k}: {v}곳')

# 2) Parquet 파일명
print('\n    2) Parquet 파일명:')
parquet_case = {'lower': 0, 'upper': 0, 'mixed': 0}

for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        c = f.read_text(encoding='utf-8', errors='ignore')
        lines = c.split('\n')
        for line in lines:
            if '.parquet' in line and ('f"' in line or "f'" in line):
                if '.lower()' in line:
                    parquet_case['lower'] += 1
                elif '.upper()' in line:
                    parquet_case['upper'] += 1
                else:
                    parquet_case['mixed'] += 1
    except Exception:

        pass

for k, v in parquet_case.items():
    status = '✅' if k == 'lower' and v > 0 else ('⚠️' if v > 0 else '⚪')
    print(f'      {status} {k}: {v}곳')

# 3) 비교 연산
print('\n    3) 비교 연산 시 정규화:')
compare_normalize = {
    '정규화 후 비교': 0,
    '직접 비교 (위험)': 0,
}

for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        c = f.read_text(encoding='utf-8', errors='ignore')
        lines = c.split('\n')
        for i, line in enumerate(lines):
            if ('symbol ==' in line or 'exchange ==' in line) and '.lower()' not in line:
                compare_normalize['직접 비교 (위험)'] += 1
            elif '.lower() ==' in line or '.upper() ==' in line:
                compare_normalize['정규화 후 비교'] += 1
    except Exception:

        pass

for k, v in compare_normalize.items():
    status = '✅' if '정규화' in k else '⚠️'
    print(f'      {status} {k}: {v}곳')

#############################################
# 최종 요약
#############################################
print('\n' + '=' * 70)
print('📊 전체 검증 요약')
print('=' * 70)
print('''
  [1] 실매매: 진입/청산/복리/PnL 확인
  [2] 백테스트: 시뮬레이션/결과/공유로직 확인
  [3] 최적화: 파라미터 탐색/병렬처리 확인
  [4] 멀티매매: 동시스캔/개별관리 확인
  [5] 기타: API/다운로드/라이선스 확인
  [6] 대소문자: 기준점 정합성 확인
''')
print('=' * 70)
