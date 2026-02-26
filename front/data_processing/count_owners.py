import json
import argparse

def count_owners(json_path):
    print(f"Reading {json_path}...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            owners = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {json_path}")
        return

    contract_count = 0
    user_count = 0
    
    for owner in owners:
        if owner.get('label') == 'contract':
            contract_count += 1
        elif owner.get('label') == 'user':
            user_count += 1
            
    print("-" * 30)
    print(f"Total Unique Owners: {len(owners)}")
    print(f"Contract Owners: {contract_count}")
    print(f"User Owners:     {user_count}")
    print("-" * 30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count owners by type")
    parser.add_argument("--input", required=True, help="Path to owner_labels.json")
    args = parser.parse_args()
    
    count_owners(args.input)
