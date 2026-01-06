# test_locales.py
import sys
sys.path.insert(0, r'c:\매매전략')

from locales import t, set_language, get_lang_manager

# 한국어 테스트
print("=== 한국어 ===")
set_language('ko')
print(f"dashboard.exchange: {t('dashboard.exchange')}")
print(f"backtest.run: {t('backtest.run')}")
print(f"settings.language: {t('settings.language')}")

# 영어 테스트
print("\n=== English ===")
set_language('en')
print(f"dashboard.exchange: {t('dashboard.exchange')}")
print(f"backtest.run: {t('backtest.run')}")
print(f"settings.language: {t('settings.language')}")

print("\n✅ Locales test passed!")
