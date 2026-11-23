import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    """Test the root endpoint returns app metadata."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "AnkiBook Backend API"
    assert "version" in data
    assert data["health"] == "/health"
    assert data["api_v1"] == "/api/v1"


@pytest.mark.asyncio
async def test_root_health_check(client: AsyncClient) -> None:
    """Test the root /health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["app"] == "AnkiBook Backend API"
    assert "database" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_api_v1_health_check(client: AsyncClient) -> None:
    """Test the versioned /api/v1/health endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["version"] == "0.1.0"
    assert "database" in data
