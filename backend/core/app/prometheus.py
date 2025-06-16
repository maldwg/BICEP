from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import os
from app.bicep_utils.models.ids_base import Alert
import logging
from datetime import datetime
import uuid

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

async def push_evaluation_metrics_to_prometheus(metrics: dict, container_name: str=None, ensemble_name: str=None, dataset_name: str = None):
    timestamp = datetime.now().isoformat()
    prometheusUrl = os.environ.get('PROMETHEUS_URL')
    registry = CollectorRegistry()
    for k,v in metrics.items():
        if ensemble_name:
            display_name = f"{ensemble_name} - {dataset_name}"
            Gauge(k, k, ['metric', 'display_name','container', 'ensemble', 'dataset', 'timestamp'], registry=registry).labels(
                display_name=display_name,
                container=container_name, 
                ensemble=ensemble_name, 
                dataset=dataset_name, 
                metric="alert-metrics",
                timestamp = timestamp
            ).set(v)
        else:
            display_name = f"{container_name} - {dataset_name}"
            Gauge(k, k, ['metric', 'display_name','container', 'ensemble', 'dataset', 'timestamp'], registry=registry).labels(
                display_name=display_name,
                container=container_name, 
                ensemble=ensemble_name,
                dataset=dataset_name, 
                metric="alert-metrics",
                timestamp=timestamp
            ).set(v)
    uid = uuid.uuid4()
    job_name=f"{display_name}_alert_metrics_{uid}"
    push_to_gateway(prometheusUrl, job=job_name, registry=registry)