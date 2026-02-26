import json
import argparse
import random

def read_balance_sample(file_path, num_samples=3):
    print(f"Reading {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON. The file might be corrupted or too large.")
        return

    total_owners = len(data)
    print(f"Successfully loaded. Total owners: {total_owners}")
    
    # Sort owners by length of history of their first token (usually ACT)
    print("Sorting owners by history length...")
    
    owner_stats = []
    for owner, tokens in data.items():
        # Sum history length across all tokens (usually just 1)
        total_history = sum(len(t.get('history', [])) for t in tokens.values())
        owner_stats.append((owner, total_history))
        
    # Sort descending
    owner_stats.sort(key=lambda x: x[1], reverse=True)
    
    top_n = min(num_samples, len(owner_stats))
    samples = [x[0] for x in owner_stats[:top_n]]
        
    print(f"\nDisplaying top {top_n} owners with longest history:\n")
    
    for owner in samples:
        print(f"Owner: {owner}")
        tokens = data[owner]
        for symbol, details in tokens.items():
            balance = details.get('balance', 0)
            history = details.get('history', [])
            print(f"  Token: {symbol}")
            print(f"  Final Balance: {balance}")
            print(f"  History Count: {len(history)}")
            
            # Show first 3 and last 3 history items
            if history:
                print("  History Preview:")
                display_items = history[:3]
                if len(history) > 6:
                    display_items.extend(history[-3:])
                elif len(history) > 3:
                    display_items = history # show all if small
                    
                for item in display_items:
                    time = item.get('time', 'N/A')
                    change = item.get('change', 0)
                    context = item.get('context', '')
                    reason = item.get('reason', '')
                    print(f"    [{time}] {change:+.4f} | {context} | {reason}")
        print("-" * 40)
    else:
        print("No owner data found in the file.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read and sample owner balance history")
    parser.add_argument("--input", required=True, help="Path to owner_balance_history.json")
    args = parser.parse_args()
    
    read_balance_sample(args.input)
