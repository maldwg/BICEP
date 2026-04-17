import json
import logging
import os
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

RESOURCE_QUERY_MODE_EXACT = "exact"
RESOURCE_QUERY_MODE_PREFIX = "prefix"


def serialize_resource_query_targets(targets: list[str] | None) -> str | None:
    if not targets:
        return None
    return json.dumps(list(targets))


def deserialize_resource_query_targets(raw_targets: str | None) -> list[str]:
    if not raw_targets:
        return []

    try:
        parsed = json.loads(raw_targets)
    except json.JSONDecodeError:
        LOGGER.warning("Could not decode resource query targets JSON.")
        return []

    if not isinstance(parsed, list):
        return []

    return [str(target) for target in parsed if target]


def default_resource_query_spec(
    container_name: str | None,
) -> tuple[str | None, list[str]]:
    if not container_name:
        return None, []
    return RESOURCE_QUERY_MODE_EXACT, [container_name]


def _derive_compose_container_prefix(container_name: str) -> str:
    normalized_name = container_name.strip()
    suffix_separator_index = max(normalized_name.rfind("-"), normalized_name.rfind("_"))
    if suffix_separator_index == -1:
        return normalized_name

    suffix = normalized_name[suffix_separator_index + 1 :]
    if suffix.isdigit():
        return normalized_name[:suffix_separator_index]
    return normalized_name


def build_resource_query_spec_for_ids_system(
    ids_system,
) -> tuple[str | None, list[str]]:
    raw_components = getattr(ids_system, "components", None)
    components = (
        raw_components
        if isinstance(raw_components, (list, tuple, set))
        else []
    )
    component_prefixes = sorted(
        {
            _derive_compose_container_prefix(component.name)
            for component in components
            if getattr(component, "name", None)
        }
    )
    if component_prefixes:
        return RESOURCE_QUERY_MODE_PREFIX, component_prefixes

    return default_resource_query_spec(getattr(ids_system, "name", None))


def _normalize_prometheus_url() -> str | None:
    prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
    if not prometheus_url:
        return None
    if not prometheus_url.startswith("http://") and not prometheus_url.startswith(
        "https://"
    ):
        prometheus_url = f"http://{prometheus_url}"
    return prometheus_url


def _parse_timestamp(timestamp: str) -> float:
    return datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S.%f").timestamp()


def _resolve_query_targets(
    container_name: str | None,
    match_mode: str | None,
    targets: list[str] | None,
) -> tuple[str | None, list[str]]:
    if targets:
        normalized_targets = [target for target in targets if target]
        if not normalized_targets:
            return default_resource_query_spec(container_name)
        return match_mode or RESOURCE_QUERY_MODE_EXACT, normalized_targets
    return default_resource_query_spec(container_name)


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _escape_promql_regex_literal(value: str) -> str:
    regex_special_chars = set(".+*?^$()[]{}|\\")
    escaped = []
    for char in value:
        if char in regex_special_chars:
            escaped.append("\\")
        escaped.append(char)
    return _escape_label_value("".join(escaped))


def _build_name_selector(match_mode: str | None, targets: list[str]) -> str | None:
    if not targets:
        return None

    if match_mode == RESOURCE_QUERY_MODE_EXACT and len(targets) == 1:
        return f'name="{_escape_label_value(targets[0])}"'

    escaped_targets = [_escape_promql_regex_literal(target) for target in targets]
    if match_mode == RESOURCE_QUERY_MODE_PREFIX:
        patterns = [f"{target}([-_].*)?" for target in escaped_targets]
    else:
        patterns = escaped_targets

    return f'name=~"^({"|".join(patterns)})$"'


def _build_range_query(
    metric_name: str,
    match_mode: str | None,
    targets: list[str],
    *,
    convert_to_mb: bool = False,
) -> str | None:
    selector = _build_name_selector(match_mode, targets)
    if selector is None:
        return None

    query = f"sum({metric_name}{{{selector}}})"
    if convert_to_mb:
        query += " / 1024 / 1024"
    return query


def build_resource_metric_query(
    metric_name: str,
    *,
    match_mode: str | None,
    targets: list[str] | None,
    convert_to_mb: bool = False,
) -> str | None:
    return _build_range_query(
        metric_name,
        match_mode,
        [target for target in (targets or []) if target],
        convert_to_mb=convert_to_mb,
    )


async def _query_range_series(
    query: str | None, start_time: str, end_time: str, step: str
) -> list[float]:
    prometheus_url = _normalize_prometheus_url()
    if not prometheus_url:
        LOGGER.warning("PROMETHEUS_URL not set, cannot query Prometheus")
        return []
    if not query:
        return []

    params = {
        "query": query,
        "start": _parse_timestamp(start_time),
        "end": _parse_timestamp(end_time),
        "step": step,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{prometheus_url}/api/v1/query_range", params=params, timeout=10.0
        )

        if response.status_code != 200:
            LOGGER.error(
                "Prometheus query failed: %s for query=%s response=%s",
                response.status_code,
                query,
                response.text,
            )
            return []

        data = response.json()
        if data.get("status") != "success":
            LOGGER.error(f"Prometheus query unsuccessful: {data}")
            return []

        results = data.get("data", {}).get("result", [])
        if not results:
            return []

        aggregated_by_timestamp: dict[float, float] = {}
        for result in results:
            for timestamp, value in result.get("values", []):
                timestamp_key = float(timestamp)
                aggregated_by_timestamp[timestamp_key] = (
                    aggregated_by_timestamp.get(timestamp_key, 0.0) + float(value)
                )

        return [
            round(aggregated_by_timestamp[timestamp], 10)
            for timestamp in sorted(aggregated_by_timestamp)
        ]


