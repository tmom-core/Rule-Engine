import asyncio
import sys
import json
import pandas as pd
from llm_layer.data_ingestion import WebSocketIngestion

async def test_client(url):
    print(f"Client: Connecting to {url}...")
    client = WebSocketIngestion(url)
    
    received_data = []
    
    async def msg_handler(msg):
        try:
            data = json.loads(msg)
            received_data.append(data)
        except json.JSONDecodeError:
            print(f"Client: Received non-JSON message: {msg[:100]}...")
        
    # Run listen for a short duration or until interrupted
    try:
        # Listen for 30 seconds
        print("Client: Listening for 30 seconds to capture data...")
        await asyncio.wait_for(client.listen(msg_handler), timeout=30)
    except asyncio.TimeoutError:
        print("Client: Finished capturing data (30s)")
    except KeyboardInterrupt:
        print("Client: Interrupted by user")
    except Exception as e:
        print(f"Client: Error: {e}")
        # If we have some data, we can still show it
        
    if received_data:
        print(f"\nVERIFICATION SUCCESS: Received {len(received_data)} messages.")
        try:
            df = pd.DataFrame(received_data)
            print("\n--- Data Preview (Head) ---")
            print(df.head())
            print("\n--- Data Info ---")
            print(df.info())
            
            # Optional: save to CSV for better inspection if needed
            df.to_csv("market_data.csv", index=False)
            print("\nSaved to market_data.csv")
            return True
        except Exception as e:
            print(f"Error creating DataFrame: {e}")
            return False
    else:
        print("VERIFICATION FAILED: No messages received.")
        return False

if __name__ == "__main__":
    # Default to Market State stream
    market_url = "wss://tmom-app-backend.onrender.com/ws/market-state"
    # wss://tmom-app-backend.onrender.com/ws/user-activity
    
    if len(sys.argv) < 2:
        print(f"No URL provided. Using default mock URL: {market_url}")
        url = market_url
    else:
        url = sys.argv[1]
    
    try:
        success = asyncio.run(test_client(url))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        pass
