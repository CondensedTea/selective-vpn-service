import aiosqlite
import asyncio
from app.database import DATABASE_FILE

data = [('twitter.com',)]


async def create_db(file: str) -> None:
    async with aiosqlite.connect(file) as db:
        await db.execute("create table Users (pubkey text, ip integer)")
        await db.execute("create table Domains (name text)")
        await db.commit()


async def insert_data() -> None:
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.executemany("insert into Domains (name) values (?)", data)
        await db.commit()


async def main(file):
    await create_db(file)
    await insert_data()


if __name__ == '__main__':
    asyncio.run(main(DATABASE_FILE))
