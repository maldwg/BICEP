import asyncio
import json
import docker
from .utils import get_core_host
import time
import httpx

from requests.models import Response
from .prometheus import push_metrics_to_prometheus

def get_docker_client(host_system):
    if "Core" in host_system.name or host_system.host == "localhost":
         core_host = get_core_host()
         host_url = f"tcp://{core_host}:{host_system.docker_port}"
    else: 
        host_url = f"tcp://{host_system.host}:{host_system.docker_port}"
    try:
        client = docker.DockerClient(base_url=host_url)
    except Exception as e:
        print(e)
        raise(Exception(f"Could not create a docker client for url {host_url} \n Try to use an IP instead of hostname"))
    return client

async def start_docker_container(ids_container, ids_tool, config, ruleset):
    core_ip = get_core_host()
    core_url = f"http://{core_ip}:8000" 
    client = get_docker_client(ids_container.host_system)

    # ensure image is present 
    # TODO 0: docker needs longer or cant take it at all when image needs to be pulled. solution ?
    # TODO: 0 activate this again for prod to ensure the image is pulled. For local tests deactivate that
    # TODO 0: more spohisticated solution maybe with env variables to be abl to pull or use image locally if needed by cgheckoing ewith the dokcer sdk if image is present
    # await pull_image_async(client, ids_properties.image)
    await run_container_async(client=client, container=ids_container, ids_tool=ids_tool, url=core_url)
    await check_container_health(ids_container)
    await inject_config(ids_container, config)
    if ruleset != None:
        await inject_ruleset(ids_container, ruleset)
    client.close()

async def pull_image_async(client, image):
    await asyncio.to_thread(client.images.pull, image)

async def run_container_async(client, ids_tool, container, url):
    image_name_and_version = f"{ids_tool.image_name}:{ids_tool.image_tag}"
    await asyncio.to_thread(
        client.containers.run, 
        image=image_name_and_version,
        name=container.name,
        network_mode="host",
        environment={
            "PORT": container.port,
            "CORE_URL": url,
            "TZ": "UTC"
        },
        cap_add=["NET_ADMIN", "NET_RAW"],
        detach=True  
        )
    

async def inject_config(ids_container, config):
    container_url = ids_container.get_container_http_url()
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
    container_url = ids_container.get_container_http_url()
    endpoint = "/ruleset"
    print(f"debug: {container_url}{endpoint}")
    async with httpx.AsyncClient() as client:
        file={"file": (config.name, config.configuration)}
        response = await client.post(container_url+endpoint,files=file)
    return response

async def remove_docker_container(ids_container):
    client = get_docker_client(ids_container.host_system)
    container = client.containers.get(container_id=ids_container.name)
    container.stop()
    container.remove()
    client.close()
    

async def check_container_health(ids_container, timeout=60):
    start_time = time.time()
    container_url = ids_container.get_container_http_url()
    print(container_url)
    url = f"{container_url}/healthcheck"
    print(url)
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
            await remove_docker_container(ids_container)
            return False
        time.sleep(1)

async def start_metric_stream(container, interval=1.0):
    try:
        client = get_docker_client(container.host_system)
        container = client.containers.get(container_id=container.name)
        for stats_bytes in container.stats(stream=True):
            stats_decoded = stats_bytes.decode("utf-8")
            stats = json.loads(stats_decoded)
            try:
                cpu_usage = await calculate_cpu_usage(stats) 
                memory_usage = await calculate_memory_usage(stats)
            except KeyError as e:
                # Keyerrors occur on every 1st iteration as tehre is not pre_cpu statistic yet
                continue            
            stat = {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
            }
            await push_metrics_to_prometheus(stat, container.name)
            await asyncio.sleep(interval)

    except asyncio.CancelledError as e:
        print(f"Task for sending metrics for container {container.name} was cancelled successfully")

async def stop_metric_stream(task_id, stream_metric_tasks, container):
    try:
        task = stream_metric_tasks[task_id]
        task.cancel()
        # push a last time to pomtheus the values None, so that there is no continuous timeline for the metrics
        stats = {
            "cpu_usage": -1,
            "memory_usage": -1
        }
        await push_metrics_to_prometheus(stats, container.name)
    except Exception as e:
        print(f"ID {task_id} for metric collection could not be found, skiping cancellation and proceeding")
        print(e)


async def calculate_memory_usage(stats) -> float:
    memory_usage_bytes = stats['memory_stats']['usage']
    memory_usage_mb = memory_usage_bytes / (1024 * 1024)
    return round(memory_usage_mb, 2)

async def calculate_cpu_usage(stats) -> float:
    UsageDelta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
    SystemDelta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
    len_cpu = len(stats['cpu_stats']['cpu_usage']['percpu_usage'])
    percentage_total = (UsageDelta / SystemDelta) * len_cpu * 100
    available_cpus = stats['precpu_stats']['online_cpus']
    percentage = percentage_total / available_cpus
    return round(percentage, 2)