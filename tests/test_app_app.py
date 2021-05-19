import pytest

from app.app import get_all_routes, get_ip, nslookup


@pytest.mark.asyncio
async def test_get_ip():
    address = await get_ip()
    assert address == 3


@pytest.mark.asyncio
async def test_nslookup(dns_checkup, fake_redis):
    domain = 'twitter.com'
    await nslookup(fake_redis, domain)
    ips = await fake_redis.lrange(domain, 0, -1, encoding='utf-8')
    assert ips == dns_checkup


@pytest.mark.asyncio
async def test_get_all_routes(fake_redis, dns_checkup):
    ch_name = 'channel:routes'
    [channel] = await fake_redis.subscribe(ch_name)
    await get_all_routes(fake_redis, ch_name)
    recieved_domain = await channel.get(encoding='utf-8')
    assert recieved_domain == dns_checkup[0]


def test_register_endpoint_ok(client, register_response):
    response = client.post('/register', json={'key': 'justakey'})
    assert response.json() == register_response


def test_register_endpoint_failed(client):
    response = client.post('/register', json={'key': 'test_pubkey'})
    assert response.json() == {'error': 'Public key already present in database'}


def test_add_domain_endpoint_ok(client):
    domain = 'facebook.com'
    response = client.post(f'/domain/{domain}')
    assert response.json() == {'domain': domain, 'status': 'created'}


def test_add_domain_endpoint_failed(client):
    domain = 'twitter.com'
    response = client.post(f'/domain/{domain}')
    assert response.json() == {'error': 'Domain already present in database'}


def test_delete_domain_endpoint(client):
    domain = 'twitter.com'
    response = client.delete(f'/domain/{domain}')
    assert response.json() == {'domain': domain, 'status': 'deleted'}


@pytest.mark.asyncio
async def test_routes_channel_getall(client, dns_checkup):
    with client.websocket_connect('/ws') as websocket:
        websocket.send_text('getall')
        msg = websocket.receive_text()
        assert msg == dns_checkup[0]


@pytest.mark.asyncio
async def test_routes_channel_ping(client):
    with client.websocket_connect('/ws') as websocket:
        websocket.send_text('ping')
        msg = websocket.receive_text()
        assert msg == 'Pong!'
