"""
Parameter Range Static Validation Script

Purpose:
1. Check if DEFAULT_PARAMS values are included in all INDICATOR_RANGE_*
2. Verify combination counts match targets
3. Validate range reasonableness

Usage: python tools/validate_param_ranges.py
"""

import sys
import os

# Add project root path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.parameters import DEFAULT_PARAMS
from core.optimizer import INDICATOR_RANGE_QUICK, INDICATOR_RANGE_STANDARD, INDICATOR_RANGE_DEEP


def validate_default_params_inclusion():
    """Validate if DEFAULT_PARAMS values are included in all ranges"""
    print("=" * 80)
    print("1. DEFAULT_PARAMS Inclusion Validation")
    print("=" * 80)

    # Core parameters to validate
    target_params = {
        'atr_mult': DEFAULT_PARAMS['atr_mult'],
        'rsi_period': DEFAULT_PARAMS['rsi_period'],
        'entry_validity_hours': DEFAULT_PARAMS['entry_validity_hours']
    }

    all_passed = True

    for mode_name, range_dict in [
        ('Quick', INDICATOR_RANGE_QUICK),
        ('Standard', INDICATOR_RANGE_STANDARD),
        ('Deep', INDICATOR_RANGE_DEEP)
    ]:
        print(f"\n[{mode_name} Mode]")
        for param_name, default_value in target_params.items():
            if param_name in range_dict:
                values = range_dict[param_name]
                is_included = default_value in values
                status = "[PASS]" if is_included else "[FAIL]"
                print(f"  {param_name}: {default_value} in {values} -> {status}")
                if not is_included:
                    all_passed = False
            else:
                print(f"  {param_name}: Not defined in range -> [SKIP]")

    return all_passed


def validate_combination_count():
    """Validate if combination counts match targets"""
    print("\n" + "=" * 80)
    print("2. Combination Count Validation")
    print("=" * 80)

    # Target combination counts
    targets = {
        'Quick': 4,
        'Standard': 36,
        'Deep': 252
    }

    all_passed = True

    for mode_name, range_dict in [
        ('Quick', INDICATOR_RANGE_QUICK),
        ('Standard', INDICATOR_RANGE_STANDARD),
        ('Deep', INDICATOR_RANGE_DEEP)
    ]:
        print(f"\n[{mode_name} Mode]")

        # Calculate core parameter combination count
        atr_mult_count = len(range_dict.get('atr_mult', [1]))
        rsi_period_count = len(range_dict.get('rsi_period', [1]))
        entry_validity_hours_count = len(range_dict.get('entry_validity_hours', [1]))

        actual_count = atr_mult_count * rsi_period_count * entry_validity_hours_count
        target_count = targets[mode_name]

        print(f"  atr_mult: {atr_mult_count} values")
        print(f"  rsi_period: {rsi_period_count} values")
        print(f"  entry_validity_hours: {entry_validity_hours_count} values")
        print(f"  Core combinations: {atr_mult_count} x {rsi_period_count} x {entry_validity_hours_count} = {actual_count}")

        is_match = actual_count == target_count
        status = "[PASS]" if is_match else "[FAIL]"
        print(f"  Target count: {target_count} -> {status}")

        if not is_match:
            all_passed = False

    return all_passed


def validate_range_reasonableness():
    """Validate range reasonableness"""
    print("\n" + "=" * 80)
    print("3. Range Reasonableness Validation")
    print("=" * 80)

    # Reasonable ranges (based on technical analysis conventions)
    reasonable_ranges = {
        'atr_mult': (0.5, 5.0),          # ATR multiplier: too small is meaningless, too large is excessive stop loss
        'rsi_period': (5, 50),            # RSI period: 5-50 is typical (too short = noise, too long = lag)
        'entry_validity_hours': (1, 168)  # Entry validity: 1h - 1week (for 15min candles)
    }

    all_passed = True

    for mode_name, range_dict in [
        ('Quick', INDICATOR_RANGE_QUICK),
        ('Standard', INDICATOR_RANGE_STANDARD),
        ('Deep', INDICATOR_RANGE_DEEP)
    ]:
        print(f"\n[{mode_name} Mode]")
        for param_name, (min_reasonable, max_reasonable) in reasonable_ranges.items():
            if param_name in range_dict:
                values = range_dict[param_name]
                min_val = min(values)
                max_val = max(values)

                is_reasonable = (min_val >= min_reasonable and max_val <= max_reasonable)
                status = "[PASS]" if is_reasonable else "[WARNING]"

                print(f"  {param_name}: [{min_val}, {max_val}] (recommended: [{min_reasonable}, {max_reasonable}]) -> {status}")

                if not is_reasonable:
                    all_passed = False

    return all_passed


def main():
    """Main validation function"""
    print("\n")
    print("=" * 80)
    print(" " * 20 + "Parameter Range Static Validation")
    print("=" * 80)

    # 1. DEFAULT_PARAMS inclusion
    check1 = validate_default_params_inclusion()

    # 2. Combination count
    check2 = validate_combination_count()

    # 3. Range reasonableness
    check3 = validate_range_reasonableness()

    # Final result
    print("\n" + "=" * 80)
    print("Final Validation Result")
    print("=" * 80)
    print(f"1. DEFAULT_PARAMS Inclusion: {'[PASS]' if check1 else '[FAIL]'}")
    print(f"2. Combination Count Match: {'[PASS]' if check2 else '[FAIL]'}")
    print(f"3. Range Reasonableness: {'[PASS]' if check3 else '[WARNING]'}")

    overall_pass = check1 and check2
    print(f"\n{'[SUCCESS] All validations passed!' if overall_pass else '[FAIL] Validation failed - range adjustment needed'}")
    print("=" * 80)

    return 0 if overall_pass else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
