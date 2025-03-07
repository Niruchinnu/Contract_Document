from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

KAFKA_BROKER_URL = "localhost:9092"  # Replace with your Kafka broker URL
KAFKA_TOPIC = "document-processing"  # Replace with your topic name
KAFKA_ADMIN_CLIENT = "fastapi-admin-client"  # Unique client ID for the admin client

def create_kafka_topic():
    """
    Create the Kafka topic if it doesn't already exist.
    """
    admin_client = KafkaAdminClient(
        bootstrap_servers=KAFKA_BROKER_URL,
        client_id=KAFKA_ADMIN_CLIENT
    )

    try:
        # Check if the topic already exists
        if KAFKA_TOPIC not in admin_client.list_topics():
            # Create the topic
            admin_client.create_topics(
                new_topics=[
                    NewTopic(
                        name=KAFKA_TOPIC,
                        num_partitions=1,  # Number of partitions
                        replication_factor=1  # Replication factor
                    )
                ],
                validate_only=False  # Actually create the topic
            )
            print(f"Topic '{KAFKA_TOPIC}' created successfully.")
        else:
            print(f"Topic '{KAFKA_TOPIC}' already exists.")
    except TopicAlreadyExistsError:
        print(f"Topic '{KAFKA_TOPIC}' already exists.")
    except Exception as e:
        print(f"Failed to create topic '{KAFKA_TOPIC}': {e}")
    finally:
        admin_client.close()