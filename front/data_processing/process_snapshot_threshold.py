import json
import argparse
import sys
import os

def process_snapshot(input_path, output_path, threshold_percentage):
    print(f"Processing {input_path} with threshold {threshold_percentage}%...")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {input_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {input_path}")
        return

    if 'balances' not in data or 'users' not in data['balances']:
        print("Error: Invalid snapshot format. 'balances.users' not found.")
        return

    users = data['balances']['users']
    contracts = data['balances'].get('contracts', {})
    exchanges = data['balances'].get('exchanges', {})
    
    # Calculate total user balance
    total_user_balance = sum(users.values())
    print(f"Total user balance: {total_user_balance}")

    # Sort users by balance descending
    sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)
    
    accumulated_balance = 0
    target_balance = total_user_balance * (threshold_percentage / 100.0)
    
    processed_users = {}
    others_balance = 0
    included_count = 0
    
    threshold_met = False
    
    for address, balance in sorted_users:
        if not threshold_met:
            processed_users[address] = balance
            accumulated_balance += balance
            included_count += 1
            if accumulated_balance >= target_balance:
                threshold_met = True
        else:
            others_balance += balance

    if others_balance > 0:
        processed_users["Others"] = others_balance

    # Calculate statistics
    total_contract_balance = sum(contracts.values())
    total_exchange_balance = sum(exchanges.values())
    total_supply = total_user_balance + total_contract_balance + total_exchange_balance
    
    contract_count = len(contracts)
    exchange_count = len(exchanges)
    user_count = len(users)
    processed_user_count = included_count + (1 if others_balance > 0 else 0)

    stats = {
        "threshold_percentage": threshold_percentage,
        "total_supply": total_supply,
        "users": {
            "count": user_count,
            "processed_count": processed_user_count,
            "total_balance": total_user_balance,
            "top_users_balance": accumulated_balance,
            "top_users_percentage": (accumulated_balance / total_user_balance * 100) if total_user_balance > 0 else 0,
            "others_balance": others_balance,
            "others_percentage": (others_balance / total_user_balance * 100) if total_user_balance > 0 else 0,
            "percentage": (total_user_balance / total_supply * 100) if total_supply > 0 else 0
        },
        "contracts": {
            "count": contract_count,
            "total_balance": total_contract_balance,
            "percentage": (total_contract_balance / total_supply * 100) if total_supply > 0 else 0
        },
        "exchanges": {
            "count": exchange_count,
            "total_balance": total_exchange_balance,
            "percentage": (total_exchange_balance / total_supply * 100) if total_supply > 0 else 0
        }
    }

    print(f"Top {included_count} users hold {accumulated_balance} ({accumulated_balance/total_user_balance*100:.2f}%)")
    print(f"Grouped {len(users) - included_count} users into 'Others' with balance {others_balance}")
    print(f"Stats: Total Supply: {total_supply}, Users: {user_count} ({total_user_balance}), Contracts: {contract_count} ({total_contract_balance}), Exchanges: {exchange_count} ({total_exchange_balance})")

    # Construct new data
    new_data = {
        "time": data.get("time", ""),
        "statistics": stats,
        "balances": {
            "users": processed_users,
            "contracts": contracts,
            "exchanges": exchanges
        }
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2)
        print(f"Successfully saved processed snapshot to {output_path}")
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process snapshot to group small user balances.")
    parser.add_argument("--input", default="/Users/xiaolin/Projects/CryptoVis/code/front/public/processed/transfers/latest_balance_snapshot.json", help="Input snapshot JSON path")
    parser.add_argument("--output", default="/Users/xiaolin/Projects/CryptoVis/code/front/public/processed/transfers/processed_latest_snapshot.json", help="Output snapshot JSON path")
    parser.add_argument("--threshold", type=float, default=90.0, help="Threshold percentage (0-100) to keep individual users")

    args = parser.parse_args()
    
    process_snapshot(args.input, args.output, args.threshold)
