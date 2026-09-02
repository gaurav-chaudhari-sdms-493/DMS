import asyncio
import asyncpg


async def main():
    conn = await asyncpg.connect(
        user="docsearch",
        password="reset123",
        database="docsearch",
        host="localhost",
        port=5432
    )

    version = await conn.fetchval("SELECT version();")
    print(version)

    await conn.close()


if __name__ == "__main__":
    # Manual connectivity check, not a pytest test -- but its filename
    # matches pytest's default `*_test.py` discovery pattern, so without
    # this guard `pytest -q` (no path args) tried to import this module
    # and immediately attempted a real localhost:5432 connection at
    # collection time, failing the whole run with a connection error
    # before any real test executed.
    asyncio.run(main())
