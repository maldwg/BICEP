from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import os
from .bicep_utils.models.ids_base import Alert


async def push_metrics_to_prometheus(data, container_name: str, ensemble_name: str=None):
    prometheusUrl = os.environ.get('PROMETHEUS_URL')
    registry = CollectorRegistry()
    cpu_gauge = Gauge('container_cpu_usage', 'CPU usage of the container', ['display_name','container', 'ensemble'], registry=registry)
    memory_gauge = Gauge('container_memory_usage', 'Memory usage of the container', ['display_name','container', 'ensemble'], registry=registry)

    cpu_gauge.labels(display_name=container_name,container=container_name, ensemble=ensemble_name).set(data["cpu_usage"])
    memory_gauge.labels(display_name=container_name, container=container_name, ensemble=ensemble_name).set(data["memory_usage"])
            
    push_to_gateway(prometheusUrl, job='container_metrics', registry=registry)

async def push_evaluation_metrics_to_prometheus(metrics: dict, container_name: str=None, ensemble_name: str=None, dataset_name: str = None):
    prometheusUrl = os.environ.get('PROMETHEUS_URL')
    registry = CollectorRegistry()
    for k,v in metrics.items():
        if ensemble_name:
            Gauge(k, k, ['metric', 'display_name','container', 'ensemble', 'dataset'], registry=registry).labels(display_name=ensemble_name,container=container_name, ensemble=ensemble_name, dataset=dataset_name, metric="alert-metrics").set(v)
        else:
            Gauge(k, k, ['metric', 'display_name','container', 'ensemble', 'dataset'], registry=registry).labels(display_name=container_name,container=container_name, ensemble=ensemble_name, dataset=dataset_name, metric="alert-metrics").set(v)
                
    push_to_gateway(prometheusUrl, job='alert_metrics', registry=registry)