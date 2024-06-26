from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import os




async def push_metrics_to_prometheus(data, container_name: str, ensemble_name: str=None):
    prometheusUrl = os.environ.get('PROMETHEUS_URL')
    registry = CollectorRegistry()
    cpu_gauge = Gauge('container_cpu_usage', 'CPU usage of the container', ['container', 'ensemble'], registry=registry)
    memory_gauge = Gauge('container_memory_usage', 'Memory usage of the container', ['container', 'ensemble'], registry=registry)

    cpu_gauge.labels(container=container_name, ensemble=ensemble_name).set(data["cpu_usage"])
    memory_gauge.labels(container=container_name, ensemble=ensemble_name).set(data["memory_usage"])
            
    push_to_gateway(prometheusUrl, job='container_metrics', registry=registry)

