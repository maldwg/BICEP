import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.prometheus import (
    query_average_cpu_usage,
    query_average_memory_usage,
    query_current_cpu_usage,
    query_current_memory_usage,
    query_cpu_usage_series,
    query_memory_usage_series,
)
import os


@pytest.mark.asyncio
async def test_query_average_cpu_usage_success():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [{"values": [[1609459200, "0.5"], [1609459215, "0.6"]]}]
            },
        }
        mock_client.get.return_value = mock_response

        # Mock start and end times
        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"

        result = await query_average_cpu_usage("test-container", start_time, end_time)
        assert result == 0.55


@pytest.mark.asyncio
async def test_query_average_cpu_usage_failure_http():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"

        result = await query_average_cpu_usage("test-container", start_time, end_time)
        assert result is None


@pytest.mark.asyncio
async def test_query_average_memory_usage_success():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "values": [[1609459200, "10485760"], [1609459215, "20971520"]]
                    }  # 10MB, 20MB
                ]
            },
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"

        # Note: query_average_memory_usage divides by 1024*1024 in the query itself?
        # Wait, the function docs say "Query for average memory usage of a container during a time range. Returns memory usage in MB."
        # And the code does: query = f'avg(container_memory_usage_bytes{{name=~".*{container_name}.*"}}) / 1024 / 1024'
        # BUT the test mock returns raw values. IF the query string is what controls the calculation on prom side,
        # our mock response should simulate receiving the ALREADY CALCULATED values if we assume the query worked.
        # However, the logic in python takes the values and averages them.
        # "all_values.extend([float(v[1]) for v in values])"
        # "avg_memory = sum(all_values) / len(all_values)"
        # So if the query ALREADY does /1024/1024, the values returned by prom will be in MB.
        # So let's return values in MB in our mock to simulate that.

        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [{"values": [[1609459200, "10.0"], [1609459215, "20.0"]]}]
            },
        }

        result = await query_average_memory_usage(
            "test-container", start_time, end_time
        )
        assert result == 15.0


@pytest.mark.asyncio
async def test_query_current_cpu_usage_success():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": [{"value": [1609459200, "0.12345"]}]},
        }
        mock_client.get.return_value = mock_response

        result = await query_current_cpu_usage("test-container")
        assert result == 0.1235


@pytest.mark.asyncio
async def test_query_current_memory_usage_success():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        # The query does / 1024 / 1024, so return value is in MB
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": [{"value": [1609459200, "128.5"]}]},
        }
        mock_client.get.return_value = mock_response

        # Function returns rounded to 2 decimals
        result = await query_current_memory_usage("test-container")
        assert result == 128.5


@pytest.mark.asyncio
async def test_query_cpu_usage_series_success():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": [{"values": [[1, "0.1"], [2, "0.2"], [3, "0.3"]]}]},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_cpu_usage_series("test-container", start_time, end_time)
        assert result == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_query_memory_usage_series_success():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Query does / 1024 / 1024
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": [{"values": [[1, "100.0"], [2, "105.5"]]}]},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_memory_usage_series("test-container", start_time, end_time)
        assert result == [100.0, 105.5]


@pytest.mark.asyncio
async def test_prom_url_not_set():
    with patch.dict(os.environ, {}, clear=True):
        # When PROMETHEUS_URL is not set, it defaults to http://prometheus:9090 in the code itself
        # So we can't easily test "not set" returning None unless we force it to empty string or check logic
        # Actually the code says: prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
        # Then: if not prometheus_url: ...
        # Since it has a default, this branch might be unreachable unless set to empty string actively.

        with patch.dict(os.environ, {"PROMETHEUS_URL": ""}):
            start_time = "01-01-2021 00:00:00.000000"
            end_time = "01-01-2021 00:01:00.000000"
            result = await query_average_cpu_usage("test", start_time, end_time)
            assert result is None


@pytest.mark.asyncio
async def test_query_exception_handling():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Connection error")

        result = await query_current_cpu_usage("test")
        assert result is None