async def query_average_cpu_usage(
    container_name: str | None,
    start_time: str,
    end_time: str,
    *,
    match_mode: str | None = RESOURCE_QUERY_MODE_EXACT,
    targets: list[str] | None = None,
) -> float | None:
    """
    Query Prometheus for average CPU usage during a time range.
    When multiple targets are matched, their CPU usage is summed per timestamp first.
    Returns CPU usage in core-equivalent units.
    """
    try:
        resolved_mode, resolved_targets = _resolve_query_targets(
            container_name, match_mode, targets
        )
        query = _build_range_query(
            "container_cpu_usage",
            resolved_mode,
            resolved_targets,
        )
        values = await _query_range_series(query, start_time, end_time, "1s")
        if not values:
            LOGGER.warning(f"No CPU metrics found for targets {resolved_targets}")
            return None
        return round(sum(values) / len(values), 10)
    except Exception as exc:
        LOGGER.error(f"Error querying CPU metrics: {exc}")
        return None


async def query_average_memory_usage(
    container_name: str | None,
    start_time: str,
    end_time: str,
    *,
    match_mode: str | None = RESOURCE_QUERY_MODE_EXACT,
    targets: list[str] | None = None,
) -> float | None:
    """
    Query Prometheus for average memory usage during a time range.
    When multiple targets are matched, their memory usage is summed per timestamp first.
    Returns memory usage in MB.
    """
    try:
        resolved_mode, resolved_targets = _resolve_query_targets(
            container_name, match_mode, targets
        )
        query = _build_range_query(
            "container_memory_usage_bytes",
            resolved_mode,
            resolved_targets,
            convert_to_mb=True,
        )
        values = await _query_range_series(query, start_time, end_time, "1s")
        if not values:
            LOGGER.warning(f"No memory metrics found for targets {resolved_targets}")
            return None
        return round(sum(values) / len(values), 2)
    except Exception as exc:
        LOGGER.error(f"Error querying memory metrics: {exc}")
        return None


async def query_current_cpu_usage(container_name: str) -> float | None:
    """
    Query Prometheus for current CPU usage of a container.
    Returns CPU usage in core-equivalent units.
    """
    try:
        prometheus_url = _normalize_prometheus_url()
        if not prometheus_url:
            LOGGER.warning("PROMETHEUS_URL not set, cannot query current CPU usage")
            return None

        query = f'container_cpu_usage{{name="{container_name}"}}'

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=5.0,
            )

            if response.status_code != 200:
                return None

            data = response.json()
            results = data.get("data", {}).get("result", [])
            if not results:
                return 0.0

            value = float(results[0].get("value", [0, 0])[1])
            return round(value, 4)
    except Exception as exc:
        LOGGER.error(f"Error querying current CPU metrics: {exc}")
        return None


async def query_current_memory_usage(container_name: str) -> float | None:
    """
    Query Prometheus for current memory usage of a container.
    Returns memory usage in MB.
    """
    try:
        prometheus_url = _normalize_prometheus_url()
        if not prometheus_url:
            LOGGER.warning("PROMETHEUS_URL not set, cannot query current memory usage")
            return None

        query = f'container_memory_usage_bytes{{name="{container_name}"}} / 1024 / 1024'

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=5.0,
            )

            if response.status_code != 200:
                return None

            data = response.json()
            results = data.get("data", {}).get("result", [])
            if not results:
                return 0.0

            value = float(results[0].get("value", [0, 0])[1])
            return round(value, 2)
    except Exception as exc:
        LOGGER.error(f"Error querying current memory metrics: {exc}")
        return None


async def query_cpu_usage_series(
    container_name: str | None,
    start_time: str,
    end_time: str,
    *,
    match_mode: str | None = RESOURCE_QUERY_MODE_EXACT,
    targets: list[str] | None = None,
) -> list[float]:
    """
    Query Prometheus for CPU usage samples during a time range.
    When multiple targets are matched, their CPU usage is summed per timestamp first.
    Returns CPU usage in core-equivalent units.
    """
    try:
        resolved_mode, resolved_targets = _resolve_query_targets(
            container_name, match_mode, targets
        )
        query = _build_range_query(
            "container_cpu_usage",
            resolved_mode,
            resolved_targets,
        )
        return await _query_range_series(query, start_time, end_time, "2s")
    except Exception as exc:
        LOGGER.error(f"Error querying CPU series: {exc}")
        return []


async def query_memory_usage_series(
    container_name: str | None,
    start_time: str,
    end_time: str,
    *,
    match_mode: str | None = RESOURCE_QUERY_MODE_EXACT,
    targets: list[str] | None = None,
) -> list[float]:
    """
    Query Prometheus for memory usage samples during a time range.
    When multiple targets are matched, their memory usage is summed per timestamp first.
    Returns memory usage in MB.
    """
    try:
        resolved_mode, resolved_targets = _resolve_query_targets(
            container_name, match_mode, targets
        )
        query = _build_range_query(
            "container_memory_usage_bytes",
            resolved_mode,
            resolved_targets,
            convert_to_mb=True,
        )
        return await _query_range_series(query, start_time, end_time, "2s")
    except Exception as exc:
        LOGGER.error(f"Error querying memory series: {exc}")
        return []
