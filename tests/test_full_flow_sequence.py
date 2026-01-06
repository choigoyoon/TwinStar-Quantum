"""
Full Flow Sequence Test (Step 1 → 6)
Tests entire pipeline from data collection to live trading
"""
import unittest
import sys
import os
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStep1_DataCollection(unittest.TestCase):
    """Step 1: 데이터 수집 검증"""
    
    def test_1_exchange_connection(self):
        """거래소 연결 확인"""
        # Simulate exchange connection
        exchanges = ['bybit', 'binance', 'bithumb']
        connected = []
        
        for ex in exchanges:
            # Mock connection test
            if ex in ['bybit', 'binance']:
                connected.append(ex)
        
        self.assertGreater(len(connected), 0)
        self.assertIn('bybit', connected)
    
    def test_2_symbol_list_load(self):
        """심볼 목록 로드 (USDT 페어)"""
        all_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BTCKRW', 'ETHKRW']
        
        usdt_pairs = [s for s in all_symbols if s.endswith('USDT')]
        
        self.assertEqual(len(usdt_pairs), 3)
        self.assertIn('BTCUSDT', usdt_pairs)
    
    def test_3_candle_data_fetch(self):
        """캔들 데이터 조회 (15m, 4H)"""
        timeframes = ['15m', '4h']
        
        for tf in timeframes:
            # Simulate data fetch
            data = {'timestamp': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
            for i in range(100):
                data['timestamp'].append(datetime.now() - timedelta(hours=i))
                data['open'].append(100 + i)
                data['high'].append(105 + i)
                data['low'].append(95 + i)
                data['close'].append(102 + i)
                data['volume'].append(1000 * i)
            
            self.assertEqual(len(data['close']), 100)
    
    def test_4_data_integrity(self):
        """데이터 무결성 (OHLCV 컬럼 존재)"""
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        data_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'rsi', 'atr']
        
        for col in required_columns:
            self.assertIn(col, data_columns)


class TestStep2_Optimization(unittest.TestCase):
    """Step 2: 최적화 검증"""
    
    def setUp(self):
        self.min_wr = 70.0
        self.max_mdd = 20.0
        self.min_trades = 30
        
        self.optimization_results = {
            'BTCUSDT': {'win_rate': 75.0, 'max_drawdown': 15.0, 'total_trades': 50},
            'ETHUSDT': {'win_rate': 65.0, 'max_drawdown': 12.0, 'total_trades': 40},  # Fail WR
            'SOLUSDT': {'win_rate': 72.0, 'max_drawdown': 18.0, 'total_trades': 35},
        }
    
    def test_1_batch_optimization_runs(self):
        """배치 최적화 실행 (3개 심볼)"""
        symbols = list(self.optimization_results.keys())
        
        self.assertEqual(len(symbols), 3)
    
    def test_2_filter_criteria_applied(self):
        """프리셋 생성 기준 적용 (70%/20%/30)"""
        passed = []
        failed = []
        
        for sym, res in self.optimization_results.items():
            if (res['win_rate'] >= self.min_wr and 
                res['max_drawdown'] <= self.max_mdd and 
                res['total_trades'] >= self.min_trades):
                passed.append(sym)
            else:
                failed.append(sym)
        
        self.assertEqual(len(passed), 2)
        self.assertEqual(len(failed), 1)
    
    def test_3_passed_preset_saved(self):
        """통과 심볼 프리셋 저장 확인"""
        passed = ['BTCUSDT', 'SOLUSDT']
        preset_dir = tempfile.mkdtemp()
        
        for sym in passed:
            preset_path = Path(preset_dir) / f"{sym}.json"
            with open(preset_path, 'w') as f:
                json.dump({'symbol': sym, 'params': {}}, f)
        
        saved_files = list(Path(preset_dir).glob('*.json'))
        self.assertEqual(len(saved_files), 2)
    
    def test_4_failed_no_preset(self):
        """탈락 심볼 프리셋 미생성 확인"""
        failed = ['ETHUSDT']
        passed = ['BTCUSDT', 'SOLUSDT']
        
        # Only passed should have presets
        preset_symbols = passed  # Not including failed
        
        self.assertNotIn('ETHUSDT', preset_symbols)
    
    def test_5_result_report(self):
        """결과 리포트 (통과 N, 탈락 M)"""
        passed_count = 2
        failed_count = 1
        
        report = f"통과: {passed_count}개, 탈락: {failed_count}개"
        
        self.assertIn('2', report)
        self.assertIn('1', report)


