from pathlib import Path
import re

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')

# Fix the specific pattern that causes quote collisions in f-strings
# Search for: (self.exchange.attr if self.exchange else "Unknown")
# Replace with: (self.exchange.attr if self.exchange else 'Unknown')
# This is safe because Python 3.12+ handles nested quotes better, 
# but for compatibility and current environment, single quotes are safer inside f-string double quotes.

def fix_quotes(match):
    content = match.group(0)
    # If the match contains "Unknown", replace it with 'Unknown'
    return content.replace('"Unknown"', "'Unknown'")

# Pattern to find the ternary expressions with double quotes
code = re.sub(r'\(self\.exchange\.\w+ if self\.exchange else "Unknown"\)', fix_quotes, code)

bot.write_text(code, encoding='utf-8')
print("✅ Quote collision fix complete.")

# Final check with py_compile
import py_compile
try:
    py_compile.compile(str(bot), doraise=True)
    print("✅ unified_bot.py is now syntactically correct.")
except py_compile.PyCompileError as e:
    print(f"❌ Still has syntax error: {e}")
