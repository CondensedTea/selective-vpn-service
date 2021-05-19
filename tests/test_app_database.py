import pytest

from app.database import add_domain, add_user, delete_domain, get_all_domains
from app.exceptions import DomainExsists, PublicKeyExsists


@pytest.mark.asyncio
async def test_get_all_domains():
    domains = await get_all_domains()
    assert domains == ['twitter.com']


@pytest.mark.asyncio
async def test_add_user_ok():
    result = await add_user('dummy', 3)
    assert result == 'created'


@pytest.mark.asyncio
async def test_add_user_pubkey_exsists():
    with pytest.raises(PublicKeyExsists):
        await add_user('test_pubkey', 3)


@pytest.mark.asyncio
async def test_add_domain_ok():
    result = await add_domain('facebook.com')
    assert result == 'created'


@pytest.mark.asyncio
async def test_add_user_domain_exsists():
    with pytest.raises(DomainExsists):
        await add_domain('twitter.com')


@pytest.mark.asyncio
async def test_delete_domain_ok():
    result = await delete_domain('twitter.com')
    assert result == 'deleted'
