import os

# --- LOGIC CONFIG ---
QUEUE_IN = "query_queue"
QUEUE_OUT = "url_queue"

# Connection strings
REDIS_HOST = os.getenv("REDIS_HOST", "redis-state-store")
RMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq-broker")
REDIS_URL = f"redis://{REDIS_HOST}:6379"
RMQ_URL = f"amqp://admin:password123@{RMQ_HOST}:5672/"

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080/search")
