import asyncio
import websockets
from typing import Callable, Awaitable

'''
```
export APCA_API_KEY_ID=PKSUH6PMI2OZ6U3JMWTT6YKLHM
export APCA_API_SECRET_KEY=GvUT8fmiGQXHwC25empMJhe6o3L3pVLo6CjYT5LsAALa
export APCA_BASE_URL=https://paper-api.alpaca.markets
```
'''

class WebSocketIngestion:
    def __init__(self, url: str):
        self.url = url
        self.connection = None

    async def connect(self, **kwargs):
        """Establishes connection to the WebSocket URL."""
        try:
            # increased default timeout and disabled ping_interval by default if not provided
            # as some servers (like Render) can be finicky or slow.
            connect_args = {
                "open_timeout": 20,
                # "ping_interval": None  # Uncomment if keepalive pings cause issues
            }
            connect_args.update(kwargs)
            
            self.connection = await websockets.connect(self.url, **connect_args)
            print(f"Connected to {self.url}")
        except Exception as e:
            print(f"Failed to connect to {self.url}: {e}")
            raise

    async def listen(self, callback: Callable[[str], Awaitable[None]]):
        """
        Listens for messages and calls the callback for each message.
        
        Args:
            callback: An async function that takes a string message as input.
        """
        if not self.connection:
            await self.connect()
        
        try:
            async for message in self.connection:
                await callback(message)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
        except Exception as e:
            print(f"Error while listening: {e}")
        finally:
            if self.connection:
                await self.connection.close()
