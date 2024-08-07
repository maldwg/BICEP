import asyncio
import json
import docker
from .utils import Suricata, Slips, get_container_host, get_core_host, stream_metric_tasks, calculate_cpu_percent
import time
import httpx
import uuid

from requests.models import Response
from .prometheus import push_metrics_to_prometheus

def get_docker_client(host: str, port: int = 2375):
    if host == "localhost":
        host_ip = get_core_host()
        host_url = f"tcp://{host_ip}:2375"
        client = docker.DockerClient(base_url=host_url)
    else:
        host_url = f"tcp://{host}:{str(port)}"
        client = docker.DockerClient(base_url=host_url)
    return client

async def start_docker_container(ids_container, ids_tool, config, ruleset):
    core_ip = get_core_host()
    core_url = f"http://{core_ip}:8000" 
    client = get_docker_client(ids_container.host)
    if ids_tool.name == Slips.name:
        ids_properties = Slips()
    elif ids_tool.name == Suricata.name:
        ids_properties = Suricata()

    # ensure image is present 
    # TODO: 0 activate this again for prod to ensure the image is pulled. For local tests deactivate that
    # await pull_image_async(client, ids_properties.image)
    await run_container_async(client=client, container=ids_container, properties=ids_properties, url=core_url)
    await check_container_health(ids_container)
    await inject_config(ids_container, config)
    if ruleset != None:
        await inject_ruleset(ids_container, ruleset)
    client.close()

async def pull_image_async(client, image):
    await asyncio.to_thread(client.images.pull, image)

async def run_container_async(client, properties, container, url):
    await asyncio.to_thread(
        client.containers.run, 
        image=properties.image,
        name=container.name,
        network_mode="host",
        environment={
            "PORT": container.port,
            "CORE_URL": url
        },
        cap_add=["NET_ADMIN", "NET_RAW"],
        detach=True  
        )

async def inject_config(ids_container, config):
    host = get_container_host(ids_container)
    container_url = f"http://{host}:{ids_container.port}"
    endpoint = "/configuration"
    print(f"debug: {container_url}{endpoint}")
    async with httpx.AsyncClient() as client:
        form_data={
            "file": (config.name, config.configuration, "application/octet-stream"),
            "container_id": (None, str(ids_container.id), "application/json"),
            }
        
        response = await client.post(container_url+endpoint,files=form_data)
        
    return response
async def inject_ruleset(ids_container, config):
    host = get_container_host(ids_container)
    container_url = f"http://{host}:{ids_container.port}"
    endpoint = "/ruleset"
    print(f"debug: {container_url}{endpoint}")
    async with httpx.AsyncClient() as client:
        file={"file": (config.name, config.configuration)}
        response = await client.post(container_url+endpoint,files=file)
    return response

async def remove_docker_container(ids_container):
    client = get_docker_client(ids_container.host)
    container = client.containers.get(container_id=ids_container.name)
    container.stop()
    container.remove()
    client.close()
    

async def check_container_health(ids_container, timeout=60):
    start_time = time.time()
    host = get_container_host(ids_container)
    url = f"http://{host}:{ids_container.port}/healthcheck"
    response = Response()
    response.status_code = 500
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
        except:
            print("Container not ready")
        if response.status_code == 200:
            print(f"Healthcheck for container {url} was sucessful")
            return True
        if time.time() - start_time > timeout:
            print("Container did not become healthy in time.")
            return False
        time.sleep(1)

async def start_metric_stream(container, ensemble_name: str="NaN", interval=10):
    try:
        client = get_docker_client(container.host)
        container = client.containers.get(container_id=container.name)
        for stats_bytes in container.stats(stream=True):
            stats_decoded = stats_bytes.decode("utf-8")
            stats = json.loads(stats_decoded)
            # CPU usage calculation
            # CPU usage calculation
            # TODO 9: CPU uage is not 100% true.... wrong calculation ? which values to trust ? Should i even trust docker stats ? what do i acutally want to dispaly?
            cpu_total_usage = stats['cpu_stats']['cpu_usage']['total_usage']
            system_cpu_usage = stats['cpu_stats']['system_cpu_usage']
            online_cpus = stats['cpu_stats'].get('online_cpus', 1)

            cpu_percentage = (cpu_total_usage / system_cpu_usage) * online_cpus * 100.0

            # Memory usage calculation
            memory_usage_bytes = stats['memory_stats']['usage']
            memory_usage_mb = memory_usage_bytes / (1024 * 1024)  # Convert to MB

            stat = {
                "cpu_usage": cpu_percentage,
                "memory_usage": memory_usage_mb,
            }
            await push_metrics_to_prometheus(stat, container.name, ensemble_name)
            await asyncio.sleep(interval)
    except asyncio.CancelledError as e:
        print("Task was cancelled successfully")

async def stop_metric_stream(task_id):
    try:
        # TODO 10: Cancellation does nothing --> task goes on anyways
        task = stream_metric_tasks[task_id]
        res = task.cancel()
        print(f"Task was canceld? {res}")
    except KeyError as e:
        print(f"ID {task_id} for metric collection could not be found, skiping cancellation and proceeding")
