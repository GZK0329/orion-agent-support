import os
import tempfile

_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="test_chat_")
os.close(_fd)

os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["ADMIN_PASSWORD"] = "test"
os.environ["DEEPSEEK_API_KEY"] = "test-dummy-key"
os.environ["EMBEDDING_API_KEY"] = "test-dummy-key"

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import async_engine, engine
from app.models.db_models import Base
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    Base.metadata.create_all(bind=engine)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await async_engine.dispose()
    engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient):
    resp = await client.post("/auth/login", json={"password": "test"})
    return {"X-Admin-Token": resp.json()["token"]}
