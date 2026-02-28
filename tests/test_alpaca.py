import sys
import os
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from broker.account_providers import AlpacaAccountProvider
from broker.account_validation import validate_account_for_playbook

# Force load .env from the root directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

def test_alpaca_provider():
    print("--- 1. Testing Environment Variables ---")
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("SECRET_KEY")
    print(f"API_KEY Loaded: {'Yes' if api_key else 'No'} (Ends with ...{api_key[-4:] if api_key else 'N/A'})")
    print(f"SECRET_KEY Loaded: {'Yes' if api_secret else 'No'}")
    
    if not api_key or not api_secret:
        print("ERROR: API keys not loaded. Please check your .env file.")
        return

    print("\n--- 2. Connecting to Alpaca (Paper) ---")
    try:
        provider = AlpacaAccountProvider(paper=True)
    except Exception as e:
        print(f"Failed to initialize Alpaca provider: {e}")
        return

    print("\n--- 3. Fetching Full Account Snapshot ---")
    try:
        snapshot = provider.get_snapshot()
        print("\nRaw Snapshot Dictionary output:")
        print(json.dumps(snapshot, indent=2, default=str)) # Use default=str for decimals/datetime tracking
    except Exception as e:
        print(f"Error fetching snapshot: {e}")
        return

    print("\n--- 4. Running Validation Engine Against Snapshot ---")
    # This runs the exact logic killing the live_engine
    conflicts = validate_account_for_playbook(snapshot)
    
    if conflicts:
        print("ACCOUNT CONFLICTS DETECTED:")
        for conflict in conflicts:
            print(f" - {conflict}")
    else:
        print("SUCCESS! No account conflicts detected. Ready to trade.")

if __name__ == "__main__":
    test_alpaca_provider()
