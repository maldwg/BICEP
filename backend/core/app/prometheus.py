from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import os
from .bicep_utils.models.ids_base import Alert
import logging

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)



# TODO 10 : refactor metrics to be not started or stopped by container setup/removal but have a permanent endpoint or background task ha ndle the job
async def push_metrics_to_prometheus(data, container_name: str):
    prometheusUrl = os.environ.get('PROMETHEUS_URL')
    registry = CollectorRegistry()
    cpu_gauge = Gauge('container_cpu_usage', 'CPU usage of the container', ['display_name','container'], registry=registry)
    memory_gauge = Gauge('container_memory_usage', 'Memory usage of the container', ['display_name','container'], registry=registry)
    cpu_gauge.labels(display_name=container_name,container=container_name).set(data["cpu_usage"])
    memory_gauge.labels(display_name=container_name, container=container_name).set(data["memory_usage"])
    job_name=f"{container_name}_metrics"
    response = push_to_gateway(prometheusUrl, job=job_name, registry=registry)

async def push_evaluation_metrics_to_prometheus(metrics: dict, container_name: str=None, ensemble_name: str=None, dataset_name: str = None):
    prometheusUrl = os.environ.get('PROMETHEUS_URL')
    registry = CollectorRegistry()
    for k,v in metrics.items():
        if ensemble_name:
            display_name = ensemble_name
            Gauge(k, k, ['metric', 'display_name','container', 'ensemble', 'dataset'], registry=registry).labels(display_name=display_name,container=container_name, ensemble=ensemble_name, dataset=dataset_name, metric="alert-metrics").set(v)
        else:
            display_name = container_name
            Gauge(k, k, ['metric', 'display_name','container', 'ensemble', 'dataset'], registry=registry).labels(display_name=display_name,container=container_name, ensemble=ensemble_name, dataset=dataset_name, metric="alert-metrics").set(v)
    job_name=f"{display_name}_alert_metrics"
    push_to_gateway(prometheusUrl, job=job_name, registry=registry)