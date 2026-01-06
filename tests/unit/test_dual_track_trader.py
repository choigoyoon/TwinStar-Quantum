# -*- coding: utf-8 -*-
"""
DualTrackTrader 검증 테스트
- 2-Track 복리 로직 (BTC 고정 + ALT 복리)
- BTC/ALT 동시 포지션 관리
- check_entry_allowed() 조건
- 프리셋 파일 연동 플로우
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestDualTrackTraderCompound(unittest.TestCase):
    """2-Track 복리 로직 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # Mock exchange client
        self.mock_exchange = Mock()
        self.mock_exchange.name = 'bybit'
        
        # Import with mocks
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None):
            from core.dual_track_trader import DualTrackTrader
            self.trader = DualTrackTrader(
                exchange_client=self.mock_exchange,
                btc_fixed_usd=100.0,
                initial_alt_capital=1000.0
            )
    
    def test_01_initial_capital_setup(self):
        """초기 자본 설정 확인"""
        self.assertEqual(self.trader.btc_fixed_usd, 100.0, "BTC 고정 금액이 $100이어야 함")
        self.assertEqual(self.trader.alt_capital, 1000.0, "ALT 초기 자본이 $1000이어야 함")
        print("✓ 초기 자본 설정 확인됨 (BTC: $100, ALT: $1000)")
    
    def test_02_btc_symbol_detection(self):
        """BTC 심볼 감지 로직"""
        btc_symbols = ['BTCUSDT', 'BTCUSD', 'BTC-USDT', 'btcusdt']
        alt_symbols = ['ETHUSDT', 'SOLUSDT', 'XRPUSDT']
        
        for sym in btc_symbols:
            self.assertTrue(self.trader.is_btc(sym), f"{sym}이 BTC로 감지되어야 함")
        
        for sym in alt_symbols:
            self.assertFalse(self.trader.is_btc(sym), f"{sym}이 ALT로 감지되어야 함")
        
        print("✓ BTC/ALT 심볼 분류 정상")
    
    def test_03_entry_allowed_position_limit(self):
        """진입 가능 여부 - 포지션 제한"""
        with patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            
            # 초기 상태: 진입 가능
            self.assertTrue(self.trader.check_entry_allowed('BTCUSDT'))
            self.assertTrue(self.trader.check_entry_allowed('ETHUSDT'))
            
            # BTC 진입 후
            self.trader.on_entry_executed('BTCUSDT', 0.01, 50000.0)
            
            # BTC 트랙은 잠김, ALT 트랙은 가능
            self.assertFalse(self.trader.check_entry_allowed('BTCUSDT'))
            self.assertTrue(self.trader.check_entry_allowed('ETHUSDT'))
            
            # ALT 진입 후
            self.trader.on_entry_executed('ETHUSDT', 0.5, 3000.0)
            
            # 둘 다 잠김
            self.assertFalse(self.trader.check_entry_allowed('BTCUSDT'))
            self.assertFalse(self.trader.check_entry_allowed('ETHUSDT'))
        
        print("✓ 트랙별 동시 포지션 제한 정상 (BTC 1개 + ALT 1개)")
    
    def test_04_btc_track_no_compound(self):
        """BTC 트랙 - 고정 금액 (복리 미적용)"""
        with patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            mock_health.return_value.record_trade = Mock()
            
            initial_alt = self.trader.alt_capital
            
            # BTC 진입 및 청산 (수익)
            self.trader.on_entry_executed('BTCUSDT', 0.01, 50000.0)
            self.trader.on_exit_executed('BTCUSDT', pnl_usd=50.0, pnl_pct=5.0)
            
            # ALT 자본 변화 없음
            self.assertEqual(self.trader.alt_capital, initial_alt, "BTC 수익이 ALT 자본에 영향 주지 않아야 함")
            # BTC 트랙 해제됨
            self.assertIsNone(self.trader.active_positions['btc'])
        
        print("✓ BTC 트랙: 고정 금액 유지 (복리 미적용)")
    
    def test_05_alt_track_compound_profit(self):
        """ALT 트랙 - 수익 복리 적용"""
        with patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            mock_health.return_value.record_trade = Mock()
            
            initial_alt = self.trader.alt_capital  # $1000
            
            # ALT 진입 및 청산 (10% 수익)
            self.trader.on_entry_executed('ETHUSDT', 0.5, 3000.0)
            self.trader.on_exit_executed('ETHUSDT', pnl_usd=100.0, pnl_pct=10.0)
            
            # ALT 자본 증가 ($1000 + $100 = $1100)
            self.assertEqual(self.trader.alt_capital, 1100.0, "ALT 수익이 자본에 복리 적용되어야 함")
        
        print("✓ ALT 트랙: 수익 $100 → 자본 $1000 → $1100 (복리 적용)")
    
    def test_06_alt_track_compound_loss(self):
        """ALT 트랙 - 손실 복리 적용"""
        with patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            mock_health.return_value.record_trade = Mock()
            
            # ALT 진입 및 청산 (5% 손실)
            self.trader.on_entry_executed('SOLUSDT', 5.0, 200.0)
            self.trader.on_exit_executed('SOLUSDT', pnl_usd=-50.0, pnl_pct=-5.0)
            
            # 현재 ALT 자본: $1100 - $50 = $1050
            self.assertEqual(self.trader.alt_capital, 1050.0, "ALT 손실이 자본에서 차감되어야 함")
        
        print("✓ ALT 트랙: 손실 $50 → 자본 $1100 → $1050 (복리 적용)")
    
    def test_07_summary_output(self):
        """현황 요약 출력"""
        with patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            
            self.trader.on_entry_executed('BTCUSDT', 0.01, 50000.0)
            
            summary = self.trader.get_summary()
            
            self.assertEqual(summary['btc_fixed'], 100.0)
            self.assertEqual(summary['active_btc'], 'BTCUSDT')
            self.assertIn('alt_capital', summary)
            self.assertIn('total_bots', summary)
        
        print("✓ 현황 요약 출력 정상")