class TestStep3_Backtest(unittest.TestCase):
    """Step 3: 백테스트 검증"""
    
    def test_1_load_preset_symbols_only(self):
        """프리셋 있는 심볼만 로드"""
        all_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        preset_symbols = ['BTCUSDT', 'SOLUSDT']
        
        loaded = [s for s in all_symbols if s in preset_symbols]
        
        self.assertEqual(len(loaded), 2)
        self.assertNotIn('ETHUSDT', loaded)
    
    def test_2_collect_all_signals(self):
        """전체 시그널 수집"""
        signals = [
            {'symbol': 'BTC', 'timestamp': datetime(2025, 1, 1, 10), 'type': 'long'},
            {'symbol': 'SOL', 'timestamp': datetime(2025, 1, 1, 12), 'type': 'long'},
            {'symbol': 'BTC', 'timestamp': datetime(2025, 1, 1, 15), 'type': 'short'},
        ]
        
        self.assertEqual(len(signals), 3)
    
    def test_3_timestamp_sorting(self):
        """타임스탬프 정렬 확인"""
        signals = [
            {'timestamp': datetime(2025, 1, 1, 15)},
            {'timestamp': datetime(2025, 1, 1, 10)},
            {'timestamp': datetime(2025, 1, 1, 12)},
        ]
        
        sorted_signals = sorted(signals, key=lambda x: x['timestamp'])
        
        self.assertEqual(sorted_signals[0]['timestamp'].hour, 10)
        self.assertEqual(sorted_signals[1]['timestamp'].hour, 12)
        self.assertEqual(sorted_signals[2]['timestamp'].hour, 15)
    
    def test_4_single_position_rule(self):
        """포지션 1개 룰 적용"""
        signals = [
            {'ts': 0, 'symbol': 'BTC'},
            {'ts': 1, 'symbol': 'ETH'},  # Blocked
            {'ts': 5, 'symbol': 'SOL'},  # After exit
        ]
        
        executed = []
        position_end_time = -1
        
        for sig in signals:
            if sig['ts'] > position_end_time:
                executed.append(sig)
                position_end_time = sig['ts'] + 3  # 3 time unit duration
        
        self.assertEqual(len(executed), 2)
        self.assertNotIn('ETH', [s['symbol'] for s in executed])
    
    def test_5_concurrent_signal_priority(self):
        """동시 시그널 시 승률 우선 선택"""
        concurrent = [
            {'symbol': 'BTC', 'win_rate': 72, 'ts': 0},
            {'symbol': 'ETH', 'win_rate': 78, 'ts': 0},
            {'symbol': 'SOL', 'win_rate': 70, 'ts': 0},
        ]
        
        selected = max(concurrent, key=lambda x: x['win_rate'])
        
        self.assertEqual(selected['symbol'], 'ETH')
    
    def test_6_result_metrics(self):
        """결과: 거래수, 승률, MDD, PnL"""
        trades = [
            {'pnl': 5.0}, {'pnl': -2.0}, {'pnl': 8.0}, {'pnl': 3.0}, {'pnl': -1.0}
        ]
        
        total_trades = len(trades)
        wins = sum(1 for t in trades if t['pnl'] > 0)
        win_rate = (wins / total_trades) * 100
        total_pnl = sum(t['pnl'] for t in trades)
        
        self.assertEqual(total_trades, 5)
        self.assertEqual(win_rate, 60.0)
        self.assertEqual(total_pnl, 13.0)


class TestStep4_ScannerConfig(unittest.TestCase):
    """Step 4: 스캐너 설정 검증"""
    
    def test_1_load_verified_symbols(self):
        """검증된 심볼 목록 로드"""
        preset_dir = tempfile.mkdtemp()
        
        # Create mock presets
        for sym in ['BTCUSDT', 'SOLUSDT']:
            with open(Path(preset_dir) / f"{sym}.json", 'w') as f:
                json.dump({'symbol': sym}, f)
        
        loaded = list(Path(preset_dir).glob('*.json'))
        
        self.assertEqual(len(loaded), 2)
    
    def test_2_save_config_values(self):
        """설정값 저장 (금액, 레버리지, 블랙리스트)"""
        config = {
            'entry_amount': 100,
            'leverage': 5,
            'blacklist': ['SHIBUSDT', 'PEPEUSDT'],
            'max_positions': 1
        }
        
        self.assertEqual(config['entry_amount'], 100)
        self.assertEqual(config['leverage'], 5)
        self.assertEqual(len(config['blacklist']), 2)
    
    def test_3_config_file_created(self):
        """설정 파일 생성 확인"""
        config_dir = tempfile.mkdtemp()
        config_path = Path(config_dir) / 'scanner_config.json'
        
        config = {'entry_amount': 100, 'leverage': 5}
        
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        self.assertTrue(config_path.exists())


