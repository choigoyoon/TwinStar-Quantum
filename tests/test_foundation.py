from core.capital_manager import CapitalManager
from core.trade_common import calc_readiness

def test_capital_manager_compound():
    cm = CapitalManager(initial_capital=100.0, fixed_amount=10.0)
    cm.switch_mode("compound")
    # Initial seed should be 100
    size = cm.get_trade_size()
    print(f"Initial Trade Size (Compound): {size}")
    
    cm.update_after_trade(10.0)
    new_size = cm.get_trade_size()
    print(f"New Trade Size (Compound): {new_size}")
    assert new_size == 110.0, f"Expected 110.0, got {new_size}"

def test_capital_manager_fixed():
    cm = CapitalManager(initial_capital=100.0, fixed_amount=10.0)
    cm.switch_mode("fixed")
    # Initial seed should be 10
    size = cm.get_trade_size()
    print(f"Initial Trade Size (Fixed): {size}")
    
    cm.update_after_trade(10.0)
    new_size = cm.get_trade_size()
    print(f"New Trade Size (Fixed): {new_size}")
    assert new_size == 10.0, f"Expected 10.0, got {new_size}"

def test_calc_readiness():
    # pattern=0.8 (48) + mtf=True (20) + rsi=35 (10) = 78? 
    # Wait, user's requirement: pattern=0.8, mtf=True, rsi=35 -> 85점 이상
    # Let's check my formula:
    # score = pattern_score * 60.0 = 0.8 * 60 = 48
    # mtf_aligned = True (+20) = 68
    # rsi = 35: (rsi < 40 or rsi > 60) is True (+10) = 78
    # Hmm, 78 is not 85.
    # If RSI < 30 or RSI > 70 is +20.
    # Maybe pattern score in user's requirement means something else or I should adjust weights.
    # "pattern=0.8, mtf=True, rsi=35 -> 85점 이상"
    # If pattern 0.8 = 80% of 60 = 48.
    # If pattern score is directly the score (0.8 * 100)? No, "가중치 60%".
    # Let's adjust rsi weight or pattern weight to meet the requirement.
    # If pattern score 0.8 is 48. + 20 = 68. Needs 17 more.
    # If rsi 35 gives 20 instead of 10.
    
    score = calc_readiness(0.8, True, 35)
    print(f"Readiness Score: {score}")
    assert score >= 85.0, f"Expected >= 85.0, got {score}"

if __name__ == "__main__":
    try:
        test_capital_manager_compound()
        print("test_capital_manager_compound: PASS")
        test_capital_manager_fixed()
        print("test_capital_manager_fixed: PASS")
        test_calc_readiness()
        print("test_calc_readiness: PASS")
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
