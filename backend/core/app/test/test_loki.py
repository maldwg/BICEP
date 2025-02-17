import pytest
from ..loki import get_chunk_of_values


@pytest.mark.asyncio
async def test_chunk_values():
    values = [x for x in range(0,12351)]
    chunked_values = await get_chunk_of_values(values, alert_chunk_size=1000)
    assert len(chunked_values) == 13
    assert len(chunked_values[-1]) == 351