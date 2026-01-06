"""전체 위젯/모듈 연결 검증 (간소화)"""
from pathlib import Path
import re
import py_compile

base = Path(r'C:\매매전략')
gui_dir = base / 'GUI'

print("=" * 60)
print("[1] 핵심 파일 문법 검사")
print("=" * 60)

critical = [
    gui_dir / 'trading_dashboard.py',
    gui_dir / 'staru_main.py',
    base / 'core' / 'unified_bot.py',
    base / 'core' / 'strategy_core.py',
]

syntax_ok = 0
for f in critical:
    try:
        py_compile.compile(str(f), doraise=True)
        print(f"  [OK] {f.name}")
        syntax_ok += 1
    except Exception as e:
        print(f"  [ERR] {f.name}: {str(e)[:40]}")

print(f"\n  결과: {syntax_ok}/{len(critical)} 통과")

print("\n" + "=" * 60)
print("[2] v1.6.3 신규 위젯 검사")
print("=" * 60)

dashboard = gui_dir / 'trading_dashboard.py'
code = dashboard.read_text(encoding='utf-8')

checks = {
    'self.current_label': 'self.current_label' in code,
    'self.pnl_label': 'self.pnl_label' in code,
    'self.lock_btn': 'self.lock_btn' in code,
    'self.arrow_label': 'self.arrow_label' in code,
    'def _toggle_lock': 'def _toggle_lock' in code,
    'def update_balance': 'def update_balance' in code,
}

for name, ok in checks.items():
    print(f"  {'[OK]' if ok else '[MISS]'} {name}")

v163_ok = sum(checks.values())
print(f"\n  결과: {v163_ok}/{len(checks)} 통과")

print("\n" + "=" * 60)
print("[3] 필수 메서드 검사")
print("=" * 60)

methods = [
    '_init_ui', '_add_coin_row', '_on_row_start', 
    '_sync_position_states', 'save_state', 'load_state'
]

method_ok = 0
for m in methods:
    if f'def {m}' in code:
        print(f"  [OK] def {m}")
        method_ok += 1
    else:
        print(f"  [MISS] def {m}")

print(f"\n  결과: {method_ok}/{len(methods)} 통과")

print("\n" + "=" * 60)
print("[4] 핵심 위젯 검사")
print("=" * 60)

widgets = ['position_table', 'pos_status_widget', 'log_text', 'coin_rows', 'running_bots']

widget_ok = 0
for w in widgets:
    if f'self.{w}' in code:
        print(f"  [OK] self.{w}")
        widget_ok += 1
    else:
        print(f"  [MISS] self.{w}")

print(f"\n  결과: {widget_ok}/{len(widgets)} 통과")

print("\n" + "=" * 60)
print("[최종] 종합 결과")
print("=" * 60)

total = syntax_ok + v163_ok + method_ok + widget_ok
max_total = len(critical) + len(checks) + len(methods) + len(widgets)

print(f"  총점: {total}/{max_total}")

if total == max_total:
    print("\n  [PASS] 모든 검사 통과! 빌드 가능")
else:
    print(f"\n  [WARN] {max_total - total}개 항목 확인 필요")
