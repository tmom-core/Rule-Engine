import asyncio
import websockets
import websockets.exceptions
import json
from typing import Callable, Awaitable, Union

'''
```
export APCA_API_KEY_ID=PKSUH6PMI2OZ6U3JMWTT6YKLHM
export APCA_API_SECRET_KEY=GvUT8fmiGQXHwC25empMJhe6o3L3pVLo6CjYT5LsAALa
export APCA_BASE_URL=https://paper-api.alpaca.markets
```
'''

class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self.connection = None

    async def connect(self, max_retries=5, base_delay=2.0, **kwargs):
        """Establishes connection to the WebSocket URL with exponential backoff retry."""
        connect_args = {
            "open_timeout": 20,
        }
        connect_args.update(kwargs)

        attempt = 0
        while attempt < max_retries:
            try:
                self.connection = await websockets.connect(self.url, **connect_args)
                print(f"Connected to {self.url}")
                return
            except websockets.exceptions.InvalidStatus as e:
                if e.response.status_code == 429:
                    attempt += 1
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"Rate limited (429) connecting to {self.url}. Retrying in {delay}s (Attempt {attempt}/{max_retries})...")
                    await asyncio.sleep(delay)
                else:
                    print(f"Failed to connect to {self.url}: {e}")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                     attempt += 1
                     delay = base_delay * (2 ** (attempt - 1))
                     print(f"Connection error to {self.url}: {e}. Retrying in {delay}s...")
                     await asyncio.sleep(delay)
                else:
                    print(f"Failed to connect to {self.url} after {max_retries} attempts: {e}")
                    raise

    async def send(self, data: Union[str, dict]):
        """Sends data to the websocket server."""
        if not self.connection:
            await self.connect()
        
        if isinstance(data, dict):
            message = json.dumps(data)
        else:
            message = str(data)

        try:
            await self.connection.send(message)
        except Exception as e:
            print(f"Error sending data to {self.url}: {e}")
            raise

    async def listen(self, callback: Callable[[str], Awaitable[None]]):
        """
        Listens for messages and calls the callback for each message.
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
