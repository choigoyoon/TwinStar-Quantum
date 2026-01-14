#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_phase3_batch3.py - GUI Phase 3 Batch 3 Tests
Widgets:
1. GlossaryPopup (GUI/glossary_popup.py)
2. HelpDialog (GUI/help_dialog.py)
3. HelpPopup (GUI/help_popup.py)
4. HelpWidget (GUI/help_widget.py)
5. TierPopup (GUI/tier_popup.py)
"""
import sys
import os
from pathlib import Path
import logging
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "GUI")) # Add GUI to path
os.chdir(PROJECT_ROOT)

logging.basicConfig(level=logging.WARNING)

from PyQt6.QtWidgets import QApplication, QTabWidget

# Initialize QApplication once
app = QApplication.instance() or QApplication(sys.argv)

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def ok(self, name, condition, msg=""):
        if condition:
            print(f"  ✅ {name}")
            self.passed += 1
        else:
            print(f"  ❌ {name}: {msg}")
            self.failed += 1
            self.errors.append(f"{name}: {msg}")

def run_batch3_tests():
    print("\n" + "="*60)
    print("🧪 Phase 3 Batch 3 Tests (Help & Info)")
    print("="*60)
    
    result = TestResult()
    
    # ---------------------------------------------------------
    # 1. GlossaryPopup
    # ---------------------------------------------------------
    print("\n[1. GlossaryPopup]")
    try:
        from GUI.glossary_popup import GlossaryPopup
        print("  ✅ Import Successful")
        
        # Test default lang
        popup = GlossaryPopup(lang='ko')
        result.ok("Instance Created (ko)", popup is not None)
        result.ok("_populate_glossary exists", hasattr(popup, '_populate_glossary'))
        
        # Test english lang
        popup_en = GlossaryPopup(lang='en')
        result.ok("Instance Created (en)", popup_en is not None)
        
        popup.close()
        popup_en.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 2. HelpDialog
    # ---------------------------------------------------------
    print("\n[2. HelpDialog]")
    try:
        # Mock dependencies: user_guide, referral_links
        with patch.dict(sys.modules, {
            'user_guide': MagicMock(),
            'referral_links': MagicMock()
        }):
            # Setup mocks
            sys.modules['user_guide'].get_quick_start.return_value = "Quick Start Content"
            sys.modules['user_guide'].get_trading_method.return_value = {"strategy": "Trading Method Content"}
            sys.modules['user_guide'].get_faq.return_value = "FAQ Content"
            
            sys.modules['referral_links'].REFERRAL_LINKS = {
                'binance': {
                    'benefits': ['Benefit 1'],
                    'guide': 'Guide Text',
                    'link': 'http://example.com'
                }
            }

            from GUI.help_dialog import HelpDialog
            print("  ✅ Import Successful")
            
            dialog = HelpDialog()
            result.ok("Instance Created", dialog is not None)
            result.ok("Quick Start Tab exists", hasattr(dialog, '_create_quick_start_tab'))
            result.ok("Trading Method Tab exists", hasattr(dialog, '_create_trading_methods_tab'))
            result.ok("Referral Tab exists", hasattr(dialog, '_create_referral_tab'))
            result.ok("FAQ Tab exists", hasattr(dialog, '_create_faq_tab'))
            
            # Test usage of mocks
            from PyQt6.QtWidgets import QTextBrowser
            current_tab = dialog.findChild(QTabWidget).currentWidget()
            browser = current_tab.findChild(QTextBrowser)
            
            # If findChild fails (sometimes nested layouts complicate things), iterate children
            if not browser:
                 # Fallback
                 for child in current_tab.children():
                     if isinstance(child, QTextBrowser):
                         browser = child
                         break
            
            if browser:
                result.ok("Quick Start loaded", "Quick Start Content" in browser.toPlainText())
            else:
                result.ok("Quick Start loaded", False, "QTextBrowser not found")
            
            dialog.close()
            
            # Clean up sys.modules mocks handled by patch.dict? 
            # patch.dict restores original, but if they weren't there, it removes them.
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 3. HelpPopup
    # ---------------------------------------------------------
    print("\n[3. HelpPopup]")
    try:
        from GUI.help_popup import HelpPopup
        print("  ✅ Import Successful")
        
        popup = HelpPopup()
        result.ok("Instance Created", popup is not None)
        result.ok("_create_workflow_tab exists", hasattr(popup, '_create_workflow_tab'))
        result.ok("_create_faq_tab exists", hasattr(popup, '_create_faq_tab'))
        
        popup.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 4. HelpWidget
    # ---------------------------------------------------------
    print("\n[4. HelpWidget]")
    try:
        from GUI.help_widget import HelpWidget
        print("  ✅ Import Successful")
        
        widget = HelpWidget()
        result.ok("Instance Created", widget is not None)
        result.ok("_create_step_card exists", hasattr(widget, '_create_step_card'))
        result.ok("_create_faq_item exists", hasattr(widget, '_create_faq_item'))
        
        widget.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 5. TierPopup
    # ---------------------------------------------------------
    print("\n[5. TierPopup]")
    try:
        # Mock locales if needed, but it has try-catch fallback.
        # We can test fallback or mock it.
        # Let's mock it to be safe and consistent.
        with patch.dict(sys.modules, {'locales': MagicMock()}):
            sys.modules['locales'].t.side_effect = lambda key, default=None: default or key
            
            from GUI.tier_popup import TierPopup
            print("  ✅ Import Successful")
            
            popup = TierPopup()
            result.ok("Instance Created", popup is not None)
            
            # Check table presence (TierPopup has a QTableWidget)
            from PyQt6.QtWidgets import QTableWidget
            tables = popup.findChildren(QTableWidget)
            result.ok("Table exists", len(tables) > 0)
            if tables:
                result.ok("Table row count 5", tables[0].rowCount() == 5)
                
            popup.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))
    
    # ===========================================
    # 결과 요약
    # ===========================================
    print("\n" + "="*60)
    total = result.passed + result.failed
    pct = result.passed / total * 100 if total > 0 else 0
    print(f"📊 결과: {result.passed}/{total} ({pct:.0f}%)")
    
    if result.failed > 0:
        print("\n실패 목록:")
        for err in result.errors:
            print(f"  - {err}")
    print("="*60)
    
    return result

if __name__ == "__main__":
    result = run_batch3_tests()
    sys.exit(0 if result.failed == 0 else 1)
