"""
GUI 위젯 기능 분석 스크립트
각 위젯의 클래스, 메서드, 기능을 체크
"""
import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class WidgetAnalyzer:
    """위젯 분석기"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.module_name = self._get_module_name(file_path)
        self.classes: List[Dict] = []
        self.functions: List[str] = []
        self.imports: Set[str] = set()

    def _get_module_name(self, path: str) -> str:
        """파일 경로를 모듈 이름으로 변환"""
        return path.replace('\\', '/').replace('.py', '').replace('/', '.')

    def analyze(self):
        """파일 분석"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # AST 파싱
            tree = ast.parse(content)

            # 클래스 추출
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class(node)
                    self.classes.append(class_info)
                elif isinstance(node, ast.FunctionDef) and not self._is_in_class(node, tree):
                    self.functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        self.imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self.imports.add(node.module)

        except Exception as e:
            pass

    def _is_in_class(self, func_node, tree) -> bool:
        """함수가 클래스 내부에 있는지 확인"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.walk(node):
                    if child is func_node:
                        return True
        return False

    def _analyze_class(self, node: ast.ClassDef) -> Dict:
        """클래스 분석"""
        methods = []
        signals = []
        slots = []
        properties = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_name = item.name

                # 메서드 분류
                if method_name.startswith('_') and not method_name.startswith('__'):
                    # Private method
                    methods.append(('private', method_name))
                elif method_name.startswith('__'):
                    # Magic method
                    methods.append(('magic', method_name))
                elif 'slot' in method_name.lower() or self._has_slot_decorator(item):
                    slots.append(method_name)
                else:
                    methods.append(('public', method_name))

            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # PyQt Signal 감지
                        if 'Signal' in ast.unparse(item.value):
                            signals.append(name)

        # 베이스 클래스
        bases = [self._get_base_name(base) for base in node.bases]

        return {
            'name': node.name,
            'bases': bases,
            'methods': methods,
            'signals': signals,
            'slots': slots,
            'total_methods': len(methods)
        }

    def _has_slot_decorator(self, node: ast.FunctionDef) -> bool:
        """Slot 데코레이터 확인"""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and 'slot' in decorator.id.lower():
                return True
            elif isinstance(decorator, ast.Attribute) and 'slot' in decorator.attr.lower():
                return True
        return False

    def _get_base_name(self, base) -> str:
        """베이스 클래스 이름 추출"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return base.attr
        return str(base)


def scan_widgets() -> Dict[str, WidgetAnalyzer]:
    """모든 위젯 스캔"""
    widgets = {}

    gui_dirs = ['GUI', 'ui']

    for gui_dir in gui_dirs:
        if not os.path.exists(gui_dir):
            continue

        for root, dirs, files in os.walk(gui_dir):
            dirs[:] = [d for d in dirs if d != '__pycache__']

            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)

                    analyzer = WidgetAnalyzer(file_path)
                    analyzer.analyze()

                    # 위젯 클래스가 있는 파일만 추가
                    if analyzer.classes:
                        widgets[analyzer.module_name] = analyzer

    return widgets


def categorize_widgets(widgets: Dict[str, WidgetAnalyzer]) -> Dict[str, List[str]]:
    """위젯 카테고리별 분류"""
    categories = defaultdict(list)

    widget_keywords = {
        'main': ['main', 'window', 'app'],
        'dialog': ['dialog', 'popup'],
        'widget': ['widget'],
        'component': ['component', 'card', 'button'],
        'page': ['page', 'step'],
        'chart': ['chart', 'plot', 'graph'],
        'table': ['table', 'list'],
    }

    for module_name, analyzer in widgets.items():
        categorized = False
        module_lower = module_name.lower()

        for category, keywords in widget_keywords.items():
            if any(kw in module_lower for kw in keywords):
                categories[category].append(module_name)
                categorized = True
                break

        if not categorized:
            categories['other'].append(module_name)

    return dict(categories)


