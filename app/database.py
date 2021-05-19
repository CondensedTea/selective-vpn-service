import os
from sqlite3 import IntegrityError
from typing import List

import aiosqlite

from app.exceptions import DomainExsists, PublicKeyExsists


async def add_user(pubkey: str, ip: int) -> str:
    async with aiosqlite.connect(os.environ['DB_FILE']) as db:
        try:
            await db.execute(
                'insert into Users (pubkey, ip) values (?, ?)', (pubkey, ip)
            )
            await db.commit()
        except IntegrityError as e:
            raise PublicKeyExsists from e
        else:
            return 'created'


async def add_domain(name: str) -> str:
    async with aiosqlite.connect(os.environ['DB_FILE']) as db:
        try:
            await db.execute('insert into Domains (name) values (?)', (name,))
            await db.commit()
        except IntegrityError as e:
            raise DomainExsists from e
        else:
            return 'created'


async def delete_domain(name: str) -> str:
    async with aiosqlite.connect(os.environ['DB_FILE']) as db:
        await db.execute('delete from Domains where name = ?', (name,))
        await db.commit()
        return 'deleted'


async def get_all_domains() -> List[str]:
    domains = []
    async with aiosqlite.connect(os.environ['DB_FILE']) as db:
        async with db.execute('select name from Domains') as cursor:
            rows = await cursor.fetchall()
    for (domain,) in rows:
        domains.append(domain)
    return domains


async def get_all_ips() -> List[int]:
    ips = []
    async with aiosqlite.connect(os.environ['DB_FILE']) as db:
        async with db.execute('select ip from Users') as cursor:
            rows = await cursor.fetchall()
    for (ip,) in rows:
        ips.append(int(ip))
    return ips