class TestPresetIntegrationFlow(unittest.TestCase):
    """BatchOptimizer → Preset 생성 → MultiTrader 로드 플로우 테스트"""
    
    def setUp(self):
        """테스트용 임시 프리셋 경로 설정"""
        self.test_preset_name = '__test_integration_preset__'
    
    def tearDown(self):
        """테스트용 프리셋 삭제"""
        try:
            from utils.preset_manager import PresetManager
            pm = PresetManager()
            pm.delete_preset(self.test_preset_name)
        except:
            pass
    
    def test_01_batch_optimizer_creates_preset(self):
        """BatchOptimizer가 프리셋 저장 가능한지 확인"""
        from utils.preset_manager import PresetManager
        
        pm = PresetManager()
        
        # BatchOptimizer 결과 시뮬레이션
        optimized_params = {
            '_meta': {
                'name': self.test_preset_name,
                'type': 'preset',
                'version': '2.0',
                'source': 'batch_optimizer'
            },
            'trading': {
                'pullback_rsi_long': 45,
                'pullback_rsi_short': 55,
                'pattern_tolerance': 0.05
            },
            'risk': {
                'trail_start_r': 0.8,
                'trail_dist_r': 0.5,
                'min_rr': 1.0
            },
            'results': {
                'win_rate': 75.0,
                'mdd': -8.5,
                'net_pnl': 1500.0
            }
        }
        
        # 저장
        result = pm.save_preset(self.test_preset_name, optimized_params)
        self.assertTrue(result, "프리셋 저장 성공해야 함")
        
        print("✓ BatchOptimizer 결과 프리셋 저장 성공")
    
    def test_02_preset_load_v2_format(self):
        """저장된 프리셋 V2 형식으로 로드"""
        from utils.preset_manager import PresetManager
        
        pm = PresetManager()
        
        # 먼저 저장
        pm.save_preset(self.test_preset_name, {
            '_meta': {'name': self.test_preset_name, 'version': '2.0'},
            'trading': {'pullback_rsi_long': 45}
        })
        
        # 로드
        loaded = pm.load_preset(self.test_preset_name)
        
        self.assertIn('_meta', loaded, "V2 형식에 _meta 필드 필요")
        self.assertIn('trading', loaded, "V2 형식에 trading 필드 필요")
        
        print("✓ 프리셋 V2 형식 로드 성공")
    
    def test_03_preset_load_flat_for_bot(self):
        """봇 호환용 flat 형식으로 변환 로드"""
        from utils.preset_manager import PresetManager
        
        pm = PresetManager()
        
        # 저장
        pm.save_preset(self.test_preset_name, {
            '_meta': {'name': self.test_preset_name, 'version': '2.0'},
            'trading': {'pullback_rsi_long': 45, 'pullback_rsi_short': 55},
            'risk': {'trail_start_r': 0.8}
        })
        
        # flat 로드
        flat = pm.load_preset_flat(self.test_preset_name)
        
        # flat 형식 확인 (중첩 없이 직접 키)
        self.assertIn('pullback_rsi_long', flat, "flat 형식에 직접 키 필요")
        self.assertEqual(flat['pullback_rsi_long'], 45)
        
        print("✓ 프리셋 flat 형식 로드 성공 (봇/백테스트 호환)")
    
    def test_04_real_preset_files_exist(self):
        """실제 프리셋 파일 존재 확인"""
        preset_dir = PROJECT_ROOT / 'config' / 'presets'
        
        self.assertTrue(preset_dir.exists(), "config/presets 디렉토리 존재해야 함")
        
        json_files = list(preset_dir.glob('*.json'))
        self.assertGreater(len(json_files), 0, "최소 1개 이상의 프리셋 파일 필요")
        
        print(f"✓ 실제 프리셋 파일 확인: {len(json_files)}개 존재")
        for f in json_files[:5]:
            print(f"  - {f.name}")
    
    def test_05_load_actual_preset(self):
        """실제 프리셋 파일 로드 테스트"""
        from utils.preset_manager import PresetManager
        
        pm = PresetManager()
        preset_list = pm.list_presets()
        
        self.assertGreater(len(preset_list), 0, "프리셋 목록이 비어있지 않아야 함")
        
        # 첫 번째 프리셋 로드
        first_preset = preset_list[0]['name']
        loaded = pm.load_preset(first_preset)
        
        self.assertIsInstance(loaded, dict, "프리셋은 dict 형태여야 함")
        
        print(f"✓ 실제 프리셋 '{first_preset}' 로드 성공")


