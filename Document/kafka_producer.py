from kafka import KafkaProducer
import json
import asyncio

def get_kafka_producer():
    return KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

async def send_to_kafka(topic, message):
    producer = get_kafka_producer()
    future = producer.send(topic, value=message)
    await asyncio.get_event_loop().run_in_executor(None, future.get)
    producer.flush()
    producer.close()