def print_widget_summary(widgets: Dict[str, WidgetAnalyzer]):
    """위젯 요약 출력"""
    print("=" * 80)
    print("GUI Widget Function Check")
    print("=" * 80)
    print()

    # 전체 통계
    total_classes = sum(len(w.classes) for w in widgets.values())
    total_methods = sum(sum(c['total_methods'] for c in w.classes) for w in widgets.values())

    print(f"Total Modules: {len(widgets)}")
    print(f"Total Classes: {total_classes}")
    print(f"Total Methods: {total_methods}")
    print()

    # 카테고리별 분류
    categories = categorize_widgets(widgets)

    print("=" * 80)
    print("Widgets by Category")
    print("=" * 80)
    print()

    for category, modules in sorted(categories.items()):
        print(f"\n[{category.upper()}] ({len(modules)} modules)")
        print("-" * 80)

        for module_name in sorted(modules)[:10]:  # 상위 10개만
            analyzer = widgets[module_name]

            print(f"\n  {module_name}")

            for cls in analyzer.classes:
                print(f"    Class: {cls['name']}")

                if cls['bases']:
                    print(f"      Base: {', '.join(cls['bases'])}")

                # Public 메서드
                public_methods = [m[1] for m in cls['methods'] if m[0] == 'public']
                if public_methods:
                    print(f"      Public Methods ({len(public_methods)}): {', '.join(public_methods[:5])}")
                    if len(public_methods) > 5:
                        print(f"        ... and {len(public_methods) - 5} more")

                # Signals
                if cls['signals']:
                    print(f"      Signals: {', '.join(cls['signals'])}")

                # Slots
                if cls['slots']:
                    print(f"      Slots: {', '.join(cls['slots'])}")

        if len(modules) > 10:
            print(f"\n  ... and {len(modules) - 10} more modules")


def print_detailed_widget(module_name: str, analyzer: WidgetAnalyzer):
    """특정 위젯 상세 정보 출력"""
    print(f"\n{'=' * 80}")
    print(f"Module: {module_name}")
    print(f"Path: {analyzer.file_path}")
    print(f"{'=' * 80}")

    # 클래스 정보
    for cls in analyzer.classes:
        print(f"\nClass: {cls['name']}")
        print(f"  Inherits from: {', '.join(cls['bases']) if cls['bases'] else 'object'}")
        print(f"  Total methods: {cls['total_methods']}")

        # 메서드 분류
        print(f"\n  Methods:")

        public_methods = [m[1] for m in cls['methods'] if m[0] == 'public']
        private_methods = [m[1] for m in cls['methods'] if m[0] == 'private']
        magic_methods = [m[1] for m in cls['methods'] if m[0] == 'magic']

        if public_methods:
            print(f"    Public ({len(public_methods)}):")
            for method in public_methods:
                print(f"      - {method}()")

        if cls['signals']:
            print(f"    Signals ({len(cls['signals'])}):")
            for signal in cls['signals']:
                print(f"      - {signal}")

        if cls['slots']:
            print(f"    Slots ({len(cls['slots'])}):")
            for slot in cls['slots']:
                print(f"      - {slot}()")

        if private_methods:
            print(f"    Private ({len(private_methods)}): {', '.join(private_methods[:3])}")
            if len(private_methods) > 3:
                print(f"      ... and {len(private_methods) - 3} more")


def main():
    # 위젯 스캔
    print("Scanning widgets...")
    widgets = scan_widgets()

    # 요약 출력
    print_widget_summary(widgets)

    # 주요 위젯 상세 출력
    print("\n\n" + "=" * 80)
    print("DETAILED VIEW - Main Entry Points")
    print("=" * 80)

    main_widgets = [
        'GUI.staru_main',
        'GUI.experimental_main_window',
        'ui.widgets.dashboard.main',
    ]

    for module_name in main_widgets:
        if module_name in widgets:
            print_detailed_widget(module_name, widgets[module_name])

    print("\n" + "=" * 80)
    print("[DONE] Widget function check complete")
    print("=" * 80)


if __name__ == '__main__':
    main()