class TestHealthCheckIntegration(unittest.TestCase):
    """HealthMonitor 연동 테스트"""
    
    def test_01_health_check_blocks_entry(self):
        """헬스 체크 실패 시 진입 차단"""
        mock_exchange = Mock()
        mock_exchange.name = 'bybit'
        
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None), \
             patch('core.dual_track_trader.get_health_monitor') as mock_health:
            
            # 헬스 체크 실패 설정
            mock_health.return_value.can_trade.return_value = (False, 'Drawdown limit exceeded')
            
            from core.dual_track_trader import DualTrackTrader
            trader = DualTrackTrader(exchange_client=mock_exchange)
            
            # 진입 불가
            allowed = trader.check_entry_allowed('ETHUSDT')
            self.assertFalse(allowed, "헬스 체크 실패 시 진입 차단되어야 함")
        
        print("✓ 헬스 체크 실패 시 진입 차단 정상")
    
    def test_02_trade_recorded_on_exit(self):
        """청산 시 트레이드 기록"""
        mock_exchange = Mock()
        mock_exchange.name = 'bybit'
        
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None), \
             patch('core.dual_track_trader.get_health_monitor') as mock_health:
            
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            mock_health.return_value.record_trade = Mock()
            
            from core.dual_track_trader import DualTrackTrader
            trader = DualTrackTrader(exchange_client=mock_exchange)
            
            # 진입 및 청산
            trader.on_entry_executed('ETHUSDT', 0.5, 3000.0)
            trader.on_exit_executed('ETHUSDT', pnl_usd=100.0, pnl_pct=10.0)
            
            # record_trade 호출 확인
            mock_health.return_value.record_trade.assert_called_once()
        
        print("✓ 청산 시 HealthMonitor에 트레이드 기록됨")


def run_tests():
    """테스트 실행"""
    print("=" * 60)
    print(" DualTrackTrader & Preset Integration 검증")
    print("=" * 60)
    print()
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 테스트 클래스 추가
    suite.addTests(loader.loadTestsFromTestCase(TestDualTrackTraderCompound))
    suite.addTests(loader.loadTestsFromTestCase(TestPresetIntegrationFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestHealthCheckIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 60)
    if result.wasSuccessful():
        print("✅ 전체 테스트 통과!")
    else:
        print(f"❌ 실패: {len(result.failures)} / 에러: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
