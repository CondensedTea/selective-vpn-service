from pathlib import Path

import aiosqlite
import fakeredis.aioredis
import pytest
from aiodnsresolver import TYPES, Resolver
from fakeredis import FakeServer
from fastapi.testclient import TestClient

from app.app import app, get_redis

server = FakeServer()


async def redis():
    r = await fakeredis.aioredis.create_redis_pool(server=server)
    return r


app.dependency_overrides[get_redis] = redis


@pytest.mark.asyncio
@pytest.fixture(name='fake_redis')
async def fixture_fake_redis():
    r = await redis()
    yield r
    r.close()
    await r.wait_closed()


@pytest.mark.asyncio
@pytest.fixture(autouse=True, name='tmp_database_tables')
async def fixture_tmp_database(
    tmp_path,
    monkeypatch,
):
    db_path = str(Path(tmp_path / 'tmp_todo_list.sqlite3'))
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            'create table Users (pubkey text primary key unique, ip integer unique)'
        )
        await db.execute('create table Domains (name text primary key unique)')
        await db.commit()
    monkeypatch.setenv('DB_FILE', db_path)
    yield db_path
    Path(db_path).unlink()


@pytest.mark.asyncio
@pytest.fixture(autouse=True, name='tmp_database_data')
async def fixture_tmp_database_data(tmp_database_tables):
    db_path = tmp_database_tables
    user = ('test_pubkey', '2')
    domain = ('twitter.com',)
    async with aiosqlite.connect(db_path) as db:
        await db.execute('insert into Users (pubkey, ip) values (?, ?)', user)
        await db.execute('insert into Domains (name) values (?)', domain)
        await db.commit()


@pytest.mark.asyncio
@pytest.fixture(name='dns_checkup')
async def fixture_dns_checkup():
    resolve, _ = Resolver()
    response_list = []
    ip_addresses = await resolve('twitter.com', TYPES.A)
    for ip in ip_addresses:
        response_list.append(str(ip))
    return response_list


@pytest.fixture(name='register_response')
def fixture_register_response():
    return {
        'server_pubkey': 'K5OL6Ej+A7uFNg95AOrzL0ugrDoSGV2ng6B2qFoVkDI=',
        'endpoint_address': '159.65.197.55',
        'endpoint_port': 51820,
        'client_inbound_ip': '3',
        'server_inbound_ip': '192.168.20.1',
    }


@pytest.fixture()
def client():
    c = TestClient(app)
    return c
