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


asyncio.run(main())
