import asyncio
import aiofiles
from http.client import HTTPResponse
import socket
from contextlib import closing
from enum import Enum
import os
from app.models.benchmarking import (
    BenchmarkingResult,
    add_benchmarking_result,
    BenchmarkingResultTransferObject,
)
import httpx
from fastapi import Response, Request
from app.models.dataset import Dataset, add_dataset
from app.bicep_utils.models.ids_base import Alert
from dateutil import parser
import shutil
from app.database import SessionLocal
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from app.logger import LOGGER
from abc import ABC, abstractmethod
from app.metrics import calculate_evaluation_metrics
from app.models.dataset import get_dataset_by_id
from app.prometheus import query_average_cpu_usage, query_average_memory_usage
import json
dataset_addition_tasks = set()

class Precision(ABC):
    @property
    @abstractmethod
    def timestamp_format(self):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def replace_unnecessary_timestamp_values(self, timestamp: datetime) -> datetime:
        pass

    @abstractmethod
    def calculate_timestamps_with_tolerance(
        self, timestamp: datetime, tolerance_unit: int = 1
    ) -> list[datetime]:
        pass

    def trim_datetime_timestamp_to_str(self, timestamp: datetime) -> str:
        replaced_timestamp = self.replace_unnecessary_timestamp_values(timestamp)
        return replaced_timestamp.strftime(self.timestamp_format)


class HourPrecision(Precision):
    # hour precision technically does not make sense and should be converted to minnutes anyway...
    timestamp_format = "%Y-%m-%dT%H:%M"
    name = "hour"

    def replace_unnecessary_timestamp_values(self, timestamp):
        return timestamp.replace(second=0, microsecond=0)

    def calculate_timestamps_with_tolerance(self, timestamp, tolerance_unit=1):
        timestamp_replaced = self.replace_unnecessary_timestamp_values(timestamp)
        return [
            timestamp_replaced + timedelta(minutes=offset)
            for offset in range(-tolerance_unit, tolerance_unit + 1)
        ]


class MinutePrecision(Precision):
    timestamp_format = "%Y-%m-%dT%H:%M"
    name = "minute"

    def replace_unnecessary_timestamp_values(self, timestamp):
        return timestamp.replace(second=0, microsecond=0)

    def calculate_timestamps_with_tolerance(self, timestamp, tolerance_unit=1):
        timestamp_replaced = self.replace_unnecessary_timestamp_values(timestamp)
        return [
            timestamp_replaced + timedelta(minutes=offset)
            for offset in range(-tolerance_unit, tolerance_unit + 1)
        ]


class SecondPrecision(Precision):
    timestamp_format = "%Y-%m-%dT%H:%M:%S"
    name = "second"

    def replace_unnecessary_timestamp_values(self, timestamp):
        return timestamp.replace(microsecond=0)

    def calculate_timestamps_with_tolerance(self, timestamp, tolerance_unit=1):
        timestamp_replaced = self.replace_unnecessary_timestamp_values(timestamp)
        return [
            timestamp_replaced + timedelta(seconds=offset)
            for offset in range(-tolerance_unit, tolerance_unit + 1)
        ]


class MilisecondPrecision(Precision):
    # miliseconds precision is too precise and deviations between labels file and traffic are likely, therefor downsample to seconds
    timestamp_format = "%Y-%m-%dT%H:%M:%S"
    name = "milisecond"

    def replace_unnecessary_timestamp_values(self, timestamp):
        return timestamp.replace(microsecond=0)

    def calculate_timestamps_with_tolerance(self, timestamp, tolerance_unit=1):
        timestamp_replaced = self.replace_unnecessary_timestamp_values(timestamp)
        return [
            timestamp_replaced + timedelta(seconds=offset)
            for offset in range(-tolerance_unit, tolerance_unit + 1)
        ]


def get_precision_by_name(name: str):
    match name:
        case "hour":
            return HourPrecision()
        case "minute":
            return MinutePrecision()
        case "second":
            return SecondPrecision()
        case "milisecond":
            return MilisecondPrecision()
        case _:
            return None


# class Precision(Enum):
#     HOUR = "hour"
#     MINUTE = "minute"
#     SECOND = "second"
#     MILISECOND = "milisecond"


