import asyncio
import json
import logging
import aio_pika
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from redis import asyncio as aioredis

from config import QUEUE_IN, QUEUE_OUT, REDIS_URL, RMQ_URL
from search_service import perform_search, perform_search_get

logger = logging.getLogger("uvicorn")

async def process_message(message: aio_pika.IncomingMessage, app: FastAPI, channel: aio_pika.Channel):
    async with message.process():
        logger.info(f"[*] Received message in Search Engine Service")
        data = json.loads(message.body)
        request_id = data['request_id']
        query = data['q']
        
        try:
            data_out = await perform_search(query)
            top_3 = data_out.get('results', [])[:3]
            formatted_results = [{"request_id": request_id, "url": item['url']} for item in top_3]

            requests_to_send = len(formatted_results)
            await app.state.redis.incrby(request_id, requests_to_send)
            
            logger.info(f"[*] Search Engine Service started sending {requests_to_send} requests: {request_id}")

            for res in formatted_results:
                await channel.default_exchange.publish(
                    aio_pika.Message(body=json.dumps(res).encode()),
                    routing_key=QUEUE_OUT
                )
            
            await app.state.redis.decr(request_id)
            logger.info(f"[x] Search Engine Service finished: {request_id}")

        except Exception as e:
            logger.error(f"Error processing message in Search Engine Service: {str(e)}")

async def run_consumer(app: FastAPI):
    logger.info("[*] Starting Search Engine Service consumer...")
    channel = await app.state.rabbitmq_connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue_in = await channel.declare_queue(QUEUE_IN)
    await channel.declare_queue(QUEUE_OUT)
    
    async with queue_in.iterator() as queue_iter:
        async for message in queue_iter:
            await process_message(message, app, channel)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    app.state.rabbitmq_connection = await aio_pika.connect_robust(RMQ_URL)
    task = asyncio.create_task(run_consumer(app))
    logger.info("[*] Search Engine service is running...")

    yield
    
    task.cancel()
    await app.state.redis.close()
    await app.state.rabbitmq_connection.close()

app = FastAPI(title="Search Engine Service", lifespan=lifespan)

class SearchRequest(BaseModel):
    q: str

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Sear xng search Service!"}

@app.post("/search")
async def search(request: SearchRequest):
    return await perform_search_get(request.q)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)