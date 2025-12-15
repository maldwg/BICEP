from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import os
from app.bicep_utils.models.ids_base import Alert
import logging
from datetime import datetime
import uuid
import httpx

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


async def query_average_cpu_usage(
    container_name: str, start_time: str, end_time: str
) -> float:
    """
    Query Prometheus for average CPU usage of a container during a time range.
    Returns CPU usage as a percentage (0-100).
    """
    try:
        prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
        if not prometheus_url.startswith("http://") and not prometheus_url.startswith(
            "https://"
        ):
            prometheus_url = f"http://{prometheus_url}"
        if not prometheus_url:
            LOGGER.warning("PROMETHEUS_URL not set, cannot query CPU metrics")
            return None

        # Convert time strings to timestamps
        start_ts = datetime.strptime(start_time, "%d-%m-%Y %H:%M:%S.%f").timestamp()
        end_ts = datetime.strptime(end_time, "%d-%m-%Y %H:%M:%S.%f").timestamp()

        # Query for average CPU usage rate over the time range
        # rate() calculates per-second rate, multiply by 100 for percentage
        query = f'avg(container_cpu_usage{{name=~".*{container_name}.*"}})'

        params = {
            "query": query,
            "start": start_ts,
            "end": end_ts,
            "step": "1s",  # Sample every 15 seconds
        }

        async with httpx.AsyncClient() as client:
            # Use query_range for time-based queries
            response = await client.get(
                f"{prometheus_url}/api/v1/query_range", params=params, timeout=10.0
            )

            if response.status_code != 200:
                LOGGER.error(f"Prometheus query failed: {response.status_code}")
                return None

            data = response.json()

            if data.get("status") != "success":
                LOGGER.error(f"Prometheus query unsuccessful: {data}")
                return None

            results = data.get("data", {}).get("result", [])

            if not results:
                LOGGER.warning(f"No CPU metrics found for container {container_name}")
                return None

            # Calculate average from all values
            all_values = []
            for result in results:
                values = result.get("values", [])
                all_values.extend([float(v[1]) for v in values])

            if all_values:
                avg_cpu = sum(all_values) / len(all_values)
                return round(avg_cpu, 2)

            return None

    except Exception as e:
        LOGGER.error(f"Error querying CPU metrics: {e}")
        return None


async def query_average_memory_usage(
    container_name: str, start_time: str, end_time: str
) -> float:
    """
    Query Prometheus for average memory usage of a container during a time range.
    Returns memory usage in MB.
    """
    try:

        prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
        if not prometheus_url.startswith("http://") and not prometheus_url.startswith(
            "https://"
        ):
            prometheus_url = f"http://{prometheus_url}"
        if not prometheus_url:
            LOGGER.warning("PROMETHEUS_URL not set, cannot query memory metrics")
            return None

        # Convert time strings to timestamps
        start_ts = datetime.strptime(start_time, "%d-%m-%Y %H:%M:%S.%f").timestamp()
        end_ts = datetime.strptime(end_time, "%d-%m-%Y %H:%M:%S.%f").timestamp()

        # Query for average memory usage, convert bytes to MB
        query = f'avg(container_memory_usage_bytes{{name=~".*{container_name}.*"}}) / 1024 / 1024'

        params = {"query": query, "start": start_ts, "end": end_ts, "step": "1s"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query_range", params=params, timeout=10.0
            )

            if response.status_code != 200:
                LOGGER.error(f"Prometheus query failed: {response.status_code}")
                return None

            data = response.json()

            if data.get("status") != "success":
                LOGGER.error(f"Prometheus query unsuccessful: {data}")
                return None

            results = data.get("data", {}).get("result", [])

            if not results:
                LOGGER.warning(
                    f"No memory metrics found for container {container_name}"
                )
                return None

            # Calculate average from all values
            all_values = []
            for result in results:
                values = result.get("values", [])
                all_values.extend([float(v[1]) for v in values])

            if all_values:
                avg_memory = sum(all_values) / len(all_values)
                return round(avg_memory, 2)

            return None

    except Exception as e:
        LOGGER.error(f"Error querying memory metrics: {e}")
        return None


