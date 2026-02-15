import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080/search")  # URL of the sear-xng container

# 1. Define the Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the connect to redis, rabbitmq here
    
    yield  # The application runs while this is suspended
    
    # Shutdown: Clean up resources

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