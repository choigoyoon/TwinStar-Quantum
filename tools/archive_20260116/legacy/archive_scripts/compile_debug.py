import traceback
import py_compile
import sys

try:
    py_compile.compile(r'C:\매매전략\core\unified_bot.py', doraise=True)
    print("Compilation successful!")
except py_compile.PyCompileError as e:
    print("Compilation failed!")
    print(e.msg)
except Exception:
    traceback.print_exc()
