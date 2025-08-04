import redis.asyncio as redis
import os
from dotenv import load_dotenv

# Load .env before using os.getenv
load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "your-cloud-host")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))  # default to 6379 if missing
REDIS_USER = os.getenv("REDIS_USER", "default")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "your-password")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    username=REDIS_USER,
    password=REDIS_PASSWORD,
    decode_responses=True
)