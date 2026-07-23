import redis
import os

r = redis.Redis(host="localhost", port=6379, password=os.getenv("REDIS_PASSWORD", "reset123"), decode_responses=True)

print(r.ping())