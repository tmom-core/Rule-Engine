import asyncio
import websockets
import sys

async def test_connect(url):
    print(f"Testing connection to {url}...")
    try:
        async with asyncio.timeout(5):
            async with websockets.connect(url) as ws:
                print(f"SUCCESS: Connected to {url}")
    except Exception as e:
        print(f"FAILURE: Could not connect to {url}. Error: {e}")

async def main():
    urls = [
        "wss://tmom-app-backend.onrender.com/ws/market-state",
        "wss://tmom-app-backend.onrender.com/ws/user-activity",
        "wss://tmom-app-backend.onrender.com/ws/engine-output"
    ]
    await asyncio.gather(*(test_connect(url) for url in urls))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
