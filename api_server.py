import os
import asyncio
import json
from aiohttp import web
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

async def handle_health(request):
    """Simple health check endpoint."""
    return web.json_response({"status": "healthy", "service": "rule-engine-api"})

async def patch_context_to_db(request):
    """
    Accepts a parsed JSON ContextSkeleton from the rule engine
    and PATCHes it to the Supabase backend.
    """
    try:
        data = await request.json()
        context_skeleton = data.get("context")
        
        if not context_skeleton:
            return web.json_response({"error": "Missing 'context' in payload"}, status=400)
            
        # Send PATCH request to Supabase/Backend to save the context skeleton
        patch_url = "https://tmom-app-backend.onrender.com/playbooks/e03501db-630b-4a02-a818-99a5e31d48f4"
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            try:
                # Based on the curl, make a PATCH using aiohttp with the context dictionary
                async with session.patch(
                    patch_url,
                    json={"context": context_skeleton},
                    headers={"accept": "application/json"}
                ) as patch_resp:
                    if patch_resp.status in (200, 201, 204):
                        print(" [API] Successfully patched rule text to database.")
                    else:
                        print(f" [API WARNING] Failed to patch context. Status: {patch_resp.status}")
                        response_text = await patch_resp.text()
                        print(f" [API WARNING] Response: {response_text}")
            except Exception as req_error:
                print(f" [API ERROR] Could not reach backend: {req_error}")

        # Return a simple success message
        response_data = {
            "status": "success",
            "message": "Context Skeleton successfully synced to Database."
        }
        
        return web.json_response(response_data)
        
    except Exception as decode_err:
        if type(decode_err).__name__ == "JSONDecodeError":
            return web.json_response({"error": "Invalid JSON format"}, status=400)
        else:
            raise decode_err
    except Exception as e:
        print(f" [API ERROR] Failed to process context sync: {e}")
        return web.json_response({"error": str(e)}, status=500)


def setup_routes(app: web.Application):
    """Registers all REST API endpoints."""
    # System routes
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    
    # Rule management routes
    app.router.add_post('/api/rules/context', patch_context_to_db)

async def start_api_server():
    """Initializes and runs the web server."""
    app = web.Application()
    
    # Configure middleware (CORS, error handling, etc. can go here)
    
    # Register routes
    setup_routes(app)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Use standard 8081 or process env port (different from main.py 8080)
    port = int(os.getenv("PORT", 8081))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    await site.start()
    print(f" [API SERVER] Running on http://localhost:{port}")
    print(f" [API SERVER] Health check: http://localhost:{port}/health")
    print(f" [API SERVER] Context endpoint: POST http://localhost:{port}/api/rules/context")
    
    # Keep the server running indefinitely
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    print("Starting Standalone API Server...")
    try:
        asyncio.run(start_api_server())
    except KeyboardInterrupt:
        print("\nAPI Server stopped.")
