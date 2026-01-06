import sys
sys.path.insert(0, r'C:\매매전략')

def check_module(module_path, class_name, required_funcs):
    print(f'=== {class_name} 기능 체크 ===')
    try:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        methods = dir(cls)
        
        results = []
        for func_name, patterns in required_funcs.items():
            matched = [p for p in patterns if p in methods]
            found = len(matched) > 0
            results.append((func_name, found, matched))
            status = '✅' if found else '❌'
            print(f'{func_name}: {status} {matched if matched else "없음"}')
        
        return results
    except Exception as e:
        print(f'❌ 로드 실패: {e}')
        return []

def main():
    all_results = {}
    
    # 1. BotStateManager
    all_results['BotStateManager'] = check_module('core.bot_state', 'BotStateManager', {
        '상태 저장': ['save_state', 'save'],
        '상태 로드': ['load_state', 'load'],
        '캐시 저장': ['save_cache', '_save_cache'],
        '캐시 로드': ['load_cache', '_load_cache'],
        '거래 기록': ['save_trade', 'save_trade_history'],
        '포지션 관리': ['add_managed_position', 'managed_positions'],
        '포지션 제거': ['remove_managed_position'],
        '포지션 확인': ['is_managed_position', 'get_managed_position']
    })
    print()
    
    # 2. BotDataManager
    all_results['BotDataManager'] = check_module('core.data_manager', 'BotDataManager', {
        '히스토리 로드': ['load_historical', 'load_full', '_load_full'],
        '데이터 처리': ['process_data', 'process_all', '_process'],
        '캔들 추가': ['append_candle', 'add_candle', '_append'],
        '지표 업데이트': ['update_indicators', '_update_indicators'],
        '백필': ['backfill', '_backfill'],
        'Parquet 저장': ['save_parquet', '_save_to_parquet', 'save_to_parquet'],
        'Parquet 로드': ['load_parquet', '_load_from_parquet'],
        '리샘플링': ['resample', '_resample']
    })
    print()
    
    # 3. SignalProcessor
    all_results['SignalProcessor'] = check_module('core.signal_processor', 'SignalProcessor', {
        '시그널 감지': ['detect_signal', 'detect', 'check_signal'],
        '패턴 추가': ['add_patterns', 'add_patterns_from_df', '_add_patterns'],
        '시그널 필터': ['filter_signals', '_filter_valid', 'filter_valid'],
        '시그널 큐': ['add_to_queue', '_add_signal_to_queue', 'signal_queue'],
        '큐에서 확인': ['check_from_queue', '_check_entry_from_queue'],
        '조건 확인': ['get_trading_conditions', '_get_current_trading'],
        '만료 처리': ['expire_signals', 'remove_expired', '_expire']
    })
    print()
    
    # 4. OrderExecutor
    all_results['OrderExecutor'] = check_module('core.order_executor', 'OrderExecutor', {
        '진입 실행': ['execute_entry', 'entry', 'open_position'],
        '청산 실행': ['execute_close', 'close', 'close_position'],
        '추가 진입': ['execute_add', 'add_position'],
        'PnL 계산': ['calculate_pnl', '_calculate_pnl', 'pnl'],
        '주문 재시도': ['place_order_with_retry', '_place_order', 'retry'],
        '레버리지 설정': ['set_leverage', '_set_leverage'],
        '거래 기록': ['record_trade', '_record_trade', 'log_trade'],
        '가상 주문 (Dry)': ['_create_virtual', 'virtual', 'dry_run']
    })
    print()
    
    # 5. PositionManager
    all_results['PositionManager'] = check_module('core.position_manager', 'PositionManager', {
        '포지션 관리': ['manage', 'manage_position', '_manage'],
        '실시간 관리': ['manage_live', '_manage_position_live'],
        '진입 체크': ['check_entry', '_check_entry_live', 'should_enter'],
        '거래소 동기화': ['sync_with_exchange', 'sync', '_sync'],
        'SL 히트 체크': ['check_sl', '_check_sl_hit', 'sl_hit'],
        '트레일링 SL': ['update_trailing', '_update_trailing_sl', 'trailing'],
        '추가 진입 조건': ['should_add', '_should_add_position'],
        '청산 조건': ['should_close', 'close_on_sl', '_close_on_sl'],
        '가상 포지션 (Dry)': ['_get_virtual', 'virtual_positions', 'dry_run']
    })
    print()
    
    # Summary
    print('=' * 60)
    print('=== 전체 요약 ===')
    print(f'{"모듈":<25} {"통과":<10} {"실패":<10}')
    print('-' * 50)
    
    missing_funcs = []
    for module, results in all_results.items():
        passed = sum(1 for r in results if r[1])
        failed = sum(1 for r in results if not r[1])
        total = len(results)
        status = '✅' if failed == 0 else '⚠️'
        print(f'{module:<25} {passed}/{total:<8} {failed:<10} {status}')
        
        for func_name, found, _ in results:
            if not found:
                missing_funcs.append((module, func_name))
    
    if missing_funcs:
        print()
        print('=== 누락된 기능 ===')
        for module, func in missing_funcs:
            print(f'  ❌ {module}: {func}')

if __name__ == "__main__":
    main()
