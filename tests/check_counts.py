"""조합 수 확인"""
import sys
sys.path.insert(0, '.')
from core.optimizer import generate_quick_grid, generate_standard_grid, generate_deep_grid

def count(grid):
    total = 1
    for values in grid.values():
        total *= len(values)
    return total

quick = generate_quick_grid('1h')
std = generate_standard_grid('1h')
deep = generate_deep_grid('1h')

print(f"Quick:    {count(quick):>10,}")
print(f"Standard: {count(std):>10,}")
print(f"Deep:     {count(deep):>10,}")
