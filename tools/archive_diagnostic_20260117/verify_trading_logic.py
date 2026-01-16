import sys
import inspect
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def check_features(source, features, title):
    print(f'=== {title} ===')
    missing = []
    for feature, patterns in features.items():
        found = any(p in source for p in patterns)
        status = '✅' if found else '❌'
        print(f'  {feature}: {status}')
        if not found:
            missing.append(feature)
    print()
    return missing

def main():
    all_missing = {}
    
    # 1. Signal Processor
    from core.signal_processor import SignalProcessor
    sp_source = inspect.getsource(SignalProcessor)
    missing = check_features(sp_source, {
        '패턴 감지': ['pattern', 'Pattern', 'detect_pattern'],
        'MACD 크로스': ['macd', 'MACD', 'cross'],
        'RSI 조건': ['rsi', 'RSI'],
        'ATR 기반 SL': ['atr', 'ATR', 'stop_loss'],
        'EMA 트렌드': ['ema', 'EMA', 'trend'],
        '다중 타임프레임': ['mtf', 'MTF', 'timeframe', '4h', '1h'],
        '시그널 큐': ['queue', 'pending', 'signal_queue'],
        '시그널 만료': ['expire', 'validity', 'hours'],
        '방향 필터': ['direction', 'Long', 'Short', 'Both'],
        '풀백 진입': ['pullback', 'Pullback', 'retracement']
    }, '1. 시그널 생성 로직')
    if missing: all_missing['SignalProcessor'] = missing
    
    # 2. Entry Conditions (SignalProcessor + PositionManager)
    from core.position_manager import PositionManager
    pm_source = inspect.getsource(PositionManager)
    combined = sp_source + pm_source
    missing = check_features(combined, {
        '패턴 유효성': ['valid', 'validity', 'is_valid'],
        '진입가 계산': ['entry_price', 'entry', 'price'],
        'SL 계산': ['stop_loss', 'sl', 'SL'],
        '포지션 사이즈': ['size', 'amount', 'quantity'],
        'R:R 비율': ['risk', 'reward', 'rr', 'R:R'],
        'RSI 필터': ['rsi', 'RSI', 'pullback_rsi'],
        '트렌드 확인': ['trend', 'Trend', 'mtf'],
        '기존 포지션 체크': ['position', 'has_position', 'no_position'],
        '최대 추가 진입': ['max_adds', 'add_count', 'max_position']
    }, '2. 진입 조건 로직')
    if missing: all_missing['EntryConditions'] = missing
    
    # 3. Order Executor
    from core.order_executor import OrderExecutor
    oe_source = inspect.getsource(OrderExecutor)
    missing = check_features(oe_source, {
        '시장가 주문': ['market', 'Market', 'MARKET'],
        '레버리지 설정': ['leverage', 'set_leverage'],
        'SL 설정': ['stop_loss', 'set_sl', 'update_stop'],
        '재시도 로직': ['retry', 'attempt', 'max_retries'],
        'PnL 계산': ['pnl', 'PnL', 'profit', 'calculate_pnl'],
        '수수료 반영': ['fee', 'commission'],
        '슬리피지': ['slippage', 'slip'],
        'Dry-run 모드': ['dry_run', 'dry', 'simulation'],
        '가상 주문': ['virtual', 'Virtual', 'DRY'],
        '거래 기록': ['record', 'trade_history', 'save_trade']
    }, '3. 주문 실행 로직')
    if missing: all_missing['OrderExecutor'] = missing
    
    # 4. Position Manager
    missing = check_features(pm_source, {
        '트레일링 SL': ['trailing', 'trail', 'update_trailing'],
        'SL 히트 체크': ['sl_hit', 'stop_hit', 'check_sl'],
        '익절 조건': ['take_profit', 'tp', 'profit_target'],
        '추가 진입': ['add', 'add_position', 'pyramid'],
        '부분 청산': ['partial', 'reduce', 'scale_out'],
        '전체 청산': ['close', 'exit', 'liquidate'],
        '거래소 동기화': ['sync', 'exchange', 'sync_with'],
        'Long/Short 분기': ['Long', 'Short', 'side'],
        '극단가 추적': ['extreme', 'high_water', 'peak'],
        'R 배수 계산': ['r_mult', 'R', 'risk_reward']
    }, '4. 포지션 관리 로직')
    if missing: all_missing['PositionManager'] = missing
    
    # 5. Data Manager
    from core.data_manager import BotDataManager
    dm_source = inspect.getsource(BotDataManager)
    missing = check_features(dm_source, {
        'Parquet 저장': ['parquet', 'Parquet', 'to_parquet'],
        'Parquet 로드': ['read_parquet', 'load_parquet', 'from_parquet'],
        '캔들 추가': ['append', 'add_candle', 'new_candle'],
        '리샘플링': ['resample', 'Resample', 'timeframe'],
        '지표 계산': ['indicator', 'calculate', 'RSI', 'ATR', 'MACD'],
        '백필': ['backfill', 'fill_gap', 'missing'],
        '캐시': ['cache', 'indicator_cache'],
        '15분봉': ['15m', '15min', 'entry'],
        '1시간봉': ['1h', '60', 'pattern'],
        '4시간봉': ['4h', '240', 'trend']
    }, '5. 데이터 관리 로직')
    if missing: all_missing['DataManager'] = missing
    
    # 6. State Manager
    from core.bot_state import BotStateManager
    bs_source = inspect.getsource(BotStateManager)
    missing = check_features(bs_source, {
        '상태 저장': ['save_state', 'save', 'dump'],
        '상태 로드': ['load_state', 'load', 'read'],
        '원자적 쓰기': ['atomic', 'temp', 'replace', 'fsync'],
        '거래 기록': ['trade', 'history', 'save_trade'],
        '포지션 추적': ['managed_position', 'position'],
        '캐시 관리': ['cache', 'load_cache', 'save_cache'],
        'JSON 직렬화': ['json', 'JSON', 'dumps'],
        '타임스탬프': ['timestamp', 'datetime', 'time'],
        '심볼별 분리': ['symbol', 'Symbol'],
        '거래소별 분리': ['exchange', 'Exchange']
    }, '6. 상태 관리 로직')
    if missing: all_missing['StateManager'] = missing
    
    # 7. Unified Bot Flow
    with open(r'C:\매매전략\core\unified_bot.py', 'r', encoding='utf-8') as f:
        ub_source = f.read()
    missing = check_features(ub_source, {
        '1. 데이터 로드': ['_init_indicator_cache', 'load_historical'],
        '2. 지표 계산': ['process_data', '_process_historical'],
        '3. 패턴 감지': ['add_patterns', 'pattern'],
        '4. 시그널 생성': ['detect_signal', 'get_trading_conditions'],
        '5. 진입 체크': ['check_entry', 'can_trade'],
        '6. 주문 실행': ['execute_entry', 'mod_order'],
        '7. 포지션 관리': ['manage_position', 'mod_position'],
        '8. SL/청산': ['execute_close', 'close'],
        '9. 상태 저장': ['save_state', 'mod_state'],
        '10. 동기화': ['sync_position', 'sync']
    }, '7. 전체 매매 흐름')
    if missing: all_missing['UnifiedBotFlow'] = missing
    
    # Summary
    print('=' * 60)
    print('=== 전체 요약 ===')
    if all_missing:
        print(f'❌ 누락된 기능 발견:')
        for module, features in all_missing.items():
            print(f'  [{module}]')
            for f in features:
                print(f'    - {f}')
    else:
        print('✅ 모든 매매 로직이 정상적으로 분리되어 있습니다.')

if __name__ == "__main__":
    main()
