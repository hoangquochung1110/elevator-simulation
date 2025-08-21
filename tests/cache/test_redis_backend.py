import pytest
import fakeredis

from src.libs.cache.backends.redis import RedisBackend

@pytest.mark.asyncio
async def test_keys_returns_string_keys():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    backend = RedisBackend()
    # Inject fake redis client
    backend._client = fake

    await backend.set('foo', 'bar')
    await backend.set('fizz', 'buzz')

    keys = await backend.keys('f*')
    assert set(keys) == {'foo', 'fizz'}
