import docker
import os 
from .utils import Suricata, Slips



def get_docker_client(host: str, port: int = 2375):
    if host == "localhost":
        host_ip = os.popen("/sbin/ip route|awk '/default/ { print $3 }'").read().strip()
        host_url = f"tcp://{host_ip}:2375"
        client = docker.DockerClient(base_url=host_url)
    else:
        host_url = f"tcp://{host}:{str(port)}"
        client = docker.DockerClient(base_url=host_url)
    return client

async def start_docker_container(ids_container, ids_tool, config):
    client = get_docker_client(ids_container.host)
    if ids_tool.name == Slips.name:
        ids_properties = Slips()
    elif ids_tool.name == Suricata.name:
        ids_properties = Suricata()
    print(ids_properties)
    client.containers.run(
        image=ids_properties.image,
        name=ids_container.name,
        # healthcheck="NONE",
        ports={'80/tcp': ids_container.port},
        detach=True
    )
    await inject_config(ids_container, config, ids_properties)
    client.close()

async def inject_config(ids_container, config, properties):
    if properties.name == Suricata.name:
        file_path = "/tmp/suricata.yaml"
        write_file(config.configuration, file_path )
        await send_file_to_container(file_path, ids_container.name, properties.config_path)
    elif properties.name == Slips.name:
        file_path = "/tmp/slips.yaml"
        write_file(config.configuration, file_path)
        await send_file_to_container(file_path, ids_container.name, properties.config_path)

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
    