class STATUS(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    SETTING_UP = "setting-up"


class ANALYSIS_STATUS(Enum):
    LOGS_SENT = "LOGS_SENT"
    PROCESSING = "PROCESSING"
    IDLE = "IDLE"


class FILE_TYPES(Enum):
    CONFIG = "configuration"
    TEST_DATA = "test-data"
    RULE_SET = "rule-set"


class DOCKER_HOST_STATUS(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


def file_type_is_accepted(file_type: str, file_ending: str):
    match file_type:
        case FILE_TYPES.CONFIG.value:
            return True if file_ending in ["lua", "yaml", "xml", "conf"] else False
        case FILE_TYPES.TEST_DATA.value:
            return True if file_ending in ["pcap", "csv"] else False
        case FILE_TYPES.RULE_SET.value:
            return True if file_ending in ["rules"] else False
    return False


def find_free_port():
    # TODO 10: Adapt this to also find free ports on remote hosts --> could be hard
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def get_core_host_ip():
    return os.popen("/sbin/ip route|awk '/default/ { print $3 }'").read().strip()


def get_core_url():
    core_ip = get_core_host_ip()
    port = os.getenv("EXTERNAL_FASTAPI_PORT")
    return f"http://{core_ip}:{port}"


async def deregister_container_from_ensemble(container):
    container_url = container.get_container_http_url()
    endpoint = f"/configure/ensemble/remove"
    async with httpx.AsyncClient() as client:
        response: HTTPResponse = await client.post(container_url + endpoint)

    return response


def create_response_message(message: str, status_code: int):
    return Response(content=f'{{ "message": "{message}" }}', status_code=status_code)


def create_response_error(message: str, status_code: int):
    return Response(content=f'{{ "error": "{message}" }}', status_code=status_code)


def create_generic_response_message_for_ensemble(message: str, status_code: int):
    return {"content": message, "status_code": status_code}


async def start_static_analysis(container, form_data, dataset):
    endpoint = "/analysis/static"
    container_url = container.get_container_http_url()

    async def send_request_in_background():
        try:
            async with httpx.AsyncClient() as client:
                with open(dataset.data_file_path, "rb") as f:
                    form_data["dataset"] = (dataset.name, f, "application/octet-stream")
                    # set timeout to 600 seconds, as uploads can take a while
                    response = await client.post(
                        container_url + endpoint, files=form_data, timeout=180
                    )
                    response.raise_for_status()
        except Exception as e:
            LOGGER.error(e)

    task = asyncio.create_task(send_request_in_background())
    return JSONResponse(
        content={"message": "Successfully sending data in the background"},
        status_code=200,
    )


async def start_network_analysis(container, data):
    endpoint = "/analysis/network"
    container_url = container.get_container_http_url()
    LOGGER.debug(f"Sending network analysis request to {container_url + endpoint} with data: {data}")
    async with httpx.AsyncClient() as client:
        response = await client.post(container_url + endpoint, json=data)
    return response


async def stop_analysis(container):
    container_url = container.get_container_http_url()
    endpoint = "/analysis/stop"
    async with httpx.AsyncClient() as client:
        response: HTTPResponse = await client.post(container_url + endpoint)
    return response


async def parse_response_for_triggered_analysis(
    response: HTTPResponse, container, analysis_type: str, ensemble_id: int = None
):
    if response.status_code == 200:
        message = f"container {container.id} - {analysis_type} analysis triggered"
        if ensemble_id != None:
            message = f"container {container.id} - {analysis_type} analysis for ensemble {ensemble_id} triggered"
        parsed_response = create_response_message(message, 200)
    else:
        message = f"container {container.id} - {analysis_type} analysis could not be triggered"
        if ensemble_id != None:
            message = f"container {container.id} - {analysis_type} analysis for ensemble {ensemble_id} could not be triggered"
        parsed_response = create_response_error(message, 500)
    return parsed_response


async def calculate_and_add_dataset(
    data_file_path, labels_file_path, name, description, dataset_type, db
):
    benign, malicious = await dataset_type.get_benign_and_malicious_counts(
        labels_file_path
    )
    precision = await dataset_type.calculate_precision(labels_file_path)

    dataset = Dataset(
        name=name,
        description=description,
        data_file_path=data_file_path,
        labels_file_path=labels_file_path,
        ammount_benign=benign,
        ammount_malicious=malicious,
        dataset_type_id=dataset_type.id,
        timestamp_precision=precision.name,
    )
    await add_dataset(db, dataset)


async def save_file_to_disk(file, path):
    with open(path, "wb") as f:
        f.write(file)


async def remove_directory(path):
    try:
        shutil.rmtree(path)
    except Exception as e:
        LOGGER.error(e)


async def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_item_counts_of_dict(d: dict):
    """
    Method that returns the ammount of items stored in a dict, regardless of the keys
    """
    items = 0
    for _, v in d.items():
        items += len(v)
    return items


async def calculate_evaluation_metrics_and_push(
    db,
    benchmarking_results: BenchmarkingResultTransferObject,
    container_name: str = None,
    ensemble_name: str = None,
    configuration_name: str = None,
    ruleset_name: str = None,
    ensemble_technique_name: str = None,
):

    # necessary to only pass the id here, as otherwise the db context will be closed on the next function call
    # and an error will be thrown
    dataset = await get_dataset_by_id(db, benchmarking_results.dataset_id)
    metrics = await calculate_evaluation_metrics(
        db, benchmarking_results.dataset_id, benchmarking_results.alerts
    )
    LOGGER.info(
        f"container {container_name} for enesemble {ensemble_name} got metrics {metrics}"
    )

    # Query resource usage metrics from Prometheus
    avg_cpu = None
    avg_memory = None
    if container_name:
        try:
            avg_cpu = await query_average_cpu_usage(
                container_name,
                benchmarking_results.start_time,
                benchmarking_results.stop_time,
            )
            avg_memory = await query_average_memory_usage(
                container_name,
                benchmarking_results.start_time,
                benchmarking_results.stop_time,
            )
            LOGGER.info(
                f"Resource metrics for {container_name}: CPU={avg_cpu}%, Memory={avg_memory}MB"
            )
        except Exception as e:
            LOGGER.error(f"Failed to query resource metrics: {e}")

    result = BenchmarkingResult(
        dataset_name=dataset.name,
        ids_name=container_name if container_name else ensemble_name,
        ensembling_method=ensemble_technique_name if ensemble_technique_name else "",
        configuration_name=configuration_name,
        ruleset_name=ruleset_name,
        start_time=benchmarking_results.start_time,
        stop_time=benchmarking_results.stop_time,
        runtime=benchmarking_results.runtime,
        acc=metrics["ACCURACY"],
        fpr=metrics["FPR"],
        fnr=metrics["FNR"],
        fdr=metrics["FDR"],
        prec=metrics["PRECISION"],
        detection_rate=metrics["DR"],
        f1_score=metrics["F_SCORE"],
        avg_cpu_usage=avg_cpu,
        avg_memory_usage=avg_memory,
    )
    await add_benchmarking_result(db, result)
    await db.close()


def extract_ts_srcip_srcport_dstip_dstport_from_alert(
    alert: Alert, precision: Precision = MilisecondPrecision()
):
    source_ip = alert.source_ip.strip()
    source_port = alert.source_port.strip()
    destination_ip = alert.destination_ip.strip()
    destination_port = alert.destination_port.strip()
    timestamp = normalize_and_parse_alert_timestamp(alert.time, precision=precision)
    timestamp = timestamp.strip()
    return timestamp, source_ip, source_port, destination_ip, destination_port


def normalize_and_parse_alert_timestamp(
    timestamp_str, precision: Precision = MilisecondPrecision()
) -> str:
    """
    Method to normalize timestamp formats, as these can differ from dataset to dataset
    Returns a normalized timestamp according to the ds precision
    """

    timestamp = parser.parse(timestamp_str).replace(tzinfo=None)
    parsed_timestamp_string = precision.trim_datetime_timestamp_to_str(timestamp)
    return parsed_timestamp_string


def get_length_of_nested_dict(d: dict):
    counter = 0
    for k, v in d.items():
        for container, alerts in v.items():
            counter += len(alerts)
    return counter


async def read_data_file(file_path):
    async with aiofiles.open(file_path, "rb") as file:
        data_file = await file.read()
        return data_file


def directory_is_empty(path):
    if os.path.isdir(path):
        return True if len(os.listdir(path)) == 0 else False
    else:
        return True


async def finish_ids_setup(ids_system_id: int, cids_configurations, env_vars) -> None:
    # local import to avoid circular imports
    from app.models.ids_system import get_ids_system_by_id
    
    async with SessionLocal() as db:
        ids_system = await get_ids_system_by_id(db, ids_system_id)
        if ids_system is None:
            LOGGER.error(f"Background setup failed: IDS system {ids_system_id} was not found.")
            return

        try:
            await ids_system.setup(
                db,
                cids_configurations=cids_configurations,
                env_vars=env_vars,
            )
        except Exception as exc:
            LOGGER.error(f"Background setup failed for IDS system {ids_system_id}: {exc}")
