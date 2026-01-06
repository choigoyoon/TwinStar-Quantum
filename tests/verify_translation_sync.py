
import json
import os

def check_keys():
    ko_path = r"C:\매매전략\locales\ko.json"
    en_path = r"C:\매매전략\locales\en.json"
    
    with open(ko_path, 'r', encoding='utf-8') as f:
        ko = json.load(f)
    with open(en_path, 'r', encoding='utf-8') as f:
        en = json.load(f)
        
    def get_all_keys(d, parent=""):
        keys = set()
        for k, v in d.items():
            full_key = f"{parent}.{k}" if parent else k
            if isinstance(v, dict):
                keys.update(get_all_keys(v, full_key))
            else:
                keys.add(full_key)
        return keys

    ko_keys = get_all_keys(ko)
    en_keys = get_all_keys(en)
    
    only_ko = ko_keys - en_keys
    only_en = en_keys - ko_keys
    
    print(f"Total KO keys: {len(ko_keys)}")
    print(f"Total EN keys: {len(en_keys)}")
    
    if only_ko:
        print("\n[WARNING] Keys only in KO:")
        for k in sorted(only_ko):
            print(f"  - {k}")
            
    if only_en:
        print("\n[WARNING] Keys only in EN:")
        for k in sorted(only_en):
            print(f"  - {k}")
            
    if not only_ko and not only_en:
        print("\n[SUCCESS] All keys are perfectly synced!")

if __name__ == "__main__":
    check_keys()
