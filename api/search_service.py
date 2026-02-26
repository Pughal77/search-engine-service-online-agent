import requests
import logging
from fastapi import HTTPException
from config import SEARXNG_URL

logger = logging.getLogger("uvicorn")

async def perform_search(query: str):
    try:
        response = requests.post(SEARXNG_URL, params={"q": query, "format": "json"})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error("Error: Could not connect to SearXNG. Is the Docker container running?")
        raise HTTPException(status_code=503, detail="Search engine unavailable")
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")

async def perform_search_get(query: str):
    try:
        response = requests.get(SEARXNG_URL, params={"q": query, "format": "json"})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error during GET search: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")
