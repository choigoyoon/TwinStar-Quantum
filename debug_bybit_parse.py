
import json

def parse_balance(response, account_type):
    print(f"Testing {account_type} parsing...")
    try:
        balance = float(response['result']['list'][0]['coin'][0]['walletBalance'])
        print(f"Success! Balance: {balance}")
        return balance
    except Exception as e:
        print(f"Failed: {e}")
        return 0

# 1. Unified Structure Mock
unified_response = {
    "result": {
        "list": [
            {
                "coin": [
                    {"walletBalance": "123.45", "usdValue": "123.45"}
                ]
            }
        ]
    }
}

# 2. Standard/Contract Structure Mock (Checking if different)
# According to docs, V5 accountType=CONTRACT returns:
contract_response = {
    "result": {
        "list": [
            {
                "coin": [
                    {"walletBalance": "678.90"}
                ]
            }
        ]
    }
}

# 3. What if 'coin' list is empty? (Zero balance)
empty_response = {
    "result": {
        "list": [
            {
                "coin": []
            }
        ]
    }
}

print("--- UNIFIED ---")
parse_balance(unified_response, "UNIFIED")

print("\n--- CONTRACT ---")
parse_balance(contract_response, "CONTRACT")

print("\n--- EMPTY ---")
parse_balance(empty_response, "EMPTY")