# ==================== AVERAGE CPU - MISSING BRANCHES ====================


@pytest.mark.asyncio
async def test_query_average_cpu_usage_no_results():
    """When Prometheus returns success but no results, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_cpu_usage("test-container", start_time, end_time)
        assert result is None


@pytest.mark.asyncio
async def test_query_average_cpu_usage_unsuccessful_status():
    """When Prometheus returns non-success status, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "errorType": "bad_data",
            "error": "invalid query",
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_cpu_usage("test-container", start_time, end_time)
        assert result is None


@pytest.mark.asyncio
async def test_query_average_cpu_usage_empty_values():
    """When results have empty values arrays, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": [{"values": []}]},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_cpu_usage("test-container", start_time, end_time)
        assert result is None


@pytest.mark.asyncio
async def test_query_average_cpu_usage_exception():
    """When an exception occurs, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Timeout")

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_cpu_usage("test-container", start_time, end_time)
        assert result is None


# ==================== AVERAGE MEMORY - MISSING BRANCHES ====================


@pytest.mark.asyncio
async def test_query_average_memory_usage_http_failure():
    """When Prometheus HTTP request fails, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_memory_usage("test-container", start_time, end_time)
        assert result is None


@pytest.mark.asyncio
async def test_query_average_memory_usage_unsuccessful_status():
    """When Prometheus returns non-success status, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "error": "bad query"}
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_memory_usage("test-container", start_time, end_time)
        assert result is None


@pytest.mark.asyncio
async def test_query_average_memory_usage_no_results():
    """When Prometheus returns empty results, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_memory_usage("test-container", start_time, end_time)
        assert result is None


@pytest.mark.asyncio
async def test_query_average_memory_usage_empty_values():
    """When results have empty values arrays, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": [{"values": []}]},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_memory_usage("test-container", start_time, end_time)
        assert result is None


@pytest.mark.asyncio
async def test_query_average_memory_usage_exception():
    """When an exception occurs, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Connection error")

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_memory_usage("test-container", start_time, end_time)
        assert result is None


# ==================== CURRENT CPU - MISSING BRANCHES ====================


@pytest.mark.asyncio
async def test_query_current_cpu_usage_http_failure():
    """When HTTP request fails, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response

        result = await query_current_cpu_usage("test-container")
        assert result is None


@pytest.mark.asyncio
async def test_query_current_cpu_usage_no_results():
    """When no results, should return 0.0."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []},
        }
        mock_client.get.return_value = mock_response

        result = await query_current_cpu_usage("test-container")
        assert result == 0.0


# ==================== CURRENT MEMORY - MISSING BRANCHES ====================


@pytest.mark.asyncio
async def test_query_current_memory_usage_http_failure():
    """When HTTP request fails, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response

        result = await query_current_memory_usage("test-container")
        assert result is None


@pytest.mark.asyncio
async def test_query_current_memory_usage_no_results():
    """When no results, should return 0.0."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []},
        }
        mock_client.get.return_value = mock_response

        result = await query_current_memory_usage("test-container")
        assert result == 0.0


@pytest.mark.asyncio
async def test_query_current_memory_usage_exception():
    """When an exception occurs, should return None."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Connection error")

        result = await query_current_memory_usage("test-container")
        assert result is None


# ==================== CPU SERIES - MISSING BRANCHES ====================


@pytest.mark.asyncio
async def test_query_cpu_usage_series_http_failure():
    """When HTTP request fails, should return empty list."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_cpu_usage_series("test-container", start_time, end_time)
        assert result == []


@pytest.mark.asyncio
async def test_query_cpu_usage_series_no_results():
    """When no results, should return empty list."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_cpu_usage_series("test-container", start_time, end_time)
        assert result == []


