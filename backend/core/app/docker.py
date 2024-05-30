import docker
import os 
from .utils import Suricata, Slips
import time
import httpx
from requests.models import Response

def get_core_host():
    return os.popen("/sbin/ip route|awk '/default/ { print $3 }'").read().strip()

def get_container_host(ids_container):
    if ids_container.host != "localhost":
        return ids_container.host
    else:
        return get_core_host()

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
            "PORT": ids_container.port
        },
        detach=True
    )
    await check_container_health(ids_container)
    await inject_config(ids_container, config, ids_properties)
    if ruleset != None:
        await inject_ruleset(ids_container, ruleset, ids_properties)
    client.close()

# TODO: ids_tool needs path for config and optional for ruleset
async def inject_config(ids_container, config, properties):
    host = get_container_host(ids_container)
    container_url = f"http://{host}:{ids_container.port}"
    endpoint = "/configuration"
    print(f"debug: {container_url}{endpoint}")
    async with httpx.AsyncClient() as client:
        file={"file": (config.name, config.configuration)}
        response = await client.post(container_url+endpoint,files=file)
        print(response)
        


async def inject_ruleset(ids_container, config, properties):
    pass


def write_file(content, path):
    with open(path, "wb") as output_file:
        output_file.write(content)

async def send_file_to_container(src_path, container_name, dest_path):
    # TODO: docker command wont work, use fatapi endpoint to send file
    pass

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