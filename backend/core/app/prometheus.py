from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import os
from .bicep_utils.models.ids_base import Alert



async def push_metrics_to_prometheus(data, container_name: str, ensemble_name: str=None):
    prometheusUrl = os.environ.get('PROMETHEUS_URL')
    registry = CollectorRegistry()
    cpu_gauge = Gauge('container_cpu_usage', 'CPU usage of the container', ['container', 'ensemble'], registry=registry)
    memory_gauge = Gauge('container_memory_usage', 'Memory usage of the container', ['container', 'ensemble'], registry=registry)

    cpu_gauge.labels(container=container_name, ensemble=ensemble_name).set(data["cpu_usage"])
    memory_gauge.labels(container=container_name, ensemble=ensemble_name).set(data["memory_usage"])
            
    push_to_gateway(prometheusUrl, job='container_metrics', registry=registry)

# TODO add dataset name
async def push_evaluation_metrics_to_prometheus(metrics: dict, container_name: str, ensemble_name: str=None):
    prometheusUrl = os.environ.get('PROMETHEUS_URL')
    registry = CollectorRegistry()
    for k,v in metrics.items():
        Gauge(k, k, ['metric', 'container', 'ensemble'], registry=registry).labels(container=container_name, ensemble=ensemble_name, metric="alert-metrics").set(v)
        
                
    push_to_gateway(prometheusUrl, job='alert_metrics', registry=registry)