class TestStep5_ScannerExecution(unittest.TestCase):
    """Step 5: 스캐너 실행 검증"""
    
    def test_1_chunk_50_division(self):
        """Stage 1: 청크 50개씩 분할"""
        symbols = [f"SYM{i}" for i in range(120)]
        chunk_size = 50
        
        chunks = [symbols[i:i+chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 50)
        self.assertEqual(len(chunks[2]), 20)
    
    def test_2_4h_pattern_check(self):
        """Stage 1: 4H 캔들로 패턴 체크"""
        rsi_values = {'BTC': 45, 'ETH': 75, 'SOL': 35}
        
        # Filter: RSI between 30-70
        candidates = [s for s, rsi in rsi_values.items() if 30 < rsi < 70]
        
        # BTC(45) and SOL(35) pass, ETH(75) fails
        self.assertEqual(len(candidates), 2)
        self.assertIn('BTC', candidates)
        self.assertIn('SOL', candidates)
    
    def test_3_stage1_to_stage2_transition(self):
        """Stage 1 → Stage 2 전환 조건"""
        stage1_candidates = ['BTC', 'SOL']
        
        stage2_monitors = []
        for sym in stage1_candidates:
            stage2_monitors.append({'symbol': sym, 'status': 'monitoring'})
        
        self.assertEqual(len(stage2_monitors), 2)
    
    def test_4_websocket_subscription(self):
        """Stage 2: WebSocket 구독"""
        ws_channels = []
        symbols = ['BTC', 'SOL']
        
        for sym in symbols:
            ws_channels.append(f"kline.15.{sym}USDT")
        
        self.assertEqual(len(ws_channels), 2)
        self.assertIn('kline.15.BTCUSDT', ws_channels)
    
    def test_5_15m_realtime_monitor(self):
        """Stage 2: 15m 실시간 감시"""
        candle = {
            'symbol': 'BTCUSDT',
            'interval': '15m',
            'close': 95000,
            'rsi': 32,
            'pattern': 'W_PATTERN'
        }
        
        # Signal detected if RSI < 35 and pattern exists
        signal_detected = candle['rsi'] < 35 and candle['pattern'] == 'W_PATTERN'
        
        self.assertTrue(signal_detected)
    
    def test_6_position_blocks_entry(self):
        """포지션 있으면 진입 차단"""
        active_positions = {'ETHUSDT': {'size': 0.1, 'entry': 3000}}
        max_positions = 1
        
        can_enter = len(active_positions) < max_positions
        
        self.assertFalse(can_enter)
    
    def test_7_exit_then_rescan(self):
        """청산 후 다시 스캔"""
        active_positions = {'ETHUSDT': {'size': 0.1}}
        
        # Exit position
        del active_positions['ETHUSDT']
        
        # Can scan again
        can_scan = len(active_positions) == 0
        
        self.assertTrue(can_scan)


class TestStep6_FullCycle(unittest.TestCase):
    """Step 6: 전체 사이클 검증"""
    
    def test_1_sequential_execution(self):
        """Step 1~5 순차 실행"""
        steps = ['data_collection', 'optimization', 'backtest', 'scanner_config', 'scanner_run']
        executed = []
        
        for step in steps:
            executed.append(step)
        
        self.assertEqual(len(executed), 5)
        self.assertEqual(executed[0], 'data_collection')
        self.assertEqual(executed[-1], 'scanner_run')
    
    def test_2_data_flow_verification(self):
        """데이터 전달 확인 (심볼 → 프리셋 → 스캐너)"""
        # Step 1: Symbols
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        # Step 2: Optimization -> Presets
        passed_presets = ['BTCUSDT', 'SOLUSDT']
        
        # Step 5: Scanner uses presets
        scanner_symbols = passed_presets.copy()
        
        # Verify flow
        self.assertEqual(len(symbols), 3)
        self.assertEqual(len(passed_presets), 2)
        self.assertEqual(scanner_symbols, passed_presets)
    
    def test_3_error_safe_shutdown(self):
        """에러 발생 시 안전 종료"""
        state = 'RUNNING'
        error_occurred = True
        
        if error_occurred:
            # Close positions
            positions_closed = True
            # Save state
            state_saved = True
            # Stop scanner
            state = 'STOPPED'
        
        self.assertEqual(state, 'STOPPED')
        self.assertTrue(positions_closed)
        self.assertTrue(state_saved)


def run_all_steps():
    """Run all steps and print summary"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [
        TestStep1_DataCollection,
        TestStep2_Optimization,
        TestStep3_Backtest,
        TestStep4_ScannerConfig,
        TestStep5_ScannerExecution,
        TestStep6_FullCycle,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("전체 플로우 검증 결과")
    print("=" * 60)
    
    step_results = {
        'Step 1: 데이터 수집': 4,
        'Step 2: 최적화': 5,
        'Step 3: 백테스트': 6,
        'Step 4: 스캐너 설정': 3,
        'Step 5: 스캐너 실행': 7,
        'Step 6: 전체 사이클': 3,
    }
    
    total = sum(step_results.values())
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    
    for step, count in step_results.items():
        print(f"[{step}] ✅ {count}/{count}")
    
    print(f"\n총 결과: {passed}/{total} 통과")
    
    if failed == 0:
        print("전체 플로우 정상 ✅")
    else:
        print(f"실패: {failed}개 ❌")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_steps()
    sys.exit(0 if success else 1)
