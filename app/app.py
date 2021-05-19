import asyncio
import threading
import time
from typing import Dict

import aioredis
import aioschedule as schedule
from aiodnsresolver import TYPES, Resolver
from aioredis import Channel, ConnectionsPool
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

from .database import add_domain, add_user, delete_domain, get_all_domains, get_all_ips
from .exceptions import DomainExsists, PublicKeyExsists
from .pydantic_models import RegisterRequestModel, RegisterResponseModel
from .wireguard import WireGuard

app = FastAPI()
wg = WireGuard()


endpoint_address = '159.65.197.55'
endpoint_port = 51820
server_inbound_ip = '192.168.20.1'
server_pubkey = 'K5OL6Ej+A7uFNg95AOrzL0ugrDoSGV2ng6B2qFoVkDI='
redis_url = ('redis', 6379)


async def get_redis() -> ConnectionsPool:
    pool = await aioredis.create_redis_pool(redis_url)
    return pool


async def close_redis(r: ConnectionsPool) -> None:
    r.close()
    await r.wait_closed()


async def get_ip() -> int:
    all_ips = list(range(2, 255))
    taken_ips = await get_all_ips()
    free_ips = set(all_ips) - set(taken_ips)
    return list(free_ips)[0]


async def reader(channel: Channel, socket: WebSocket) -> None:
    async for message in channel.iter():
        await socket.send_text(message.decode('utf-8'))


async def get_all_routes(redis: ConnectionsPool, channel: str) -> None:
    domains = await get_all_domains()
    for domain in domains:
        routes = await redis.lrange(domain, 0, -1)
        for route in routes:
            await redis.publish(channel, route)


async def pong(redis: ConnectionsPool, channel: str) -> None:
    await redis.publish(channel, 'Pong!')


async def nslookup(redis: ConnectionsPool, domain: str) -> None:
    resolve, _ = Resolver()
    ttl = 180
    ip_addresses = await resolve(domain, TYPES.A)
    loop = asyncio.get_event_loop()
    for ip_address in ip_addresses:
        new_ttl = ip_address.expires_at - loop.time()
        if new_ttl < ttl:
            ttl = new_ttl
        if ttl < 60:
            ttl = 60
        await redis.rpush(domain, str(ip_address))
        await redis.expire(domain, ttl)
        await redis.publish('channel:routes', str(ip_address))
    schedule.clear(domain)
    schedule.every(ttl).seconds.do(nslookup, redis=redis, domain=domain).tag(domain)


async def run_schedule() -> None:
    while True:
        await schedule.run_pending()
        time.sleep(0.1)


@app.on_event('startup')
async def startup() -> None:
    redis = await get_redis()
    _thread = threading.Thread(target=asyncio.run, args=(schedule_nslookups(redis),))
    _thread.start()


async def schedule_nslookups(redis: ConnectionsPool) -> None:
    domains = await get_all_domains()
    for domain in domains:
        await nslookup(redis, domain)
    loop = asyncio.get_event_loop()
    loop.create_task(run_schedule())


@app.exception_handler(PublicKeyExsists)
async def public_key_exsists_handler(
    request: Request, exc: PublicKeyExsists  # pylint:disable=unused-argument
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={'error': 'Public key already present in database'},
    )


@app.exception_handler(DomainExsists)
async def domain_exsists_handler(
    request: Request, exc: DomainExsists  # pylint:disable=unused-argument
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={'error': 'Domain already present in database'},
    )


@app.post('/register')
async def register(
    form: RegisterRequestModel, r: ConnectionsPool = Depends(get_redis)
) -> RegisterResponseModel:
    ip = await get_ip()
    await add_user(form.key, ip)
    await r.lpop('ip_pool')
    await wg.set_peer(form.key, ip)
    return RegisterResponseModel(
        server_pubkey=server_pubkey,
        endpoint_address=endpoint_address,
        endpoint_port=endpoint_port,
        client_inbound_ip=ip,
        server_inbound_ip=server_inbound_ip,
    )


@app.post('/domain/{name}', status_code=status.HTTP_201_CREATED)
async def add_domain_endpoint(name: str) -> Dict[str, str]:
    result = await add_domain(name)
    return {'domain': name, 'status': result}


@app.delete('/domain/{name}', status_code=status.HTTP_200_OK)
async def delete_domain_endpoint(name: str) -> Dict[str, str]:
    result = await delete_domain(name)
    return {'domain': name, 'status': result}


@app.websocket('/ws')
async def routes_channel(
    websocket: WebSocket, r: ConnectionsPool = Depends(get_redis)
) -> None:
    await websocket.accept()
    channel_name = 'channel:routes'
    [channel] = await r.subscribe(channel_name)
    asyncio.get_running_loop().create_task(reader(channel, websocket))
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == 'getall':
                await get_all_routes(r, channel_name)
            elif msg == 'ping':
                await pong(r, channel_name)
    except WebSocketDisconnect:
        await close_redis(r)