async def query_current_cpu_usage(container_name: str) -> float:
    """
    Query Prometheus for current CPU usage of a container (last 1 minute rate).
    Returns CPU usage in cores.
    """
    try:
        prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
        if not prometheus_url.startswith("http://") and not prometheus_url.startswith(
            "https://"
        ):
            prometheus_url = f"http://{prometheus_url}"
        if not prometheus_url:
            LOGGER.warning("PROMETHEUS_URL not set, cannot query current CPU usage")
            return None

        # Query for current CPU usage from pushgateway metrics
        # The metrics are pushed with the label "name" matching container_name
        query = f'container_cpu_usage{{name="{container_name}"}}'

        params = {"query": query}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query", params=params, timeout=5.0
            )

            if response.status_code != 200:
                return None

            data = response.json()
            results = data.get("data", {}).get("result", [])

            if not results:
                return 0.0

            # Get the value from the first result
            value = float(results[0].get("value", [0, 0])[1])
            return round(value, 4)

    except Exception as e:
        LOGGER.error(f"Error querying current CPU metrics: {e}")
        return None


async def query_current_memory_usage(container_name: str) -> float:
    """
    Query Prometheus for current memory usage of a container.
    Returns memory usage in MB.
    """
    try:
        prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
        if not prometheus_url.startswith("http://") and not prometheus_url.startswith(
            "https://"
        ):
            prometheus_url = f"http://{prometheus_url}"
        if not prometheus_url:
            LOGGER.warning("PROMETHEUS_URL not set, cannot query current memory usage")
            return None

        # Query for current memory usage from pushgateway metrics
        query = f'container_memory_usage_bytes{{name="{container_name}"}} / 1024 / 1024'

        params = {"query": query}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query", params=params, timeout=5.0
            )

            if response.status_code != 200:
                return None

            data = response.json()
            results = data.get("data", {}).get("result", [])

            if not results:
                return 0.0

            # Get the value from the first result
            value = float(results[0].get("value", [0, 0])[1])
            return round(value, 2)

    except Exception as e:
        LOGGER.error(f"Error querying current memory metrics: {e}")
        return None


async def query_cpu_usage_series(
    container_name: str, start_time: str, end_time: str
) -> list[float]:
    """
    Query Prometheus for a series of CPU usage samples for a container during a time range.
    Returns list of CPU usage percentages.
    """
    try:
        prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
        if not prometheus_url.startswith("http://") and not prometheus_url.startswith(
            "https://"
        ):
            prometheus_url = f"http://{prometheus_url}"
        if not prometheus_url:
            LOGGER.warning("PROMETHEUS_URL not set, cannot query CPU usage series")
            return []

        # Convert time strings to timestamps
        start_ts = datetime.strptime(start_time, "%d-%m-%Y %H:%M:%S.%f").timestamp()
        end_ts = datetime.strptime(end_time, "%d-%m-%Y %H:%M:%S.%f").timestamp()

        # Query for CPU usage rate over the time range
        query = f'container_cpu_usage{{name=~".*{container_name}.*"}}'

        params = {"query": query, "start": start_ts, "end": end_ts, "step": "2s"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query_range", params=params, timeout=10.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            results = data.get("data", {}).get("result", [])

            if not results:
                return []

            # Extract values from the first result series
            values = results[0].get("values", [])
            return [float(v[1]) for v in values]

    except Exception as e:
        LOGGER.error(f"Error querying CPU series: {e}")
        return []


async def query_memory_usage_series(
    container_name: str, start_time: str, end_time: str
) -> list[float]:
    """
    Query Prometheus for a series of memory usage samples for a container during a time range.
    Returns list of memory usage in MB.
    """
    try:
        prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
        if not prometheus_url.startswith("http://") and not prometheus_url.startswith(
            "https://"
        ):
            prometheus_url = f"http://{prometheus_url}"
        if not prometheus_url:
            LOGGER.warning("PROMETHEUS_URL not set, cannot query memory usage series")
            return []

        # Convert time strings to timestamps
        start_ts = datetime.strptime(start_time, "%d-%m-%Y %H:%M:%S.%f").timestamp()
        end_ts = datetime.strptime(end_time, "%d-%m-%Y %H:%M:%S.%f").timestamp()

        # Query for memory usage
        query = f'container_memory_usage_bytes{{name=~".*{container_name}.*"}} / 1024 / 1024'

        params = {"query": query, "start": start_ts, "end": end_ts, "step": "2s"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query_range", params=params, timeout=10.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            results = data.get("data", {}).get("result", [])

            if not results:
                return []

            # Extract values from the first result series
            values = results[0].get("values", [])
            return [float(v[1]) for v in values]

    except Exception as e:
        LOGGER.error(f"Error querying memory series: {e}")
        return []
