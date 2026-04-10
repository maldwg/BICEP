import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.prometheus import (
    RESOURCE_QUERY_MODE_EXACT,
    RESOURCE_QUERY_MODE_PREFIX,
    build_resource_metric_query,
    build_resource_query_spec_for_ids_system,
    deserialize_resource_query_targets,
    query_average_cpu_usage,
    query_average_memory_usage,
    query_current_cpu_usage,
    query_current_memory_usage,
    query_cpu_usage_series,
    query_memory_usage_series,
    serialize_resource_query_targets,
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
    """When Prometheus returns multiple result series, should sum them per timestamp."""
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
        # Summed series becomes [0.8, 1.2], average = 1.0 cores.
        assert result == 1.0


@pytest.mark.asyncio
async def test_query_cpu_usage_series_aggregates_multiple_results():
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
        result = await query_cpu_usage_series("test-container", start_time, end_time)

        assert result == [0.8, 1.2]


@pytest.mark.asyncio
async def test_query_average_cpu_usage_exact_target_uses_exact_label_matcher():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": [{"values": [[1, "0.2"], [2, "0.4"]]}]},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_cpu_usage("Suricata-38667", start_time, end_time)

        assert result == 0.3
        query = mock_client.get.call_args.kwargs["params"]["query"]
        assert 'name="Suricata-38667"' in query
        assert 'name=~' not in query


@pytest.mark.asyncio
async def test_query_average_memory_usage_prefix_targets_builds_sum_query():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": [{"values": [[1, "256.0"], [2, "512.0"]]}]},
        }
        mock_client.get.return_value = mock_response

        start_time = "01-01-2021 00:00:00.000000"
        end_time = "01-01-2021 00:01:00.000000"
        result = await query_average_memory_usage(
            None,
            start_time,
            end_time,
            match_mode=RESOURCE_QUERY_MODE_PREFIX,
            targets=["bicep_cids_1_core-sensor", "bicep_cids_1_core-aggregator"],
        )

        assert result == 384.0
        query = mock_client.get.call_args.kwargs["params"]["query"]
        assert "sum(container_memory_usage_bytes" in query
        assert "bicep_cids_1_core-sensor" in query
        assert "bicep_cids_1_core-aggregator" in query
        assert "\\-" not in query
        assert "(?:" not in query


def test_serialize_and_deserialize_resource_query_targets():
    targets = ["sensor-prefix", "aggregator-prefix"]

    serialized = serialize_resource_query_targets(targets)

    assert deserialize_resource_query_targets(serialized) == targets


def test_build_resource_query_spec_for_ids_system_uses_component_prefixes():
    ids_system = MagicMock()
    ids_system.name = "hamstring-8080"
    component_one = MagicMock()
    component_one.name = "bicep_cids_5_core-sensor-1"
    component_two = MagicMock()
    component_two.name = "bicep_cids_5_core-aggregator-1"
    component_three = MagicMock()
    component_three.name = "bicep_cids_5_remote-sensor-2"
    ids_system.components = [component_one, component_two, component_three]

    mode, targets = build_resource_query_spec_for_ids_system(ids_system)

    assert mode == RESOURCE_QUERY_MODE_PREFIX
    assert targets == [
        "bicep_cids_5_core-aggregator",
        "bicep_cids_5_core-sensor",
        "bicep_cids_5_remote-sensor",
    ]


def test_build_resource_query_spec_for_single_container_falls_back_to_exact_name():
    ids_system = MagicMock()
    ids_system.name = "suricata-8080"
    ids_system.components = []

    mode, targets = build_resource_query_spec_for_ids_system(ids_system)

    assert mode == RESOURCE_QUERY_MODE_EXACT
    assert targets == ["suricata-8080"]


def test_build_resource_metric_query_prefix_does_not_escape_hyphen():
    query = build_resource_metric_query(
        "container_cpu_usage",
        match_mode=RESOURCE_QUERY_MODE_PREFIX,
        targets=[
            "bicep_cids_4_core-server-detector",
            "bicep_cids_4_core-server-monitoring-agent",
        ],
    )

    assert query is not None
    assert 'name=~"^(' in query
    assert "bicep_cids_4_core-server-detector([-_].*)?" in query
    assert "bicep_cids_4_core-server-monitoring-agent([-_].*)?" in query
    assert "\\-" not in query
