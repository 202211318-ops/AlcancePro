from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from .config import settings
from .models import DOCUMENT_MODELS

client: AsyncIOMotorClient | None = None


async def init_db() -> None:
    global client
    client = AsyncIOMotorClient(settings.mongodb_uri)
    await init_beanie(
        database=client[settings.mongodb_db],
        document_models=DOCUMENT_MODELS,
    )


async def close_db() -> None:
    global client
    if client is not None:
        client.close()
        client = None
