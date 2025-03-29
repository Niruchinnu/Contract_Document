from fastapi import FastAPI
from Document import router as document_router
from Document.kafka_producer import stop_kafka_producer, get_kafka_producer
from database import engine, Base
from Auth import router as auth_router, Roles_router as roles_router
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
import logging
import models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ✅ Function to initialize models
async def init_models():
    """Initialize database models (drop and create tables)."""
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)  # Create tables
        logger.info("Database tables initialized.")


@asynccontextmanager
async def lifespan(apps: FastAPI):
    """Manage startup and shutdown of Kafka producer, consumer, and other resources."""

    # ✅ Ensure Kafka topic exists
    try:
        logger.info("Kafka topic 'document-processing' is ready.")
    except Exception as e:
        logger.error(f"Failed to create Kafka topic: {e}")
        raise

    # ✅ Initialize database models
    await init_models()
    # ✅ Start Kafka Producer (so it runs throughout the app lifecycle)
    await get_kafka_producer()
    logger.info("Kafka producer started.")
    try:
        yield  # ✅ FastAPI keeps running

    finally:
        await stop_kafka_producer()
        logger.info("Kafka producer stopped.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(document_router.router, tags=["documents"])
app.include_router(auth_router.router, tags=["auth"])
#app.include_router(roles_router.router, tags=["roles"])


@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI with Kafka!"}
