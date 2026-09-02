import redis
import os

if __name__ == "__main__":
    # Manual connectivity check, not a pytest test -- guarded for the same
    # reason as postgres_db_test.py (see its comment): the *_test.py
    # filename matches pytest's default discovery pattern.
    r = redis.Redis(host="localhost", port=6379, password=os.getenv("REDIS_PASSWORD", "reset123"), decode_responses=True)
    print(r.ping())