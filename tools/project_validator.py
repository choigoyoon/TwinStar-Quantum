#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TwinStar-Quantum 프로젝트 검증 도구 (v1.0)

기능:
1. Import 연결 검증 - 모든 모듈의 import 문 유효성 검사
2. 문법 오류 검증 - AST 파싱으로 Python 문법 오류 탐지
3. 중복 계산 탐지 - 동일 함수/클래스 정의 중복 검사
4. 병목 분석 - 순환 import, 과도한 의존성 탐지
5. GUI-Core 연결 검증 - GUI 위젯과 Core 모듈 간 연결 상태 확인

사용법:
    python tools/project_validator.py [옵션]

옵션:
    --all           모든 검증 실행 (기본값)
    --import        Import 검증만 실행
    --syntax        문법 검증만 실행
    --duplicate     중복 검증만 실행
    --bottleneck    병목 분석만 실행
    --connection    GUI-Core 연결 검증만 실행
    --fix           자동 수정 가능한 문제 수정 (주의 필요)
    --output FILE   결과를 파일로 출력
"""

import os
import sys
import ast
import re
import argparse
import importlib.util
import io
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime
import traceback

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# 데이터 클래스 정의
# ============================================================================

@dataclass
class Issue:
    """검증 이슈"""
    level: str  # 'ERROR', 'WARNING', 'INFO'
    category: str  # 'import', 'syntax', 'duplicate', 'bottleneck', 'connection'
    file_path: str
    line_number: int
    message: str
    suggestion: str = ""

    def __str__(self) -> str:
        loc = f"{self.file_path}:{self.line_number}"
        return f"[{self.level}] {self.category.upper()} - {loc}\n  {self.message}"


@dataclass
class ModuleInfo:
    """모듈 정보"""
    path: Path
    name: str
    imports: List[str] = field(default_factory=list)
    from_imports: List[Tuple[str, List[str]]] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    parse_error: Optional[str] = None


@dataclass
class ValidationResult:
    """검증 결과"""
    total_files: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    issues: List[Issue] = field(default_factory=list)
    modules: Dict[str, ModuleInfo] = field(default_factory=dict)

    def add_issue(self, issue: Issue):
        self.issues.append(issue)
        if issue.level == 'ERROR':
            self.error_count += 1
        elif issue.level == 'WARNING':
            self.warning_count += 1
        else:
            self.info_count += 1


# ============================================================================
# 검증 클래스
# ============================================================================

class ProjectValidator:
    """프로젝트 검증기"""

    # 검사할 디렉토리
    TARGET_DIRS = ['GUI', 'ui', 'core', 'exchanges', 'utils', 'config', 'trading', 'strategies', 'storage']

    # 무시할 파일 패턴
    IGNORE_PATTERNS = [
        r'__pycache__',
        r'\.pyc$',
        r'test_.*\.py$',
        r'.*_test\.py$',
        r'tmpclaude.*',
    ]

    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.root = project_root
        self.result = ValidationResult()
        self.modules: Dict[str, ModuleInfo] = {}
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)

    def collect_python_files(self) -> List[Path]:
        """Python 파일 수집"""
        files = []

        for dir_name in self.TARGET_DIRS:
            dir_path = self.root / dir_name
            if dir_path.exists():
                for py_file in dir_path.rglob('*.py'):
                    # 무시 패턴 체크
                    skip = False
                    for pattern in self.IGNORE_PATTERNS:
                        if re.search(pattern, str(py_file)):
                            skip = True
                            break
                    if not skip:
                        files.append(py_file)

        # main.py 추가
        main_py = self.root / 'main.py'
        if main_py.exists():
            files.append(main_py)

        return files

    def parse_module(self, file_path: Path) -> ModuleInfo:
        """모듈 파싱"""
        rel_path = file_path.relative_to(self.root)
        module_name = str(rel_path).replace(os.sep, '.').replace('.py', '')

        info = ModuleInfo(
            path=file_path,
            name=module_name
        )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                # Import 문 수집
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        info.imports.append(alias.name)
                        info.dependencies.add(alias.name.split('.')[0])

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        names = [alias.name for alias in node.names]
                        info.from_imports.append((node.module, names))
                        info.dependencies.add(node.module.split('.')[0])

                # 클래스 정의 수집
                elif isinstance(node, ast.ClassDef):
                    info.classes.append(node.name)

                # 함수 정의 수집
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    # 최상위 함수만
                    if hasattr(node, 'col_offset') and node.col_offset == 0:
                        info.functions.append(node.name)

        except SyntaxError as e:
            info.parse_error = str(e)
            self.result.add_issue(Issue(
                level='ERROR',
                category='syntax',
                file_path=str(rel_path),
                line_number=e.lineno or 0,
                message=f"문법 오류: {e.msg}",
                suggestion="Python 3.12 문법에 맞게 수정하세요"
            ))

        except Exception as e:
            info.parse_error = str(e)

        return info

    # ========================================================================
    # 1. Import 검증
    # ========================================================================

    def validate_imports(self):
        """Import 연결 검증"""
        print("\n🔍 [1/5] Import 연결 검증 중...")

        for module_name, info in self.modules.items():
            if info.parse_error:
                continue

            rel_path = info.path.relative_to(self.root)

            # import 문 검증
            for imp in info.imports:
                self._check_import(str(rel_path), imp, 0)

            # from import 문 검증
            for module, names in info.from_imports:
                self._check_from_import(str(rel_path), module, names, 0)

    def _check_import(self, file_path: str, module_name: str, line: int):
        """import 문 검증"""
        # 표준 라이브러리는 스킵
        if self._is_stdlib(module_name):
            return

        # 외부 패키지는 스킵 (설치 여부만 체크)
        if self._is_external_package(module_name):
            if not self._is_package_installed(module_name):
                self.result.add_issue(Issue(
                    level='WARNING',
                    category='import',
                    file_path=file_path,
                    line_number=line,
                    message=f"외부 패키지 '{module_name}'가 설치되지 않았을 수 있음",
                    suggestion=f"pip install {module_name}"
                ))
            return

        # 프로젝트 내부 모듈 검증
        module_path = self._resolve_module_path(module_name)
        if module_path is None:
            self.result.add_issue(Issue(
                level='ERROR',
                category='import',
                file_path=file_path,
                line_number=line,
                message=f"모듈 '{module_name}'를 찾을 수 없음",
                suggestion="모듈 경로나 이름을 확인하세요"
            ))

    def _check_from_import(self, file_path: str, module_name: str, names: List[str], line: int):
        """from import 문 검증"""
        if self._is_stdlib(module_name):
            return

        if self._is_external_package(module_name):
            return

        # 상대 import 처리
        if module_name.startswith('.'):
            return  # 상대 import는 별도 처리 필요

        module_path = self._resolve_module_path(module_name)
        if module_path is None:
            self.result.add_issue(Issue(
                level='ERROR',
                category='import',
                file_path=file_path,
                line_number=line,
                message=f"모듈 '{module_name}'를 찾을 수 없음",
                suggestion="모듈 경로나 이름을 확인하세요"
            ))
            return

        # 해당 모듈에서 name이 정의되어 있는지 확인
        if module_name in self.modules:
            module_info = self.modules[module_name]
            for name in names:
                if name == '*':
                    continue
                if name not in module_info.classes and name not in module_info.functions:
                    # __init__.py에서 re-export 할 수 있으므로 WARNING
                    self.result.add_issue(Issue(
                        level='WARNING',
                        category='import',
                        file_path=file_path,
                        line_number=line,
                        message=f"'{module_name}'에서 '{name}'를 찾을 수 없음 (re-export 가능)",
                        suggestion="해당 모듈의 __init__.py를 확인하세요"
                    ))

    def _is_stdlib(self, module_name: str) -> bool:
        """표준 라이브러리 여부"""
        stdlib_modules = {
            'os', 'sys', 're', 'json', 'math', 'time', 'datetime', 'collections',
            'typing', 'dataclasses', 'abc', 'functools', 'itertools', 'operator',
            'pathlib', 'logging', 'traceback', 'threading', 'queue', 'asyncio',
            'concurrent', 'multiprocessing', 'socket', 'ssl', 'http', 'urllib',
            'hashlib', 'hmac', 'secrets', 'base64', 'pickle', 'copy', 'pprint',
            'textwrap', 'unicodedata', 'string', 'struct', 'codecs', 'locale',
            'gettext', 'argparse', 'configparser', 'csv', 'sqlite3', 'email',
            'html', 'xml', 'webbrowser', 'ctypes', 'enum', 'decimal', 'fractions',
            'random', 'statistics', 'bisect', 'heapq', 'array', 'weakref',
            'contextlib', 'inspect', 'warnings', 'unittest', 'doctest',
            'io', 'tempfile', 'shutil', 'glob', 'fnmatch', 'platform',
            'subprocess', 'sched', 'signal', 'atexit', 'uuid'
        }
        return module_name.split('.')[0] in stdlib_modules

    def _is_external_package(self, module_name: str) -> bool:
        """외부 패키지 여부"""
        external_packages = {
            'PyQt6', 'PyQt5', 'PySide6', 'pandas', 'numpy', 'ccxt',
            'pyqtgraph', 'cryptography', 'requests', 'aiohttp', 'websocket',
            'websockets', 'ta', 'pandas_ta', 'matplotlib', 'scipy',
            'PIL', 'pillow', 'cv2', 'opencv', 'sklearn', 'torch',
            'tensorflow', 'keras', 'dotenv', 'yaml', 'toml', 'httpx'
        }
        root = module_name.split('.')[0]
        return root in external_packages

    def _is_package_installed(self, package_name: str) -> bool:
        """패키지 설치 여부"""
        try:
            spec = importlib.util.find_spec(package_name.split('.')[0])
            return spec is not None
        except:
            return False

    def _resolve_module_path(self, module_name: str) -> Optional[Path]:
        """모듈 경로 해석"""
        parts = module_name.split('.')

        # 디렉토리로 해석 (패키지)
        dir_path = self.root.joinpath(*parts)
        if dir_path.is_dir() and (dir_path / '__init__.py').exists():
            return dir_path / '__init__.py'

        # 파일로 해석
        if len(parts) > 1:
            file_path = self.root.joinpath(*parts[:-1]) / f"{parts[-1]}.py"
        else:
            file_path = self.root / f"{parts[0]}.py"

        if file_path.exists():
            return file_path

        # 전체 경로로 해석 (module.py)
        full_path = self.root.joinpath(*parts)
        full_path_py = Path(str(full_path) + '.py')
        if full_path_py.exists():
            return full_path_py

        return None

    # ========================================================================
    # 2. 문법 검증
    # ========================================================================

    def validate_syntax(self):
        """문법 오류 검증 (이미 parse_module에서 수행)"""
        print("\n🔍 [2/5] 문법 오류 검증 중...")

        # 추가적인 문법 패턴 검사
        for module_name, info in self.modules.items():
            if info.parse_error:
                continue

            self._check_python312_compatibility(info)

    def _check_python312_compatibility(self, info: ModuleInfo):
        """Python 3.12 호환성 검사"""
        try:
            with open(info.path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            rel_path = str(info.path.relative_to(self.root))

            for i, line in enumerate(lines, 1):
                # 구식 문자열 포맷팅 체크
                if '%s' in line or '%d' in line or '%f' in line:
                    if 'logger' not in line.lower() and 'logging' not in line.lower():
                        self.result.add_issue(Issue(
                            level='INFO',
                            category='syntax',
                            file_path=rel_path,
                            line_number=i,
                            message="구식 문자열 포맷팅 사용",
                            suggestion="f-string 사용 권장"
                        ))

                # PyQt5 → PyQt6 마이그레이션 체크
                if 'from PyQt5' in line or 'import PyQt5' in line:
                    self.result.add_issue(Issue(
                        level='WARNING',
                        category='syntax',
                        file_path=rel_path,
                        line_number=i,
                        message="PyQt5 사용 감지 - PyQt6로 마이그레이션 필요",
                        suggestion="PyQt5 → PyQt6으로 변경"
                    ))

                # exec() 동적 실행 체크
                if 'exec(' in line and not line.strip().startswith('#'):
                    self.result.add_issue(Issue(
                        level='WARNING',
                        category='syntax',
                        file_path=rel_path,
                        line_number=i,
                        message="exec() 동적 실행 감지 - 보안 주의",
                        suggestion="가능하면 정적 코드로 대체"
                    ))

        except Exception as e:
            pass

    # ========================================================================
    # 3. 중복 검증
    # ========================================================================

    def validate_duplicates(self):
        """중복 코드 탐지"""
        print("\n🔍 [3/5] 중복 코드 탐지 중...")

        # 클래스 이름 중복 검사
        class_locations: Dict[str, List[str]] = defaultdict(list)
        for module_name, info in self.modules.items():
            for cls_name in info.classes:
                class_locations[cls_name].append(str(info.path.relative_to(self.root)))

        for cls_name, locations in class_locations.items():
            if len(locations) > 1:
                self.result.add_issue(Issue(
                    level='WARNING',
                    category='duplicate',
                    file_path=locations[0],
                    line_number=0,
                    message=f"클래스 '{cls_name}'가 여러 파일에 정의됨: {', '.join(locations)}",
                    suggestion="의도적 중복이 아니라면 통합 고려"
                ))

        # 함수 이름 중복 검사 (동일 디렉토리 내)
        self._check_function_duplicates()

        # 상수 중복 정의 검사
        self._check_constant_duplicates()

    def _check_function_duplicates(self):
        """함수 중복 검사"""
        dir_functions: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))

        for module_name, info in self.modules.items():
            dir_name = str(info.path.parent.relative_to(self.root))
            for func_name in info.functions:
                if not func_name.startswith('_'):  # private 제외
                    dir_functions[dir_name][func_name].append(str(info.path.relative_to(self.root)))

        for dir_name, funcs in dir_functions.items():
            for func_name, locations in funcs.items():
                if len(locations) > 1:
                    self.result.add_issue(Issue(
                        level='INFO',
                        category='duplicate',
                        file_path=locations[0],
                        line_number=0,
                        message=f"함수 '{func_name}'가 {dir_name}/ 내 여러 파일에 정의: {len(locations)}개",
                        suggestion="유틸리티로 통합 고려"
                    ))

    def _check_constant_duplicates(self):
        """상수 중복 정의 검사"""
        constant_pattern = re.compile(r'^([A-Z][A-Z0-9_]+)\s*=\s*[^=]')
        constant_locations: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

        for module_name, info in self.modules.items():
            if info.parse_error:
                continue

            try:
                with open(info.path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        match = constant_pattern.match(line.strip())
                        if match:
                            const_name = match.group(1)
                            rel_path = str(info.path.relative_to(self.root))
                            constant_locations[const_name].append((rel_path, i))
            except:
                pass

        # config/ 외부에서 정의된 상수 중 config/에도 있는 것
        for const_name, locations in constant_locations.items():
            config_locs = [loc for loc in locations if loc[0].startswith('config')]
            non_config_locs = [loc for loc in locations if not loc[0].startswith('config')]

            if config_locs and non_config_locs:
                for loc in non_config_locs:
                    self.result.add_issue(Issue(
                        level='WARNING',
                        category='duplicate',
                        file_path=loc[0],
                        line_number=loc[1],
                        message=f"상수 '{const_name}'가 config/ 외부에서 재정의됨",
                        suggestion="config/에서 import하여 사용하세요 (SSOT 원칙)"
                    ))

    # ========================================================================
    # 4. 병목 분석
    # ========================================================================

    def validate_bottlenecks(self):
        """병목 지점 분석"""
        print("\n🔍 [4/5] 병목 지점 분석 중...")

        # Import 그래프 구축
        self._build_import_graph()

        # 순환 의존성 탐지
        self._detect_circular_imports()

        # 과도한 의존성 탐지
        self._detect_heavy_dependencies()

        # God 클래스 탐지
        self._detect_god_classes()

    def _build_import_graph(self):
        """Import 그래프 구축"""
        for module_name, info in self.modules.items():
            for imp in info.imports:
                if not self._is_stdlib(imp) and not self._is_external_package(imp):
                    self.import_graph[module_name].add(imp.split('.')[0])

            for module, _ in info.from_imports:
                if not self._is_stdlib(module) and not self._is_external_package(module):
                    self.import_graph[module_name].add(module.split('.')[0])

    def _detect_circular_imports(self):
        """순환 Import 탐지"""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.import_graph.get(node, []):
                dfs(neighbor, path + [node])

            rec_stack.remove(node)

        for node in self.import_graph:
            if node not in visited:
                dfs(node, [])

        for cycle in cycles:
            self.result.add_issue(Issue(
                level='ERROR',
                category='bottleneck',
                file_path=cycle[0],
                line_number=0,
                message=f"순환 Import 감지: {' → '.join(cycle)}",
                suggestion="의존성 구조 재설계 또는 지연 import 사용"
            ))

    def _detect_heavy_dependencies(self):
        """과도한 의존성 탐지"""
        for module_name, info in self.modules.items():
            dep_count = len(info.dependencies)
            if dep_count > 15:
                self.result.add_issue(Issue(
                    level='WARNING',
                    category='bottleneck',
                    file_path=str(info.path.relative_to(self.root)),
                    line_number=0,
                    message=f"과도한 의존성: {dep_count}개 모듈 import",
                    suggestion="모듈 분리 또는 인터페이스 추상화 고려"
                ))

    def _detect_god_classes(self):
        """God 클래스 탐지 (메서드 수 기반)"""
        for module_name, info in self.modules.items():
            if info.parse_error:
                continue

            try:
                with open(info.path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        method_count = sum(1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
                        if method_count > 30:
                            self.result.add_issue(Issue(
                                level='WARNING',
                                category='bottleneck',
                                file_path=str(info.path.relative_to(self.root)),
                                line_number=node.lineno,
                                message=f"God 클래스 '{node.name}': {method_count}개 메서드",
                                suggestion="책임 분리하여 클래스 분할 고려"
                            ))
            except:
                pass

    # ========================================================================
    # 5. GUI-Core 연결 검증
    # ========================================================================

    def validate_connections(self):
        """GUI-Core 연결 검증"""
        print("\n🔍 [5/5] GUI-Core 연결 검증 중...")

        gui_modules = {name: info for name, info in self.modules.items() if name.startswith('GUI')}
        core_modules = {name: info for name, info in self.modules.items() if name.startswith('core')}
        exchange_modules = {name: info for name, info in self.modules.items() if name.startswith('exchanges')}

        # GUI → Core 연결 매핑
        connections: Dict[str, Set[str]] = defaultdict(set)

        for gui_name, gui_info in gui_modules.items():
            for module, names in gui_info.from_imports:
                if module.startswith('core.'):
                    connections[gui_name].add(module)
                elif module.startswith('exchanges.'):
                    connections[gui_name].add(module)

        # 연결되지 않은 Core 모듈 탐지
        connected_cores = set()
        for conns in connections.values():
            for conn in conns:
                connected_cores.add(conn)

        for core_name in core_modules:
            if core_name not in connected_cores and not core_name.endswith('__init__'):
                # GUI에서 직접 사용되지 않는 core 모듈
                self.result.add_issue(Issue(
                    level='INFO',
                    category='connection',
                    file_path=str(core_modules[core_name].path.relative_to(self.root)),
                    line_number=0,
                    message=f"GUI에서 직접 사용되지 않는 Core 모듈",
                    suggestion="다른 core 모듈을 통해 간접 사용될 수 있음"
                ))

        # GUI 위젯 연결 상태 요약
        print(f"\n  📊 GUI-Core 연결 현황:")
        print(f"     - GUI 모듈: {len(gui_modules)}개")
        print(f"     - Core 모듈: {len(core_modules)}개")
        print(f"     - Exchange 모듈: {len(exchange_modules)}개")
        print(f"     - 직접 연결: {sum(len(v) for v in connections.values())}개")

    # ========================================================================
    # 실행 메서드
    # ========================================================================

    def run(self,
            check_import: bool = True,
            check_syntax: bool = True,
            check_duplicate: bool = True,
            check_bottleneck: bool = True,
            check_connection: bool = True) -> ValidationResult:
        """검증 실행"""

        print("=" * 70)
        print("🚀 TwinStar-Quantum 프로젝트 검증 시작")
        print("=" * 70)
        print(f"📁 프로젝트 루트: {self.root}")
        print(f"🐍 Python 버전: {sys.version.split()[0]}")
        print(f"📅 검증 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 파일 수집
        files = self.collect_python_files()
        self.result.total_files = len(files)
        print(f"\n📄 검사 대상 파일: {len(files)}개")

        # 모듈 파싱
        print("\n⏳ 모듈 파싱 중...")
        for file_path in files:
            info = self.parse_module(file_path)
            self.modules[info.name] = info

        # 각 검증 실행
        if check_import:
            self.validate_imports()

        if check_syntax:
            self.validate_syntax()

        if check_duplicate:
            self.validate_duplicates()

        if check_bottleneck:
            self.validate_bottlenecks()

        if check_connection:
            self.validate_connections()

        self.result.modules = self.modules
        return self.result

    def print_report(self):
        """검증 결과 출력"""
        print("\n" + "=" * 70)
        print("📋 검증 결과 보고서")
        print("=" * 70)

        print(f"\n📊 요약:")
        print(f"   - 총 파일 수: {self.result.total_files}")
        print(f"   - ❌ 오류 (ERROR): {self.result.error_count}개")
        print(f"   - ⚠️  경고 (WARNING): {self.result.warning_count}개")
        print(f"   - ℹ️  정보 (INFO): {self.result.info_count}개")

        if self.result.issues:
            # 카테고리별 분류
            by_category: Dict[str, List[Issue]] = defaultdict(list)
            for issue in self.result.issues:
                by_category[issue.category].append(issue)

            for category, issues in sorted(by_category.items()):
                print(f"\n{'─' * 70}")
                print(f"📌 {category.upper()} 이슈 ({len(issues)}개)")
                print('─' * 70)

                # ERROR 먼저, 그 다음 WARNING, 마지막 INFO
                sorted_issues = sorted(issues, key=lambda x: {'ERROR': 0, 'WARNING': 1, 'INFO': 2}[x.level])

                for issue in sorted_issues[:20]:  # 카테고리당 최대 20개
                    level_icon = {'ERROR': '❌', 'WARNING': '⚠️', 'INFO': 'ℹ️'}[issue.level]
                    print(f"\n{level_icon} [{issue.level}] {issue.file_path}:{issue.line_number}")
                    print(f"   {issue.message}")
                    if issue.suggestion:
                        print(f"   💡 {issue.suggestion}")

                if len(issues) > 20:
                    print(f"\n   ... 외 {len(issues) - 20}개 이슈")

        print("\n" + "=" * 70)

        # 최종 판정
        if self.result.error_count == 0:
            print("✅ 검증 통과 - 심각한 오류 없음")
        else:
            print(f"❌ 검증 실패 - {self.result.error_count}개 오류 수정 필요")

        print("=" * 70)

    def save_report(self, output_path: Path):
        """보고서 파일 저장"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("TwinStar-Quantum 프로젝트 검증 보고서\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"프로젝트 루트: {self.root}\n")
            f.write(f"Python 버전: {sys.version.split()[0]}\n")
            f.write(f"검증 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write(f"총 파일 수: {self.result.total_files}\n")
            f.write(f"오류 (ERROR): {self.result.error_count}개\n")
            f.write(f"경고 (WARNING): {self.result.warning_count}개\n")
            f.write(f"정보 (INFO): {self.result.info_count}개\n\n")

            for issue in self.result.issues:
                f.write(f"[{issue.level}] {issue.category.upper()}\n")
                f.write(f"  파일: {issue.file_path}:{issue.line_number}\n")
                f.write(f"  메시지: {issue.message}\n")
                if issue.suggestion:
                    f.write(f"  제안: {issue.suggestion}\n")
                f.write("\n")

        print(f"\n📄 보고서 저장됨: {output_path}")


# ============================================================================
# CLI 인터페이스
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='TwinStar-Quantum 프로젝트 검증 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python tools/project_validator.py             # 모든 검증 실행
  python tools/project_validator.py --import    # Import 검증만
  python tools/project_validator.py --output report.txt  # 파일로 저장
        """
    )

    parser.add_argument('--all', action='store_true', default=True, help='모든 검증 실행 (기본값)')
    parser.add_argument('--import', dest='check_import', action='store_true', help='Import 검증만')
    parser.add_argument('--syntax', dest='check_syntax', action='store_true', help='문법 검증만')
    parser.add_argument('--duplicate', dest='check_duplicate', action='store_true', help='중복 검증만')
    parser.add_argument('--bottleneck', dest='check_bottleneck', action='store_true', help='병목 분석만')
    parser.add_argument('--connection', dest='check_connection', action='store_true', help='연결 검증만')
    parser.add_argument('--output', '-o', type=str, help='결과를 파일로 출력')

    args = parser.parse_args()

    # 특정 옵션이 지정되면 해당 검증만 실행
    specific_check = any([
        args.check_import,
        args.check_syntax,
        args.check_duplicate,
        args.check_bottleneck,
        args.check_connection
    ])

    if specific_check:
        check_import = args.check_import
        check_syntax = args.check_syntax
        check_duplicate = args.check_duplicate
        check_bottleneck = args.check_bottleneck
        check_connection = args.check_connection
    else:
        # 기본값: 모든 검증
        check_import = True
        check_syntax = True
        check_duplicate = True
        check_bottleneck = True
        check_connection = True

    # 검증 실행
    validator = ProjectValidator()
    result = validator.run(
        check_import=check_import,
        check_syntax=check_syntax,
        check_duplicate=check_duplicate,
        check_bottleneck=check_bottleneck,
        check_connection=check_connection
    )

    # 결과 출력
    validator.print_report()

    # 파일 저장
    if args.output:
        validator.save_report(Path(args.output))

    # 종료 코드
    sys.exit(1 if result.error_count > 0 else 0)


if __name__ == '__main__':
    main()
