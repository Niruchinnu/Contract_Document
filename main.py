from fastapi import FastAPI
from Document import router as document_router
from database import engine, Base
from Auth import router as auth_router
from Document.kafka_consumer import KafkaConsumerClient
from Document.kafka_admin import create_kafka_topic
from Document.kafka_producer import get_kafka_producer, stop_kafka_producer
import asyncio
from contextlib import asynccontextmanager
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ✅ Function to initialize models
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Drop tables (optional)
        await conn.run_sync(Base.metadata.create_all)  # Create tables

# Kafka consumer instance
consumer_client = KafkaConsumerClient(topic="document-processing")


def start_kafka_consumer():
    """Run Kafka consumer in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(consumer_client.consume_from_kafka())


@asynccontextmanager
async def lifespan(_):
    """Manage startup and shutdown of Kafka consumer."""
    create_kafka_topic()

    # ✅ Start Kafka Consumer in a separate thread
    consumer_thread = threading.Thread(target=start_kafka_consumer, daemon=True)
    consumer_thread.start()

    yield  # Let FastAPI run

    # ✅ Stop the Kafka Consumer safely on shutdown
    await consumer_client.stop_consumer()


app = FastAPI(lifespan=lifespan)

# ✅ Include routers
app.include_router(document_router.router, tags=["documents"])
app.include_router(auth_router.router, tags=["auth"])


@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI with Kafka!"}
