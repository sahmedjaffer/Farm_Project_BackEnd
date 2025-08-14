import redis.asyncio as redis
import os
from dotenv import load_dotenv

load_dotenv()

_redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    username=os.getenv("REDIS_USER"),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

def get_redis_client():

    return _redis_client
