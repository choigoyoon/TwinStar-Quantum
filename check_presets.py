"""프리셋 JSON 파라미터 확인"""
import json
from pathlib import Path

presets_dir = Path('config/presets')
print("=" * 60)
print("📊 프리셋 JSON 파라미터 확인")
print("=" * 60)

for p in sorted(presets_dir.glob('*.json'))[:15]:
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        atr = data.get('atr_mult', 'N/A')
        trail_s = data.get('trail_start_r', 'N/A')
        trail_d = data.get('trail_dist_r', 'N/A')
        validity = data.get('entry_validity_hours', 'N/A')
        print(f"{p.name[:40]:40} | atr={atr}, trail_s={trail_s}, trail_d={trail_d}, validity={validity}")
    except Exception as e:
        print(f"{p.name}: Error - {e}")
