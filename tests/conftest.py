"""
pytest conftest.py - Shared fixtures for all tests
Handles QApplication singleton and headless environment detection
"""
import sys
import os
import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


def _is_display_available():
    """Check if display is available for GUI tests"""
    # Windows always has display
    if sys.platform == 'win32':
        return True
    # Linux/Mac check DISPLAY
    return bool(os.environ.get('DISPLAY'))


# Global QApplication instance
_qapp = None


@pytest.fixture(scope="session")
def qapp():
    """
    Session-scoped QApplication fixture.
    Creates a single QApplication instance for all GUI tests.
    """
    global _qapp
    
    if not _is_display_available():
        pytest.skip("No display available for GUI tests")
    
    try:
        from PyQt6.QtWidgets import QApplication
        
        # Use existing instance if available
        _qapp = QApplication.instance()
        if _qapp is None:
            _qapp = QApplication([])
        
        yield _qapp
        
    except ImportError:
        pytest.skip("PyQt5 not installed")


@pytest.fixture
def qtbot(qapp):
    """
    Qt test helper (simplified version).
    For full functionality, install pytest-qt.
    """
    class SimpleQtBot:
        def __init__(self, app):
            self.app = app
        
        def addWidget(self, widget):
            pass
        
        def wait(self, ms):
            import time
            time.sleep(ms / 1000)
    
    return SimpleQtBot(qapp)


# Auto-use fixture to ensure QApplication exists for test_gui_* files
@pytest.fixture(autouse=True)
def auto_qapp(request):
    """Auto-create QApplication for GUI test files"""
    if 'test_gui' in request.fspath.basename or 'test_phase7_gui' in request.fspath.basename:
        global _qapp
        try:
            from PyQt6.QtWidgets import QApplication
            _qapp = QApplication.instance()
            if _qapp is None:
                _qapp = QApplication([])
        except ImportError:
            pass


# Skip marker for headless environments
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "gui: mark test as requiring GUI environment"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip GUI tests in headless environment"""
    if not _is_display_available():
        skip_gui = pytest.mark.skip(reason="No display available")
        for item in items:
            if "gui" in item.keywords or "test_gui" in item.fspath.basename:
                item.add_marker(skip_gui)
