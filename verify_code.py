#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""코드 무결성 검증 스크립트"""

import ast
import os

files = [
    "GUI/trading_dashboard.py",
    "core/unified_bot.py",
    "exchanges/exchange_manager.py",
    "GUI/settings_widget.py",
    "GUI/optimization_widget.py",
    "GUI/backtest_widget.py",
    "core/optimizer.py"
]

print("=" * 60)
print("📋 코드 무결성 검증")
print("=" * 60)

all_ok = True
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            content = fp.read()
        ast.parse(content)
        print(f"✅ {f}")
    except SyntaxError as e:
        print(f"❌ {f}: Line {e.lineno} - {e.msg}")
        all_ok = False
    except FileNotFoundError:
        print(f"⚠️ {f}: 파일 없음")
    except Exception as e:
        print(f"❌ {f}: {e}")
        all_ok = False

print("=" * 60)
if all_ok:
    print("✅ 모든 파일 문법 검증 통과 - 빌드 가능")
else:
    print("❌ 문법 오류 발견 - 수정 필요")
