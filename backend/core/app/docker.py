import docker
from .utils import Suricata, Slips, get_container_host, get_core_host
import time
import httpx
from requests.models import Response


# TODO: make docker async

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
    client.containers.run(
        image=ids_properties.image,
        name=ids_container.name,
        network_mode="host",
        environment={
            "PORT": ids_container.port,
            "CORE_URL": core_url
        },
        cap_add=["NET_ADMIN", "NET_RAW"],
        detach=True
    )
    await check_container_health(ids_container)
    await inject_config(ids_container, config)
    if ruleset != None:
        await inject_ruleset(ids_container, ruleset)
    client.close()

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
        print(response)
        
async def inject_ruleset(ids_container, config):
    host = get_container_host(ids_container)
    container_url = f"http://{host}:{ids_container.port}"
    endpoint = "/ruleset"
    print(f"debug: {container_url}{endpoint}")
    async with httpx.AsyncClient() as client:
        file={"file": (config.name, config.configuration)}
        response = await client.post(container_url+endpoint,files=file)
        print(response)
    
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