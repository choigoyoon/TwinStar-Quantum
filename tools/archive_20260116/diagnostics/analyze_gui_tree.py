"""
GUI 모듈 의존성 트리 분석
"""
import os
import re
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict

def extract_imports(file_path: str) -> Set[str]:
    """파일에서 import 문 추출"""
    imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # from X import Y 패턴
        for match in re.finditer(r'from\s+([\w.]+)\s+import', content):
            module = match.group(1)
            imports.add(module)

        # import X 패턴
        for match in re.finditer(r'^import\s+([\w.]+)', content, re.MULTILINE):
            module = match.group(1)
            imports.add(module)

    except Exception as e:
        pass

    return imports


def is_project_module(module: str) -> bool:
    """프로젝트 내부 모듈인지 확인"""
    project_packages = [
        'GUI', 'ui', 'core', 'exchanges', 'strategies',
        'trading', 'utils', 'storage', 'locales', 'config'
    ]
    return any(module.startswith(pkg) for pkg in project_packages)


def scan_gui_modules() -> Dict[str, Dict]:
    """GUI 관련 모듈 스캔"""
    gui_dirs = ['GUI', 'ui']
    modules = {}

    for gui_dir in gui_dirs:
        if not os.path.exists(gui_dir):
            continue

        for root, dirs, files in os.walk(gui_dir):
            # __pycache__ 제외
            dirs[:] = [d for d in dirs if d != '__pycache__']

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = file_path.replace('\\', '/')

                    # 모듈 경로 생성
                    module_path = rel_path.replace('/', '.').replace('.py', '')

                    imports = extract_imports(file_path)
                    project_imports = {imp for imp in imports if is_project_module(imp)}
                    external_imports = imports - project_imports

                    modules[module_path] = {
                        'path': file_path,
                        'imports': project_imports,
                        'external': external_imports,
                        'size': os.path.getsize(file_path)
                    }

    return modules


def build_dependency_tree(modules: Dict[str, Dict]) -> Dict[str, Set[str]]:
    """의존성 트리 구축"""
    tree = defaultdict(set)

    for module, info in modules.items():
        for imp in info['imports']:
            tree[module].add(imp)

    return tree


def find_entry_points(modules: Dict[str, Dict]) -> List[str]:
    """GUI 진입점 찾기 (main, window 등)"""
    entry_points = []

    keywords = ['main', 'window', 'app', 'staru']

    for module in modules.keys():
        module_lower = module.lower()
        if any(kw in module_lower for kw in keywords):
            entry_points.append(module)

    return sorted(entry_points)


def print_tree(module: str, tree: Dict[str, Set[str]], visited: Set[str],
               indent: int = 0, max_depth: int = 3):
    """의존성 트리 출력"""
    if indent > max_depth or module in visited:
        return

    visited.add(module)
    prefix = "  " * indent + "├─ " if indent > 0 else ""

    print(f"{prefix}{module}")

    if module in tree:
        deps = sorted(tree[module])
        for dep in deps:
            if is_project_module(dep):
                print_tree(dep, tree, visited.copy(), indent + 1, max_depth)


def analyze_module_stats(modules: Dict[str, Dict]) -> Dict:
    """모듈 통계 분석"""
    stats = {
        'total_modules': len(modules),
        'gui_legacy': 0,
        'ui_new': 0,
        'total_size': 0,
        'avg_imports': 0.0,
        'max_imports': 0,
    }

    import_counts = []

    for module, info in modules.items():
        if module.startswith('GUI'):
            stats['gui_legacy'] += 1
        elif module.startswith('ui'):
            stats['ui_new'] += 1

        stats['total_size'] += info['size']

        import_count = len(info['imports'])
        import_counts.append(import_count)
        stats['max_imports'] = max(stats['max_imports'], import_count)

    if import_counts:
        stats['avg_imports'] = sum(import_counts) / len(import_counts)

    return stats


def main():
    print("=" * 70)
    print("GUI Module Dependency Tree Analysis")
    print("=" * 70)
    print()

    # 모듈 스캔
    print("Scanning GUI modules...")
    modules = scan_gui_modules()

    # 통계
    stats = analyze_module_stats(modules)
    print("\n=== Module Statistics ===")
    print(f"Total modules: {stats['total_modules']}")
    print(f"  - GUI (legacy): {stats['gui_legacy']}")
    print(f"  - ui (new): {stats['ui_new']}")
    print(f"Total size: {stats['total_size'] / 1024:.1f} KB")
    print(f"Average imports per module: {stats['avg_imports']:.1f}")
    print(f"Max imports in a module: {stats['max_imports']}")

    # 진입점
    print("\n=== Entry Points ===")
    entry_points = find_entry_points(modules)
    for ep in entry_points:
        print(f"  - {ep}")

    # 의존성 트리
    tree = build_dependency_tree(modules)

    print("\n=== Dependency Trees (Top 5 Entry Points) ===")
    for ep in entry_points[:5]:
        print(f"\n{ep}:")
        visited: Set[str] = set()
        print_tree(ep, tree, visited, indent=0, max_depth=2)

    # 핵심 의존 모듈
    print("\n=== Most Imported Modules (Top 10) ===")
    import_count: Dict[str, int] = defaultdict(int)
    for module, deps in tree.items():
        for dep in deps:
            if is_project_module(dep):
                import_count[dep] += 1

    top_imports = sorted(import_count.items(), key=lambda x: x[1], reverse=True)[:10]
    for i, (module, count) in enumerate(top_imports, 1):
        print(f"{i:2d}. {module:40s} ({count} references)")

    # 외부 의존성
    print("\n=== External Dependencies (Top 10) ===")
    external_count: Dict[str, int] = defaultdict(int)
    for info in modules.values():
        for ext in info['external']:
            # 첫 번째 패키지만 추출
            pkg = ext.split('.')[0]
            external_count[pkg] += 1

    top_external = sorted(external_count.items(), key=lambda x: x[1], reverse=True)[:10]
    for i, (pkg, count) in enumerate(top_external, 1):
        print(f"{i:2d}. {pkg:30s} ({count} imports)")

    print("\n" + "=" * 70)
    print("[DONE] Analysis complete")
    print("=" * 70)


if __name__ == '__main__':
    main()
