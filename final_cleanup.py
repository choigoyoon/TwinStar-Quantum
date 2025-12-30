import re
from pathlib import Path

path = Path(r'C:\매매전략\core\unified_bot.py')
code = path.read_text(encoding='utf-8')

# Let's use a very safe approach to remove double wrapping
# Look for ((self.exchange.XYZ if self.exchange else DEF) if self.exchange else DEF)
# And replace with (self.exchange.XYZ if self.exchange else DEF)

def fix_double_wrap(match):
    # The inner part is group 1
    inner = match.group(1)
    return f'({inner})'

# This pattern matches ((inner) if self.exchange else default)
# where inner looks like self.exchange.XYZ if self.exchange else default
pattern = r'\(\((self\.exchange\.[\w.]+ if self\.exchange else [\w"\' ]+)\) if self\.exchange else [\w"\' ]+\)'
code = re.sub(pattern, fix_double_wrap, code)

# Second pass for cases without inner parentheses but still doubled
# ((self.exchange.XYZ if self.exchange else DEF) if self.exchange else DEF)
pattern2 = r'\(\(self\.exchange\.[\w.]+ if self\.exchange else [\w"\' ]+\) if self\.exchange else [\w"\' ]+\)'
def fix_double_wrap_no_inner(match):
    # Find the first self.exchange...else...
    m = re.search(r'self\.exchange\.[\w.]+ if self\.exchange else [\w"\' ]+', match.group(0))
    if m:
        return f'({m.group(0)})'
    return match.group(0)

code = re.sub(pattern2, fix_double_wrap_no_inner, code)

path.write_text(code, encoding='utf-8')
print("Final cleanup complete.")
