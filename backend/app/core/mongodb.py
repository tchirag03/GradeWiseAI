"""
MongoDB async client using Motor.
Provides lifecycle helpers and DB handle access.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    """Open the Motor client and select the database."""
    global _client, _db
    try:
        _client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        _db = _client[settings.db_name]
        # Quick connectivity check
        await _client.admin.command("ping")
        print(f"[MongoDB] Connected -> {settings.mongo_uri}/{settings.db_name}")
    except Exception as exc:
        print(f"\n[MongoDB] [ERROR] Cannot connect to MongoDB at {settings.mongo_uri}")
        print("[MongoDB] The MongoDB service is currently stopped. To start it, run as Administrator:")
        print("         net start MongoDB\n")
        raise exc


async def close_db() -> None:
    """Gracefully shut down the Motor client."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        print("[MongoDB] Connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """Return the active database handle (call after connect_db)."""
    if _db is None:
        raise RuntimeError("Database not initialised — call connect_db() first.")
    return _db
