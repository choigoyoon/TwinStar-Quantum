#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_phase3_batch5.py - GUI Phase 3 Batch 5 Tests
Widgets:
1. LoginDialog (GUI/login_dialog.py)
2. RegisterDialog (GUI/register_dialog.py)
3. PaymentDialog (GUI/payment_dialog.py)
4. PCLicenseDialog (GUI/pc_license_dialog.py)
5. OnboardingDialog (GUI/onboarding_dialog.py)
6. TelegramSettingsWidget (GUI/telegram_settings_widget.py)
"""
import sys
import os
from pathlib import Path
import logging
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from PyQt6.QtWidgets import QApplication, QDialog, QWidget
from PyQt6.QtCore import Qt

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "GUI"))
os.chdir(PROJECT_ROOT)

logging.basicConfig(level=logging.WARNING)

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
        sys.stdout.flush()

def run_batch5_tests():
    print("\n" + "="*60)
    print("🧪 Phase 3 Batch 5 Tests (Auth & Settings)")
    print("="*60)
    sys.stdout.flush()
    
    result = TestResult()
    
    # ---------------------------------------------------------
    # 1. LoginDialog
    # ---------------------------------------------------------
    print("\n[1. LoginDialog]")
    try:
        # Mock requests usually used in login
        with patch('requests.post'), \
             patch('requests.get'):
             
            from GUI.login_dialog import LoginDialog
            print("  ✅ Import Successful")
            
            dialog = LoginDialog()
            result.ok("Instance Created", dialog is not None)
            
            # Check methods
            result.ok("_do_login exists", hasattr(dialog, '_do_login'))
            result.ok("_do_register exists", hasattr(dialog, '_do_register'))
            
            # Verify UI elements
            result.ok("Email input exists", hasattr(dialog, 'login_email'))
            
            dialog.close()
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        result.ok("Import/Init Failed", False, str(e))
    
    sys.stdout.flush()

    # ---------------------------------------------------------
    # 2. RegisterDialog
    # ---------------------------------------------------------
    print("\n[2. RegisterDialog]")
    try:
        from GUI.register_dialog import RegisterDialog
        print("  ✅ Import Successful")
        
        # Mock LicenseManager
        mock_lm = MagicMock()
        mock_lm.register.return_value = {'success': True}
        
        dialog = RegisterDialog(mock_lm)
        result.ok("Instance Created", dialog is not None)
        result.ok("_validate_email exists", hasattr(dialog, '_validate_email'))
        
        # Validation Logic Test
        valid = dialog._validate_email("test@example.com")
        invalid = dialog._validate_email("test-example.com")
        result.ok("Email Validation", valid and not invalid)
        
        dialog.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()

    # ---------------------------------------------------------
    # 3. PaymentDialog (GUI/payment_dialog.py)
    # ---------------------------------------------------------
    print("\n[3. PaymentDialog]")
    try:
        from GUI.payment_dialog import PaymentDialog
        print("  ✅ Import Successful")
        
        # PaymentDialog requires LicenseManager, not user dict
        mock_lm = MagicMock()
        mock_lm.get_tier.return_value = "FREE"
        mock_lm.get_days_left.return_value = 7
        mock_lm.fetch_prices.return_value = {'success': True, 'prices': {}}
        mock_lm.fetch_wallet.return_value = "WALLET_ADDR"
        
        with patch.object(PaymentDialog, '_load_data'): # Skip network
             
            dialog = PaymentDialog(mock_lm)
            result.ok("Instance Created", dialog is not None)
            result.ok("_on_submit exists", hasattr(dialog, '_on_submit'))
            
            dialog.close()
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()
    
    # ---------------------------------------------------------
    # 4. PCLicenseDialog
    # ---------------------------------------------------------
    print("\n[4. PCLicenseDialog]")
    try:
        # Mock requests and hardware ID
        with patch('requests.post') as mock_post, \
             patch('GUI.pc_license_dialog.get_hardware_id', return_value="TEST-HW-ID"):
            
            from GUI.pc_license_dialog import PCLicenseDialog
            print("  ✅ Import Successful")
            
            dialog = PCLicenseDialog()
            result.ok("Instance Created", dialog is not None)
            result.ok("on_login_click exists", hasattr(dialog, 'on_login_click'))
            result.ok("activate_pc exists", hasattr(dialog, 'activate_pc'))
            
            dialog.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()
    
    # ---------------------------------------------------------
    # 5. OnboardingDialog
    # ---------------------------------------------------------
    print("\n[5. OnboardingDialog]")
    try:
        from GUI.onboarding_dialog import OnboardingDialog
        print("  ✅ Import Successful")
        
        dialog = OnboardingDialog()
        result.ok("Instance Created", dialog is not None)
        result.ok("_next_step exists", hasattr(dialog, '_next_step'))
        
        # Check step navigation
        initial_step = dialog.current_step
        dialog._next_step()
        result.ok("Navigation Works", dialog.current_step == initial_step + 1)
        
        dialog.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()

    # ---------------------------------------------------------
    # 6. TelegramSettingsWidget
    # ---------------------------------------------------------
    print("\n[6. TelegramSettingsWidget]")
    try:
        # Mock TelegramNotifier import or class
        # If the file tries to import it, we must mock it in sys.modules or patch it
        
        mock_notifier_class = MagicMock()
        mock_notifier_instance = MagicMock()
        mock_notifier_instance.enabled = True
        mock_notifier_instance.bot_token = "123:TOKEN"
        mock_notifier_instance.chat_id = "12345"
        mock_notifier_class.return_value = mock_notifier_instance
        
        # We need to patch the module 'telegram_notifier' if it exists.
        # But looking at outline, it does conditional import.
        # Let's inject a mock module.
        
        mock_tg_module = MagicMock()
        mock_tg_module.TelegramNotifier = mock_notifier_class
        mock_tg_module.TELEGRAM_SETUP_GUIDE = "Guide"
        
        with patch.dict(sys.modules, {'telegram_notifier': mock_tg_module}):
            from GUI.telegram_settings_widget import TelegramSettingsWidget
            print("  ✅ Import Successful")
            
            widget = TelegramSettingsWidget()
            result.ok("Instance Created", widget is not None)
            result.ok("_load_settings exists", hasattr(widget, '_load_settings'))
            result.ok("_send_test exists", hasattr(widget, '_send_test'))
            
            widget.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()

    # ---------------------------------------------------------
    # 7. AuthDialog (GUI/login.py)
    # ---------------------------------------------------------
    print("\n[7. AuthDialog]")
    try:
        # Mock trc20_payment
        mock_trc = MagicMock()
        mock_trc.TRC20PaymentChecker = MagicMock()
        mock_trc.DEPOSIT_WALLET = "TEST_WALLET"
        
        with patch.dict(sys.modules, {'trc20_payment': mock_trc}):
            from GUI.login import AuthDialog
            print("  ✅ Import Successful")
            
            dialog = AuthDialog()
            result.ok("Instance Created", dialog is not None)
            result.ok("_create_login_page exists", hasattr(dialog, '_create_login_page'))
            result.ok("_create_register_page exists", hasattr(dialog, '_create_register_page'))
            
            dialog.close()
            
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
    result = run_batch5_tests()
    sys.exit(0 if result.failed == 0 else 1)
