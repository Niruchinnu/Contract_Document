from fastapi import FastAPI
from Document import router as document_router
from database import engine, Base
from Auth import router as auth_router
from Document.kafka_consumer import KafkaConsumerClient
import asyncio
from Document.kafka_admin import create_kafka_topic
from contextlib import asynccontextmanager

# ✅ Function to initialize models
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Drop tables (optional)
        await conn.run_sync(Base.metadata.create_all)  # Create tables

# Kafka consumer instance
consumer_client = KafkaConsumerClient(topic="document-processing")


@asynccontextmanager
async def lifespan(_):
    """Manage startup and shutdown of Kafka consumer."""
    create_kafka_topic()  # Ensure Kafka topic exists

    # Start the Kafka consumer
    consumer_task = asyncio.create_task(consumer_client.consume_from_kafka())

    try:
        yield  # Keep the app running
    finally:
        consumer_task.cancel()
        try:
            await consumer_task  # Ensure task is properly canceled
        except asyncio.CancelledError:
            pass  # Expected behavior when canceling
        await consumer_client.stop_consumer()  # Stop Kafka client safely


# Initialize FastAPI with lifespan event
app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(document_router.router)
app.include_router(auth_router.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI with Kafka!"}