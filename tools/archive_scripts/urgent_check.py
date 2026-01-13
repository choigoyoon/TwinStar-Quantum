from pathlib import Path
import re
import os
import pandas as pd
import numpy as np

base = Path(r'C:\매매전략')

print('=' * 60)
print('🚨 긴급 버그 진단 보고서')
print('=' * 60)

# [1] 1000캔들 및 데이터 수집 제한 추적
print('\n[1] 1000캔들 제한 원인 추적')
f_dm = base / 'GUI' / 'data_manager.py'
if f_dm.exists():
    code = f_dm.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    # download 함수 분석
    print('\n--- data_manager.py: download() 분석 ---')
    in_download = False
    for i, line in enumerate(lines):
        if 'def download' in line:
            in_download = True
        if in_download:
            print(f'  L{i+1}: {line}')
            if 'return' in line and i > 210: # download 함수 끝 부근까지
                break

    # _fetch_ohlcv 분석
    print('\n--- data_manager.py: _fetch_ohlcv() 분석 ---')
    in_fetch = False
    target_lines = []
    for i, line in enumerate(lines):
        if 'def _fetch_ohlcv' in line:
            in_fetch = True
        if in_fetch:
            target_lines.append(f'  L{i+1}: {line}')
            if 'return all_data' in line:
                break
    for l in target_lines[:20]: print(l) # 앞부분
    print('  ...')
    for l in target_lines[-20:]: print(l) # 뒷부분

# [2] 덮어쓰기 문제 - to_parquet 분석
print('\n[2] 덮어쓰기 문제 추적 (to_parquet)')
for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.git' in str(f) or 'venv' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        if 'to_parquet' in code:
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'to_parquet' in line:
                    # 주변 5줄 확인
                    context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                    has_append = 'append' in context.lower()
                    status = '✅ append/merge' if has_append else '⚠️ overwrite'
                    print(f'  [{status}] {f.relative_to(base)} L{i+1}: {line.strip()[:60]}')
    except Exception:

        pass

# [3] 1000 하드코딩 전수 조사
print('\n[3] "1000" 하드코딩 전수 조사 (limit 관련)')
for f in [base/'GUI'/'data_manager.py', base/'GUI'/'data_collector_widget.py']:
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if '1000' in line and ('limit' in line.lower() or 'candle' in line.lower() or 'batch' in line.lower()):
                print(f'  {f.name} L{i+1}: {line.strip()[:70]}')

print('\n' + '=' * 60)
print('📊 진단 완료')
print('=' * 60)
