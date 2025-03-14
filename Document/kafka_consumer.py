import asyncio
import threading
from aiokafka import AIOKafkaConsumer
import json
import base64
from database import get_db
from .crud import get_latest_revision, insert_revision, compute_json_diff
from .extract_text import extract_text, process_text_with_deepseek
import logging
import io
from fastapi import UploadFile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KafkaConsumerClient:
    def __init__(self, topic: str, bootstrap_servers="localhost:9092", group_id="document-processor-group"):
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = None
        self._stop_requested = False

    async def consume_from_kafka(self):
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="earliest",
        )
        await self.consumer.start()
        logger.info(f"Consumer started for topic: {self.topic}")

        try:
            async for msg in self.consumer:
                print(f"[Kafka Consumer] Running on thread: {threading.current_thread().name}")
                logger.info(f"Received Kafka message: {msg.value}")
                asyncio.create_task(self.process_message(msg))
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            await self.stop_consumer()

    @staticmethod
    async def process_message(msg):
        """Handles message processing for multiple files."""
        try:
            data = json.loads(msg.value.decode("utf-8"))
            user_id = data["user_id"]
            files = data["files"]  # Expecting multiple files as a list

            for file_data in files:
                filename = file_data["filename"]
                file_content_base64 = file_data["file_content"]
                file_content = base64.b64decode(file_content_base64)
                file_like = io.BytesIO(file_content)
                upload_file = UploadFile(filename=filename, file=file_like)

                logger.info(f"Processing File: {filename}")

                text = await extract_text(upload_file)
                key_value_pairs = await process_text_with_deepseek(text)

                async for db in get_db():
                    latest_revision = await get_latest_revision(db, filename)
                    diff_data = compute_json_diff(latest_revision.data,
                                                  key_value_pairs) if latest_revision else {}
                    new_revision = latest_revision.revision + 1 if latest_revision else 1

                    await insert_revision(db, filename, new_revision, key_value_pairs, diff_data, user_id)

                    logger.info(f"File '{filename}' processed and saved as Revision {new_revision}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def stop_consumer(self):
        """Gracefully stop the Kafka consumer."""
        if self.consumer:
            self._stop_requested = True
            await self.consumer.stop()
            logger.info("Kafka consumer stopped successfully.")
