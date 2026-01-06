import os
import re
from collections import defaultdict

BASE = r'C:\매매전략'

def analyze_file(filepath):
    """Analyze a single file for cleanup opportunities"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.split('\n')
    
    result = {
        'lines': len(lines),
        'functions': len(re.findall(r'def \w+\(', content)),
        'classes': len(re.findall(r'class \w+', content)),
        'comments': len([l for l in lines if l.strip().startswith('#')]),
        'blank': len([l for l in lines if not l.strip()]),
        'imports': len([l for l in lines if l.strip().startswith('import ') or l.strip().startswith('from ')]),
        'todos': len(re.findall(r'TODO|FIXME|XXX|HACK', content, re.IGNORECASE)),
        'magic_numbers': len(re.findall(r'[=<>] \d{2,}[^.]', content)),  # Numbers > 9
    }
    return result

def main():
    print('=' * 70)
    print('=== Phase 10.2 코드 정리 분석 보고서 ===')
    print('=' * 70)
    print()
    
    # Key files to analyze
    files = {
        'GUI': [
            'GUI/trading_dashboard.py',
            'GUI/optimization_widget.py',
            'GUI/backtest_widget.py',
            'GUI/staru_main.py',
            'GUI/data_widget.py',
            'GUI/settings_widget.py',
        ],
        'Core': [
            'core/unified_bot.py',
            'core/strategy_core.py',
            'core/bot_state.py',
            'core/data_manager.py',
            'core/signal_processor.py',
            'core/order_executor.py',
            'core/position_manager.py',
        ]
    }
    
    total_stats = defaultdict(int)
    large_files = []
    
    for category, file_list in files.items():
        print(f'[{category}]')
        print(f'{"파일":<35} {"줄수":>6} {"함수":>5} {"클래스":>5} {"TODO":>5}')
        print('-' * 60)
        
        for filepath in file_list:
            full_path = os.path.join(BASE, filepath)
            if os.path.exists(full_path):
                stats = analyze_file(full_path)
                name = os.path.basename(filepath)
                print(f'{name:<35} {stats["lines"]:>6} {stats["functions"]:>5} {stats["classes"]:>5} {stats["todos"]:>5}')
                
                for k, v in stats.items():
                    total_stats[k] += v
                
                if stats['lines'] > 1000:
                    large_files.append((filepath, stats['lines']))
        print()
    
    # Summary
    print('=' * 70)
    print('=== 요약 ===')
    print('=' * 70)
    print()
    print(f'총 줄수: {total_stats["lines"]:,}줄')
    print(f'총 함수: {total_stats["functions"]}개')
    print(f'총 클래스: {total_stats["classes"]}개')
    print(f'TODO/FIXME: {total_stats["todos"]}개')
    print(f'매직넘버 추정: {total_stats["magic_numbers"]}개')
    print()
    
    # Large files
    if large_files:
        print('[1000줄 이상 대형 파일]')
        for f, lines in sorted(large_files, key=lambda x: -x[1]):
            status = '🔴' if lines > 2000 else '🟡'
            print(f'  {status} {f}: {lines}줄')
    print()
    
    # Recommendations
    print('=' * 70)
    print('=== 권장 조치 ===')
    print('=' * 70)
    print()
    print('[우선순위 1: 즉시 적용 가능]')
    print('  • 미사용 import 제거 (자동화 가능)')
    print('  • TODO/FIXME 정리 또는 이슈 등록')
    print()
    print('[우선순위 2: 안정성 유지하며 진행]')
    print('  • 대형 파일 점진적 분리')
    print('  • 하드코딩 상수 → config 이동')
    print()
    print('[우선순위 3: 시간 여유 시]')
    print('  • 타입 힌트 추가')
    print('  • Docstring 보강')

if __name__ == "__main__":
    main()
