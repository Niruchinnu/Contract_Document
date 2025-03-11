from confluent_kafka.admin import AdminClient, NewTopic

KAFKA_BROKER_URL = "localhost:9092"  # Replace with your Kafka broker URL
KAFKA_TOPIC = "document-processing"  # Replace with your topic name


def create_kafka_topic():
    """
    Create the Kafka topic if it doesn't already exist.
    """
    admin_client = AdminClient({"bootstrap.servers": KAFKA_BROKER_URL})

    # Check if the topic already exists
    existing_topics = admin_client.list_topics(timeout=5).topics
    if KAFKA_TOPIC in existing_topics:
        print(f"Topic '{KAFKA_TOPIC}' already exists.")
        return

    # Create the topic
    new_topic = NewTopic(KAFKA_TOPIC, num_partitions=1, replication_factor=1)

    # Send request to create topic
    future = admin_client.create_topics([new_topic])

    try:
        future[KAFKA_TOPIC].result()  # Wait for topic creation to complete
        print(f"Topic '{KAFKA_TOPIC}' created successfully.")
    except Exception as e:
        print(f"Failed to create topic '{KAFKA_TOPIC}': {e}")


# Run the function
create_kafka_topic()
