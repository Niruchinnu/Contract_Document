from aiokafka import AIOKafkaProducer
import json
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Kafka producer
_producer: AIOKafkaProducer | None = None

async def get_kafka_producer():
    """Returns a singleton Kafka producer."""
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            max_request_size=200000000
        )
        await _producer.start()
        logger.info("✅ Kafka producer started.")
    return _producer

async def stop_kafka_producer():
    """Gracefully stop the Kafka producer when FastAPI shuts down."""
    global _producer
    if _producer:
        await _producer.stop()
        logger.info("🛑 Kafka producer stopped.")
        _producer = None


async def send_to_kafka(topic: str, message: dict):
    """Send message to Kafka asynchronously."""
    global _producer
    if not _producer:
        await get_kafka_producer()  # Ensure producer is running
    try:
        await _producer.send_and_wait(topic, message)  # ✅ Fully async
        logger.info(f"✅ Sent to Kafka '{topic}'")
    except Exception as e:
        logger.error(f"❌ Failed to send message: {e}")
