"""
전체 검증 실행기
사용법: py tests/run_all.py [옵션]

옵션:
  --quick    빠른 검증 (GUI 제외)
  --full     전체 검증 (GUI 포함)
  --gui      GUI만 검증
  --realtime 실시간 검증
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

class VerifyRunner:
    def __init__(self):
        self.results = {}
        self.start_time = None
    
    def run_module(self, name, module_name):
        """개별 검증 모듈 실행"""
        print(f"\n{'='*50}")
        print(f"▶ {name}")
        print('='*50)
        
        try:
            module = __import__(module_name, fromlist=['run'])
            result = module.run()
            self.results[name] = result
            return result['failed'] == 0
        except Exception as e:
            print(f"❌ 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            self.results[name] = {'passed': 0, 'failed': 1, 'error': str(e)}
            return False
    
    def save_results(self):
        """결과 저장"""
        output = {
            'timestamp': datetime.now().isoformat(),
            'results': self.results,
            'summary': {
                'total_passed': sum(r.get('passed', 0) for r in self.results.values()),
                'total_failed': sum(r.get('failed', 0) for r in self.results.values()),
            }
        }
        
        output_file = Path(__file__).parent / "verify_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def print_summary(self):
        """결과 요약 출력"""
        print("\n" + "="*60)
        print("📊 전체 검증 결과")
        print("="*60)
        
        total_p = 0
        total_f = 0
        
        for name, result in self.results.items():
            p = result.get('passed', 0)
            f = result.get('failed', 0)
            total_p += p
            total_f += f
            
            status = "✅" if f == 0 else "❌"
            print(f"  {status} {name}: {p}/{p+f}")
        
        print("-"*60)
        print(f"  총계: {total_p}/{total_p+total_f} ({total_p/(total_p+total_f)*100:.1f}%)")
        
        return total_f == 0

def main():
    parser = argparse.ArgumentParser(description='TwinStar Quantum 검증')
    parser.add_argument('--quick', action='store_true', help='빠른 검증')
    parser.add_argument('--full', action='store_true', help='전체 검증')
    parser.add_argument('--gui', action='store_true', help='GUI만')
    parser.add_argument('--realtime', action='store_true', help='실시간')
    args = parser.parse_args()
    
    runner = VerifyRunner()
    
    print("="*60)
    print("🔍 TwinStar Quantum - 통합 검증 시스템 v3.0")
    print("="*60)
    
    # 기본: quick
    if args.gui:
        tests = [("GUI 검증", "tests.verify_gui")]
    elif args.realtime:
        tests = [("실시간 검증", "tests.verify_realtime")]
    elif args.full:
        tests = [
            ("모듈 검증", "tests.verify_modules"),
            ("메서드 검증", "tests.verify_methods"),
            ("임포트 검증", "tests.verify_imports"),
            ("경로 검증", "tests.verify_paths"),
            ("GUI 검증", "tests.verify_gui"),
            ("실시간 검증", "tests.verify_realtime"),
        ]
    else:  # quick (default)
        tests = [
            ("모듈 검증", "tests.verify_modules"),
            ("메서드 검증", "tests.verify_methods"),
            ("임포트 검증", "tests.verify_imports"),
            ("경로 검증", "tests.verify_paths"),
        ]
    
    for name, module in tests:
        runner.run_module(name, module)
    
    output_file = runner.save_results()
    success = runner.print_summary()
    
    print(f"\n📁 상세 결과: {output_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