@pytest.mark.asyncio
async def test_query_cpu_usage_series_exception():
    """When an exception occurs, should return empty list."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Timeout")

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_cpu_usage_series("test-container", start_time, end_time)
        assert result == []


# ==================== MEMORY SERIES - MISSING BRANCHES ====================


@pytest.mark.asyncio
async def test_query_memory_usage_series_http_failure():
    """When HTTP request fails, should return empty list."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_memory_usage_series("test-container", start_time, end_time)
        assert result == []


@pytest.mark.asyncio
async def test_query_memory_usage_series_no_results():
    """When no results, should return empty list."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_memory_usage_series("test-container", start_time, end_time)
        assert result == []


@pytest.mark.asyncio
async def test_query_memory_usage_series_exception():
    """When an exception occurs, should return empty list."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Timeout")

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_memory_usage_series("test-container", start_time, end_time)
        assert result == []


# ==================== URL PREFIX HANDLING ====================


@pytest.mark.asyncio
async def test_query_with_url_without_http_prefix():
    """When PROMETHEUS_URL doesn't start with http, should add http:// prefix."""
    with patch.dict(os.environ, {"PROMETHEUS_URL": "prometheus:9090"}):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "data": {"result": [{"value": [1609459200, "0.5"]}]},
            }
            mock_client.get.return_value = mock_response

            result = await query_current_cpu_usage("test-container")
            assert result == 0.5
            # Verify the URL was prefixed with http://
            call_args = mock_client.get.call_args
            assert call_args[0][0].startswith("http://prometheus:9090")


@pytest.mark.asyncio
async def test_query_with_https_url():
    """When PROMETHEUS_URL starts with https, should not add extra prefix."""
    with patch.dict(os.environ, {"PROMETHEUS_URL": "https://prometheus:9090"}):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "data": {"result": [{"value": [1609459200, "0.5"]}]},
            }
            mock_client.get.return_value = mock_response

            result = await query_current_cpu_usage("test-container")
            assert result == 0.5
            call_args = mock_client.get.call_args
            assert call_args[0][0].startswith("https://prometheus:9090")


@pytest.mark.asyncio
async def test_prom_url_empty_string_memory():
    """When PROMETHEUS_URL is empty string for memory query, should return None."""
    with patch.dict(os.environ, {"PROMETHEUS_URL": ""}):
        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_memory_usage("test", start_time, end_time)
        assert result is None


@pytest.mark.asyncio
async def test_prom_url_empty_string_current_cpu():
    """When PROMETHEUS_URL is empty string for current CPU query, should return None."""
    with patch.dict(os.environ, {"PROMETHEUS_URL": ""}):
        result = await query_current_cpu_usage("test")
        assert result is None


@pytest.mark.asyncio
async def test_prom_url_empty_string_current_memory():
    """When PROMETHEUS_URL is empty string for current memory query, should return None."""
    with patch.dict(os.environ, {"PROMETHEUS_URL": ""}):
        result = await query_current_memory_usage("test")
        assert result is None


@pytest.mark.asyncio
async def test_prom_url_empty_string_cpu_series():
    """When PROMETHEUS_URL is empty string for CPU series query, should return []."""
    with patch.dict(os.environ, {"PROMETHEUS_URL": ""}):
        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_cpu_usage_series("test", start_time, end_time)
        assert result == []


@pytest.mark.asyncio
async def test_prom_url_empty_string_memory_series():
    """When PROMETHEUS_URL is empty string for memory series query, should return []."""
    with patch.dict(os.environ, {"PROMETHEUS_URL": ""}):
        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_memory_usage_series("test", start_time, end_time)
        assert result == []


# ==================== MULTI-RESULT AGGREGATION ====================


@pytest.mark.asyncio
async def test_query_average_cpu_usage_multiple_results():
    """When Prometheus returns multiple result series, should average across all."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {"values": [[1, "0.2"], [2, "0.4"]]},
                    {"values": [[1, "0.6"], [2, "0.8"]]},
                ]
            },
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_cpu_usage("test-container", start_time, end_time)
        # (0.2 + 0.4 + 0.6 + 0.8) / 4 = 0.5
        assert result == 0.5
