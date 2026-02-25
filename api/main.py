import asyncio
from contextlib import asynccontextmanager
import json
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
from redis import asyncio as  aioredis
import aio_pika

logger = logging.getLogger("uvicorn")

# --- LOGIC CONFIG ---
QUEUE_IN = "query_queue" # coming from user query input
QUEUE_OUT = "url_queue" # going to web scraping service

# Connection strings
redis_host = os.getenv("REDIS_HOST", "redis-state-store") # Use localhost as deafult if you are running rabbitmq and redis on your locally
rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq-broker")
redis_url = f"redis://{redis_host}:6379"
rmq_url = f"amqp://admin:password123@{rmq_host}:5672/"

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080/search")  # URL of the sear-xng container

async def process_message(message: aio_pika.IncomingMessage, app: FastAPI, channel: aio_pika.Channel):
    '''
        Format of message coming from query_queue:
        {
            "request_id": "unique_request_id",
            "q": "user search query"
        }
        Format of message going to url_queue:
        {
            "request_id": "unique_request_id",
            "url": "https://example.com"
        }
    '''
    async with message.process():
        logger.info(f"[*] Received message in Search Engine Service")
        data = json.loads(message.body)
        request_id = data['request_id']
        query = data['q']
        
        # 
        try:
            response = requests.post(SEARXNG_URL, params={"q": query, "format": "json"})
            response.raise_for_status()
            if response.status_code == 200:
                logger.info(f"Successfully received response from SearXNG for request_id: {request_id}")
                data_out = response.json()
            else:
                raise HTTPException(status_code=400, detail=f"Error from SearXNG: {response.status_code}")

        except requests.exceptions.ConnectionError:
            logger.error("Error: Could not connect to SearXNG. Is the Docker container running?")
        except requests.exceptions.JSONDecodeError:
            logger.error("Error: Received a non-JSON response. Check if API is enabled in settings.yml.")
        
        # format to get list of messages for next queue
        top_3 = data_out.get('results', [])[:3]
        formatted_results = [
            {"request_id": request_id, "url": item['url']} 
            for item in top_3
        ]


        # how many is being sent to the next stage
        requests_to_send = 3 # hardcoded as we pass only top 3 results to next stage
        await app.state.redis.incrby(request_id, requests_to_send)
        
        logger.info(f"[*] Search Engine Service started sending requests to next stage: {request_id}")


        i = 0
        while i < requests_to_send:
            await channel.default_exchange.publish(
                aio_pika.Message(body=json.dumps(formatted_results[i]).encode()),
                routing_key=QUEUE_OUT
            )
            i += 1
        
        await app.state.redis.decr(request_id)
        logger.info(f"[x] Search Engine Service finished: {request_id}")

async def run_consumer(app: FastAPI):
    logger.info("[*] Starting Search Engine Service consumer...")

    # Set up RabbitMQ channel
    
    channel = await app.state.rabbitmq_connection.channel()

    await channel.set_qos(prefetch_count=10)

    # declare in-queue and out-queue
    queue_in = await channel.declare_queue(QUEUE_IN)
    await channel.declare_queue(QUEUE_OUT)
    
    async with queue_in.iterator() as queue_iter:
        async for message in queue_iter:
            await process_message(message, app, channel)


# 1. Define the Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to Redis on custom port 
    logger.info("[*] Connecting to Redis...")
    app.state.redis = await aioredis.from_url(redis_url, decode_responses=True)
    app.state.rabbitmq_connection = await aio_pika.connect_robust(rmq_url)

    # Start the RabbitMQ consumer as a background task
    task = asyncio.create_task(run_consumer(app))
    logger.info("[*] Search Engine service is running...")


    yield  # The application runs while this is suspended
    
    # Shutdown: Clean up resources
    task.cancel()
    await app.state.redis.close()
    await app.state.rabbitmq_connection.close()

# 2. Initialize FastAPI with the lifespan handler
app = FastAPI(title="Crawl4AI Modern Service", lifespan=lifespan)

class SearchRequest(BaseModel):
    q: str # user query

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Sear xng search Service!"}

@app.post("/search")
async def search(request: SearchRequest):
    # Forward request to sear-xng container here
    try:
        response = requests.get(SEARXNG_URL, params={"q": request.q, "format": "json"})
        response.raise_for_status()
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=400, detail=f"Error from SearXNG: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to SearXNG. Is the Docker container running?")
    except requests.exceptions.JSONDecodeError:
        print("Error: Received a non-JSON response. Check if API is enabled in settings.yml.")
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)