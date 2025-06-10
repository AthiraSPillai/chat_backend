import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from config import settings

@pytest.mark.asyncio
async def test_read_main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": settings.APP_VERSION, "environment": settings.ENVIRONMENT}

