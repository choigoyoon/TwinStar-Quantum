"""
프리셋 재검증 스크립트 (v7.24.1)
================================

v7.20-v7.23 프리셋을 v7.24 기준으로 재생성합니다.

기능:
1. presets/ 디렉토리 전체 스캔
2. validation.ssot_version != "v7.24" 프리셋 감지
3. 자동 재생성 (v7.24 메트릭 기준)
4. 결과 리포트 생성

사용법:
    python tools/revalidate_all_presets.py

옵션:
    --dry-run: 실제 재생성 없이 리포트만 생성
    --verbose: 상세 로그 출력
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import argparse

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from core.optimizer import BacktestOptimizer
    from core.strategy_core import AlphaX7Core
    from core.data_manager import BotDataManager
    from utils.preset_storage import PresetStorage
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    print("프로젝트 루트에서 실행하세요: python tools/revalidate_all_presets.py")
    sys.exit(1)

# 로깅 설정 (간단하게)
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class PresetRevalidator:
    """프리셋 재검증 클래스"""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        """
        Args:
            dry_run: 실제 재생성 없이 리포트만 생성
            verbose: 상세 로그 출력
        """
        self.dry_run = dry_run
        self.verbose = verbose
        self.preset_dir = project_root / 'presets'
        self.report: Dict = {
            'total_scanned': 0,
            'needs_revalidation': 0,
            'revalidated': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }

    def scan_presets(self) -> List[Path]:
        """프리셋 파일 전체 스캔"""
        logger.info("🔍 프리셋 스캔 시작...")

        preset_files = list(self.preset_dir.rglob('*.json'))
        self.report['total_scanned'] = len(preset_files)

        logger.info(f"✅ 스캔 완료: {len(preset_files)}개 프리셋 발견")
        return preset_files

    def check_preset_version(self, preset_path: Path) -> tuple[bool, str, dict]:
        """프리셋 버전 체크

        Returns:
            (재검증 필요 여부, 사유, 프리셋 데이터)
        """
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                preset = json.load(f)

            validation = preset.get('validation', {})
            ssot_version = validation.get('ssot_version', '')

            # v7.24 이후: 재검증 불필요
            if ssot_version == 'v7.24':
                return (False, "v7.24 프리셋 (최신)", preset)

            # v7.20-v7.23: 재검증 필요
            if ssot_version.startswith('v7.2'):
                return (True, f"{ssot_version} 프리셋 (MDD 66% 차이)", preset)

            # validation 필드 없음: 재검증 필수
            if not validation:
                return (True, "레거시 프리셋 (버전 불명)", preset)

            # 기타
            return (True, f"알 수 없는 버전 ({ssot_version})", preset)

        except Exception as e:
            logger.error(f"❌ 파일 읽기 실패 ({preset_path.name}): {e}")
            return (False, f"읽기 실패: {e}", {})

    def revalidate_preset(self, preset_path: Path, preset: dict) -> bool:
        """프리셋 재검증 (백테스트 재실행 + 저장)

        Args:
            preset_path: 프리셋 파일 경로
            preset: 프리셋 데이터

        Returns:
            재검증 성공 여부
        """
        try:
            meta_info = preset.get('meta_info', {})
            best_params = preset.get('best_params', {})

            exchange = meta_info.get('exchange', 'bybit')
            symbol = meta_info.get('symbol', 'BTCUSDT')
            timeframe = meta_info.get('timeframe', '1h')
            strategy_type = meta_info.get('strategy_type', 'macd')

            logger.info(f"🔄 재검증 시작: {exchange} {symbol} {timeframe} ({strategy_type})")

            # Dry run 모드: 실제 재생성 없이 리포트만
            if self.dry_run:
                logger.info(f"   [DRY RUN] 실제 재생성 생략")
                return True

            # 1. 데이터 로드
            dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})
            dm.load_historical()

            if dm.df_entry_full is None or dm.df_entry_full.empty:
                logger.error(f"❌ 데이터 로드 실패")
                return False

            df = dm.df_entry_full

            # 2. 백테스트 실행 (단일 파라미터)
            # AlphaX7Core는 __init__(self, use_mtf=True) 형태
            strategy = AlphaX7Core(use_mtf=True)
            result = strategy.run_backtest(df, best_params)

            if not result:
                logger.error(f"❌ 백테스트 실패")
                return False

            # 3. 프리셋 저장 (v7.24 기준)
            storage = PresetStorage()
            success = storage.save_preset(
                symbol=symbol,
                tf=timeframe,
                params=best_params,
                optimization_result={
                    'win_rate': result.get('win_rate', 0),
                    'total_trades': result.get('total_trades', 0),
                    'mdd': result.get('max_drawdown', 0),
                    'total_pnl': result.get('total_return', 0),
                    'compound_return': result.get('compound_return', 0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0),
                    'profit_factor': result.get('profit_factor', 0),
                    'avg_trades_per_day': result.get('avg_trades_per_day', 0),
                    'avg_pnl': result.get('avg_pnl', 0),
                    'stability': result.get('stability', 'F'),
                    'cagr': result.get('cagr', 0)
                },
                mode='revalidated',
                strategy_type=strategy_type,
                exchange=exchange
            )

            if success:
                logger.info(f"✅ 재검증 완료: {symbol}_{timeframe}")
                logger.info(f"   승률: {result.get('win_rate', 0):.2f}%")
                logger.info(f"   MDD: {result.get('max_drawdown', 0):.2f}%")
            else:
                logger.error(f"❌ 저장 실패")

            return success

        except Exception as e:
            logger.error(f"❌ 재검증 실패: {e}")
            return False

    def run(self) -> dict:
        """전체 재검증 프로세스 실행"""
        logger.info("=" * 80)
        logger.info("프리셋 재검증 시작 (v7.24.1)")
        logger.info("=" * 80)

        if self.dry_run:
            logger.info("⚠️  DRY RUN 모드: 실제 재생성 없이 리포트만 생성")
        logger.info("")

        # 1. 프리셋 스캔
        preset_files = self.scan_presets()

        if not preset_files:
            logger.info("ℹ️  프리셋 파일 없음")
            return self.report

        # 2. 버전 체크 + 재검증
        for preset_path in preset_files:
            needs_revalidation, reason, preset = self.check_preset_version(preset_path)

            if not needs_revalidation:
                if self.verbose:
                    logger.info(f"⏭️  건너뛰기: {preset_path.name} ({reason})")
                self.report['skipped'] += 1
                continue

            logger.info(f"⚠️  재검증 필요: {preset_path.name}")
            logger.info(f"   사유: {reason}")
            self.report['needs_revalidation'] += 1

            # 재검증 실행
            success = self.revalidate_preset(preset_path, preset)

            if success:
                self.report['revalidated'] += 1
                self.report['details'].append({
                    'file': preset_path.name,
                    'status': 'success',
                    'reason': reason
                })
            else:
                self.report['failed'] += 1
                self.report['details'].append({
                    'file': preset_path.name,
                    'status': 'failed',
                    'reason': reason
                })

        # 3. 리포트 출력
        self.print_report()

        # 4. 리포트 저장
        self.save_report()

        return self.report

    def print_report(self):
        """리포트 콘솔 출력"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("재검증 리포트")
        logger.info("=" * 80)
        logger.info(f"총 스캔: {self.report['total_scanned']}개")
        logger.info(f"재검증 필요: {self.report['needs_revalidation']}개")
        logger.info(f"재검증 완료: {self.report['revalidated']}개")
        logger.info(f"실패: {self.report['failed']}개")
        logger.info(f"건너뛰기: {self.report['skipped']}개")
        logger.info("=" * 80)

        if self.report['failed'] > 0:
            logger.info("")
            logger.info("❌ 실패 목록:")
            for detail in self.report['details']:
                if detail['status'] == 'failed':
                    logger.info(f"   - {detail['file']}: {detail['reason']}")

        if self.report['revalidated'] > 0:
            logger.info("")
            logger.info("✅ 재검증 완료 목록:")
            for detail in self.report['details']:
                if detail['status'] == 'success':
                    logger.info(f"   - {detail['file']}")

    def save_report(self):
        """리포트 JSON 저장"""
        report_dir = project_root / 'docs' / 'revalidation_reports'
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = report_dir / f'revalidation_report_{timestamp}.json'

        self.report['timestamp'] = timestamp
        self.report['dry_run'] = self.dry_run

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)

        logger.info("")
        logger.info(f"📄 리포트 저장: {report_path}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="프리셋 재검증 (v7.24.1)")
    parser.add_argument('--dry-run', action='store_true', help="실제 재생성 없이 리포트만 생성")
    parser.add_argument('--verbose', action='store_true', help="상세 로그 출력")
    args = parser.parse_args()

    revalidator = PresetRevalidator(dry_run=args.dry_run, verbose=args.verbose)

    try:
        report = revalidator.run()

        # 종료 코드
        if report['failed'] > 0:
            sys.exit(1)  # 실패 있음
        else:
            sys.exit(0)  # 성공

    except KeyboardInterrupt:
        logger.info("\n⚠️  사용자 중단")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
