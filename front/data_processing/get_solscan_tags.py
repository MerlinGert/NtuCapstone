import requests
import json
import argparse

# ==========================================
# PLEASE PASTE YOUR SOLSCAN API KEY BELOW
# ==========================================
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3NzIxNzU2OTY2NDAsImVtYWlsIjoieGlhb2xpbndlbjk4QGdtYWlsLmNvbSIsImFjdGlvbiI6InRva2VuLWFwaSIsImFwaVZlcnNpb24iOiJ2MiIsImlhdCI6MTc3MjE3NTY5Nn0.51VF0iNAar-_0gdPQDuxIYKqIdN3YGkJ8nGAdRpsk6I" 
# ==========================================

def get_account_tags(address, api_key=None):
    endpoints = []
    
    # Pro API v2 (Likely for tags)
    endpoints = [f"https://pro-api.solscan.io/v2.0/account/detail?address={address}"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    # Use global API_KEY if not provided via argument
    if not api_key and API_KEY:
        api_key = API_KEY
    
    if api_key:
        headers["token"] = api_key
        print(f"Using API Key: {api_key[:4]}...{api_key[-4:]}")
    else:
        print("No API Key provided, trying Public API only (might be rate limited or blocked)")
        # If no key, prioritize public endpoint
        endpoints = [f"https://public-api.solscan.io/account/{address}"]

    for url in endpoints:
        print(f"\nQuerying: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("Response Data:")
                print(json.dumps(data, indent=2))
                
                # Try to extract tags specifically
                tags = data.get('tags') or data.get('data', {}).get('tags')
                if tags:
                    print(f"\n[FOUND TAGS]: {tags}")
                else:
                    print("\n[INFO] No explicit 'tags' field found in response.")
                    
                return # Stop after first success
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Solscan Account Tags")
    parser.add_argument("--key", help="Solscan Pro API Key", required=False)
    parser.add_argument("--address", help="Solana Address", default="A77HErqtfN1hLLpvZ9pCtu66FEtM8BveoaKbbMoZ4RiR")
    
    args = parser.parse_args()
            
    get_account_tags(args.address, args.key)
