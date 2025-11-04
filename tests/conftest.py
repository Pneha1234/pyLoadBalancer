"""
Pytest configuration and fixtures.
"""
import pytest
import asyncio
from aiohttp import web


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_backend_server():
    """Create a mock backend server for testing."""
    app = web.Application()
    
    async def health_handler(request):
        return web.json_response({"status": "healthy"})
    
    async def echo_handler(request):
        data = await request.json() if request.content_type == "application/json" else {}
        return web.json_response({"echo": data})
    
    app.router.add_get("/health", health_handler)
    app.router.add_post("/echo", echo_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 0)
    await site.start()
    
    # Get the port
    port = site._server.sockets[0].getsockname()[1]
    
    yield f"http://localhost:{port}"
    
    await runner.cleanup()

