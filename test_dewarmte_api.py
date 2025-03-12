import pytest_asyncio

@pytest_asyncio.fixture
async def session() -> AsyncGenerator[ClientSession, None]:
    """Create and yield an aiohttp ClientSession."""
    async with aiohttp.ClientSession() as session:
        yield session

@pytest_asyncio.fixture
async def api(session: AsyncGenerator[ClientSession, None]) -> DeWarmteApiClient:
    """Create and yield a DeWarmte API client."""
    # ... rest of the code ... 