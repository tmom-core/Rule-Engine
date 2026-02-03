import asyncio
import websockets
import json

async def test_user_socket():
    url = "wss://tmom-app-backend.onrender.com/ws/user-activity"
    print(f"Connecting to {url}...")
    try:
        async with websockets.connect(url) as websocket:
            print("Connected!")
            print("Waiting for messages...")
            while True:
                msg = await websocket.recv()
                print(f"Received: {msg}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_user_socket())
