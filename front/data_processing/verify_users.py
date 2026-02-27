
import json
import os
from solders.pubkey import Pubkey

def verify_users(labels_path):
    print(f"Loading labels from {labels_path}...")
    try:
        with open(labels_path, 'r', encoding='utf-8') as f:
            labels = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {labels_path}")
        return

    print(f"Total entries: {len(labels)}")
    
    contract_count = 0
    user_count = 0
    
    reclassified_count = 0
    
    for item in labels:
        current_label = item.get('label')
        address = item.get('owner_address')
        
        if not address:
            continue
            
        try:
            pubkey = Pubkey.from_string(address)
            is_on_curve = pubkey.is_on_curve()
            
            # Logic:
            # - On curve: Likely User (Ed25519 keypair) or Program Executable (less common for holding tokens directly in this context)
            # - Off curve: PDA (Program Derived Address) -> DEFINITELY NOT A USER WALLET -> Contract/Pool/Vault
            
            if current_label == 'user':
                if not is_on_curve:
                    # It was labeled as user, but it's off curve -> Reclassify as contract/pda
                    item['label'] = 'contract'
                    item['details'] = 'PDA (Program Derived Address) - Detected by off-curve check'
                    reclassified_count += 1
            
            # Optional: Check if labeled contract is actually on curve?
            # Some contracts might use a keypair (on curve) as an authority, but usually 'contract' label came from previous rigorous checks.
            # We trust 'contract' label more if it came from known program IDs.
            
        except Exception as e:
            print(f"Error checking address {address}: {e}")
            
        if item['label'] == 'contract':
            contract_count += 1
        else:
            user_count += 1

    print(f"Verification complete.")
    print(f"Reclassified {reclassified_count} 'user' addresses to 'contract' (PDA detected).")
    print(f"Final Counts -> User: {user_count}, Contract: {contract_count}")
    
    if reclassified_count > 0:
        print(f"Saving updated labels to {labels_path}...")
        with open(labels_path, 'w', encoding='utf-8') as f:
            json.dump(labels, f, indent=2, ensure_ascii=False)
        print("Done.")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LABELS_FILE = os.path.join(BASE_DIR, "../public/processed/transfers/owner_labels.json")
    
    verify_users(LABELS_FILE)
