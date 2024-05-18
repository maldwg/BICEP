from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import os

prometheusUrl = os.environ.get('PROMETHEUS_URL')


registry = CollectorRegistry()

g = Gauge('job_last_success_unixtime', 'Last time a batch job successfully finished', registry=registry)

g.set_to_current_time()

push_to_gateway(prometheusUrl, job='batchA', registry=registry)