from app.database import Base, SessionLocal
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import (
    DOCKER_HOST_STATUS,
    METRIC_SERVICE_STATUS,
    get_core_external_ip,
    get_external_prometheus_push_gateway_url,
    get_core_host_ip,
    get_core_url,
    get_prometheus_push_gateway_url,
)
from app.deployment.deployment_plugins.docker import (
    DOCKER_CONTROL_CLIENT_TIMEOUT,
    DOCKER_DEPLOYMENT_CLIENT_TIMEOUT,
    ensure_image_present,
    get_docker_client,
)
from app.logger import LOGGER
import asyncio
import httpx
import os
import random
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
import docker as docker_sdk
from app.models.metric_service import (
    get_metric_service_by_host_id,
    get_or_create_metric_service,
    update_metric_service,
)
METRIC_SERVICE_DEFAULT_IMAGE_NAME = "ghcr.io/bicep-pump/metric-service"
METRIC_SERVICE_DEFAULT_IMAGE_VERSION = "latest"
METRIC_SERVICE_DEFAULT_NAME = "bicep-metric-service"
METRIC_SERVICE_DEFAULT_SCRAPE_INTERVAL = "5"
METRIC_SERVICE_DEFAULT_BATCH_SIZE = "10"
METRIC_SERVICE_DEFAULT_EXPORT_MODE = "prometheus"
METRIC_SERVICE_HEALTHCHECK_PATH = "/health"
METRIC_SERVICE_REGISTRATION_STUCK_TIMEOUT_SECONDS = int(
    os.getenv("METRIC_SERVICE_REGISTRATION_STUCK_TIMEOUT_SECONDS", "45")
)
METRIC_SERVICE_REDEPLOY_TIMEOUT_SECONDS = int(
    os.getenv("METRIC_SERVICE_REDEPLOY_TIMEOUT_SECONDS", "120")
)
METRIC_SERVICE_PORT_RANGE_START = 20000
METRIC_SERVICE_PORT_RANGE_END = 60000
METRIC_SERVICE_PORT_SELECTION_ATTEMPTS = 25
METRIC_SERVICE_DEPLOYMENT_SCHEDULED = "scheduled"
METRIC_SERVICE_DEPLOYMENT_ALREADY_RUNNING = "already_running"
METRIC_SERVICE_DEPLOYMENT_FAILED = "failed"

_metric_service_deployment_tasks: dict[int, asyncio.Task] = {}
_metric_service_unhealthy_since: dict[int, datetime] = {}


class DockerHostSystem(Base):
    __tablename__ = "docker_host_system"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    host = Column(String(1024), nullable=False)
    docker_port = Column(Integer)
    status = Column(String(64))

    container = relationship("IdsSystem", back_populates="host_system", lazy="selectin")
    metric_service = relationship(
        "MetricService",
        back_populates="docker_host_system",
        lazy="selectin",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def get_metric_service_container_name(self) -> str:
        return f"bicep-metric-service-{self.id}"

    def get_metric_service_prometheus_job_name(self) -> str:
        return f"metric_service_host_{self.id}"

    def get_metric_service_image_name(self) -> str:
        return os.environ.get(
            "METRIC_SERVICE_IMAGE_NAME", METRIC_SERVICE_DEFAULT_IMAGE_NAME
        )

    def get_metric_service_image_version(self) -> str:
        return os.environ.get(
            "METRIC_SERVICE_IMAGE_VERSION", METRIC_SERVICE_DEFAULT_IMAGE_VERSION
        )

    def get_metric_service_image(self) -> str:
        return (
            f"{self.get_metric_service_image_name()}:"
            f"{self.get_metric_service_image_version()}"
        )

    def is_core_host(self) -> bool:
        return self.host == "localhost" or "Core" in self.name

    def get_metric_service_core_base_url(self) -> str:
        if self.is_core_host():
            return f"http://127.0.0.1:{os.getenv('EXTERNAL_FASTAPI_PORT', '8000')}"

        return get_core_url()

    def get_metric_service_pushgateway_base_url(self) -> str:
        if self.is_core_host():
            parsed = urlparse(get_prometheus_push_gateway_url())
            scheme = parsed.scheme or "http"
            port = parsed.port or 9091
            path = parsed.path.rstrip("/")
            suffix = path if path else ""
            return f"{scheme}://127.0.0.1:{port}{suffix}"

        return get_external_prometheus_push_gateway_url()

    def get_metric_service_metric_endpoint(self) -> str:
        return (
            f"{self.get_metric_service_pushgateway_base_url()}/metrics/job/"
            f"{self.get_metric_service_prometheus_job_name()}"
        )

    def get_host_and_docker_port(self) -> tuple:
        if self.is_core_host():
            core_host = get_core_host_ip()
            return (core_host, self.docker_port)
        else:
            return (self.host, self.docker_port)

    def resolve_host_aliases(self) -> set[str]:
        aliases = {self.host.lower()}
        accessible_host, _ = self.get_host_and_docker_port()
        aliases.add(accessible_host.lower())
        registration_ip = self.get_metric_service_registration_ip()
        aliases.add(registration_ip.lower())

        if self.host == "localhost":
            aliases.add("127.0.0.1")
            aliases.add("localhost")

        for candidate in {self.host, accessible_host, registration_ip}:
            try:
                _, _, ips = socket.gethostbyname_ex(candidate)
                aliases.update(ip.lower() for ip in ips)
            except Exception:
                continue

        return aliases

    def get_metric_service_registration_ip(self) -> str:
        accessible_host, _ = self.get_host_and_docker_port()

        try:
            _, _, ips = socket.gethostbyname_ex(accessible_host)
            if ips:
                return ips[0]
        except Exception:
            pass

        return accessible_host

    async def get_metric_service_registration_ip_async(self) -> str:
        return await asyncio.to_thread(self.get_metric_service_registration_ip)

    def get_metric_service_registration_endpoint(self) -> str:
        base_endpoint = f"{self.get_metric_service_core_base_url()}/metric-services/register"
        if self.id is None:
            return base_endpoint

        return f"{base_endpoint}/{self.id}"

    async def is_metric_service_port_available(
        self, port: int, timeout: float = 0.5
    ) -> bool:
        host, _ = self.get_host_and_docker_port()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout
            )
        except Exception:
            return True

        writer.close()
        await writer.wait_closed()
        return False

    async def choose_metric_service_port(self) -> int:
        for _ in range(METRIC_SERVICE_PORT_SELECTION_ATTEMPTS):
            candidate = random.randint(
                METRIC_SERVICE_PORT_RANGE_START, METRIC_SERVICE_PORT_RANGE_END
            )
            if await self.is_metric_service_port_available(candidate):
                return candidate

        raise RuntimeError("Could not allocate an available port for the metric service.")

    async def _deploy_metric_service(self, db: AsyncSession):


        metric_service = await get_or_create_metric_service(
            db,
            self.id,
            name=METRIC_SERVICE_DEFAULT_NAME,
            status=METRIC_SERVICE_STATUS.DEPLOYING.value,
            status_message="Metric service missing. Deploying it now.",
        )

        client = get_docker_client(
            self,
            timeout=DOCKER_DEPLOYMENT_CLIENT_TIMEOUT,
        )
        try:
            image_name = self.get_metric_service_image()
            await ensure_image_present(client, image_name)

            selected_port = await self.choose_metric_service_port()
            registration_ip = await self.get_metric_service_registration_ip_async()
            await update_metric_service(
                db,
                metric_service,
                name=METRIC_SERVICE_DEFAULT_NAME,
                port=selected_port,
                status=METRIC_SERVICE_STATUS.DEPLOYING.value,
                status_message="Metric service missing. Deploying it now.",
                clear_registration=True,
            )

            container = await asyncio.to_thread(
                client.containers.create,
                image=image_name,
                name=self.get_metric_service_container_name(),
                network_mode="host",
                privileged=True,
                cap_add=["SYS_ADMIN"],
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                volumes={
                    "/var/run/docker.sock": {
                        "bind": "/var/run/docker.sock",
                        "mode": "ro",
                    },
                    "/sys/fs/cgroup": {
                        "bind": "/sys/fs/cgroup",
                        "mode": "ro",
                    },
                },
                labels={
                    "bicep.metric-service": "true",
                    "bicep.host-id": str(self.id),
                },
                environment={
                    "METRIC_EXPORT_MODE": METRIC_SERVICE_DEFAULT_EXPORT_MODE,
                    "METRIC_ENDPOINT": self.get_metric_service_metric_endpoint(),
                    "REGISTRATION_ENDPOINT": self.get_metric_service_registration_endpoint(),
                    "SCRAPE_INTERVAL": METRIC_SERVICE_DEFAULT_SCRAPE_INTERVAL,
                    "BATCH_SIZE": METRIC_SERVICE_DEFAULT_BATCH_SIZE,
                    "SERVICE_NAME": METRIC_SERVICE_DEFAULT_NAME,
                    "SERVICE_PORT": str(selected_port),
                    "SERVICE_IP": registration_ip,
                },
            )
            await asyncio.to_thread(container.start)

            await update_metric_service(
                db,
                metric_service,
                name=METRIC_SERVICE_DEFAULT_NAME,
                port=selected_port,
                status=METRIC_SERVICE_STATUS.REGISTERING.value,
                status_message="Metric service deployed. Waiting for registration.",
            )
        except Exception as exc:
            await update_metric_service(
                db,
                metric_service,
                status=METRIC_SERVICE_STATUS.UNAVAILABLE.value,
                status_message=f"Metric service deployment failed: {exc}",
            )
            LOGGER.error(f"Failed to deploy metric service on {self.name}: {exc}")
        finally:
            client.close()

    def _ensure_metric_service_deployment_task(self) -> str:
        if self.id is None or SessionLocal is None:
            LOGGER.error(
                "Could not schedule metric service deployment for host %s.",
                self.name,
            )
            return METRIC_SERVICE_DEPLOYMENT_FAILED

        existing_task = _metric_service_deployment_tasks.get(self.id)
        if existing_task is not None:
            if not existing_task.done():
                return METRIC_SERVICE_DEPLOYMENT_ALREADY_RUNNING
            _metric_service_deployment_tasks.pop(self.id, None)

        host_snapshot = DockerHostSystem(
            id=self.id,
            name=self.name,
            host=self.host,
            docker_port=self.docker_port,
            status=self.status,
        )

        async def run_deployment() -> None:
            db = SessionLocal()
            try:
                await host_snapshot._deploy_metric_service(db)
            except Exception as exc:
                LOGGER.error(
                    "Background metric service deployment failed on %s: %s",
                    self.name,
                    exc,
                )
            finally:
                await db.close()
                _metric_service_deployment_tasks.pop(self.id, None)

        _metric_service_deployment_tasks[self.id] = asyncio.create_task(
            run_deployment(),
            name=f"metric-service-deploy-{self.id}",
        )
        return METRIC_SERVICE_DEPLOYMENT_SCHEDULED

    async def _mark_metric_service_unavailable(
        self, db: AsyncSession | None, message: str
    ) -> None:
        if db is None or self.id is None:
            return

        metric_service = await get_or_create_metric_service(
            db,
            self.id,
            name=METRIC_SERVICE_DEFAULT_NAME,
            status=METRIC_SERVICE_STATUS.UNAVAILABLE.value,
            status_message=message,
        )
        await update_metric_service(
            db,
            metric_service,
            status=METRIC_SERVICE_STATUS.UNAVAILABLE.value,
            status_message=message,
        )

    async def _metric_service_healthcheck(self, ip: str, port: int) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(
                    f"http://{ip}:{port}{METRIC_SERVICE_HEALTHCHECK_PATH}"
                )
            return response.status_code == 200
        except Exception:
            return False

    def _get_metric_service_started_at(self, state: dict) -> datetime | None:
        started_at = state.get("StartedAt")
        if not started_at or started_at.startswith("0001-01-01"):
            return None

        try:
            return datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except ValueError:
            LOGGER.warning(
                "Could not parse metric service StartedAt timestamp for host %s: %s",
                self.name,
                started_at,
            )
            return None

    def _is_metric_service_registration_stuck(self, state: dict) -> bool:
        started_at = self._get_metric_service_started_at(state)
        if started_at is None:
            return False

        runtime_seconds = (
            datetime.now(timezone.utc) - started_at.astimezone(timezone.utc)
        ).total_seconds()
        return (
            runtime_seconds >= METRIC_SERVICE_REGISTRATION_STUCK_TIMEOUT_SECONDS
        )

    def _should_redeploy_metric_service(self, state: dict, metric_service) -> bool:
        if metric_service.last_registration_at:
            return False

        started_at = self._get_metric_service_started_at(state)
        if started_at is None:
            return False

        runtime_seconds = (
            datetime.now(timezone.utc) - started_at.astimezone(timezone.utc)
        ).total_seconds()
        return runtime_seconds >= METRIC_SERVICE_REDEPLOY_TIMEOUT_SECONDS

    def _clear_metric_service_unhealthy_tracker(self) -> None:
        if self.id is None:
            return
        _metric_service_unhealthy_since.pop(self.id, None)

    def _should_redeploy_unhealthy_metric_service(self) -> bool:
        if self.id is None:
            return False

        now = datetime.now(timezone.utc)
        unhealthy_since = _metric_service_unhealthy_since.get(self.id)
        if unhealthy_since is None:
            _metric_service_unhealthy_since[self.id] = now
            return False

        return (
            now - unhealthy_since.astimezone(timezone.utc)
        ).total_seconds() >= METRIC_SERVICE_REDEPLOY_TIMEOUT_SECONDS

    async def _redeploy_metric_service_container(
        self,
        db: AsyncSession,
        metric_service,
        *,
        reason: str,
    ) -> None:
        self._clear_metric_service_unhealthy_tracker()
        try:
            await self.remove_metric_service_container()
        except Exception as exc:
            LOGGER.error(
                "Failed to remove metric service container from host %s before redeploy: %s",
                self.name,
                exc,
            )
            await update_metric_service(
                db,
                metric_service,
                status=METRIC_SERVICE_STATUS.UNAVAILABLE.value,
                status_message=(
                    f"{reason} Automatic cleanup before redeploy failed: {exc}"
                ),
                clear_registration=True,
            )
            return

        deployment_state = self._ensure_metric_service_deployment_task()
        if deployment_state == METRIC_SERVICE_DEPLOYMENT_SCHEDULED:
            await update_metric_service(
                db,
                metric_service,
                status=METRIC_SERVICE_STATUS.DEPLOYING.value,
                status_message=reason,
                clear_registration=True,
            )
        elif deployment_state == METRIC_SERVICE_DEPLOYMENT_ALREADY_RUNNING:
            await update_metric_service(
                db,
                metric_service,
                status=METRIC_SERVICE_STATUS.DEPLOYING.value,
                status_message="Metric service redeployment is already in progress.",
                clear_registration=True,
            )
        else:
            await update_metric_service(
                db,
                metric_service,
                status=METRIC_SERVICE_STATUS.UNAVAILABLE.value,
                status_message=(
                    "Metric service cleanup finished, but automatic redeployment "
                    "could not be scheduled."
                ),
                clear_registration=True,
            )

    async def _check_metric_service_health(self, db: AsyncSession) -> bool:


        metric_service = await get_metric_service_by_host_id(db, self.id)
        if metric_service is None:
            metric_service = await get_or_create_metric_service(
                db,
                self.id,
                name=METRIC_SERVICE_DEFAULT_NAME,
                status=METRIC_SERVICE_STATUS.DEPLOYING.value,
                status_message="Metric service has not been deployed yet.",
            )

        client = get_docker_client(self, timeout=DOCKER_CONTROL_CLIENT_TIMEOUT)
        try:
            try:
                container = await asyncio.to_thread(
                    client.containers.get, self.get_metric_service_container_name()
                )
            except docker_sdk.errors.NotFound:
                deployment_state = self._ensure_metric_service_deployment_task()
                if deployment_state == METRIC_SERVICE_DEPLOYMENT_SCHEDULED:
                    await update_metric_service(
                        db,
                        metric_service,
                        status=METRIC_SERVICE_STATUS.DEPLOYING.value,
                        status_message="Metric service missing. Deploying it now.",
                        clear_registration=True,
                    )
                elif deployment_state == METRIC_SERVICE_DEPLOYMENT_ALREADY_RUNNING:
                    await update_metric_service(
                        db,
                        metric_service,
                        status=METRIC_SERVICE_STATUS.DEPLOYING.value,
                        status_message="Metric service deployment is already in progress.",
                    )
                else:
                    await update_metric_service(
                        db,
                        metric_service,
                        status=METRIC_SERVICE_STATUS.UNAVAILABLE.value,
                        status_message=(
                            "Metric service is missing and could not be redeployed "
                            "automatically."
                        ),
                    )
                return False

            await asyncio.to_thread(container.reload)
            state = container.attrs.get("State", {})
            if not state.get("Running"):
                if self._should_redeploy_unhealthy_metric_service():
                    await self._redeploy_metric_service_container(
                        db,
                        metric_service,
                        reason=(
                            "Metric service container stayed unavailable. Removing "
                            "and redeploying it."
                        ),
                    )
                    return False

                await update_metric_service(
                    db,
                    metric_service,
                    status=METRIC_SERVICE_STATUS.UNAVAILABLE.value,
                    status_message="Metric service container exists but is not running.",
                )
                return False

            if not metric_service.ip or not metric_service.port:
                self._clear_metric_service_unhealthy_tracker()
                if self._should_redeploy_metric_service(state, metric_service):
                    await self._redeploy_metric_service_container(
                        db,
                        metric_service,
                        reason=(
                            "Metric service did not register in time. Removing and "
                            "redeploying it."
                        ),
                    )
                    return False

                if self._is_metric_service_registration_stuck(state):
                    await self._redeploy_metric_service_container(
                        db,
                        metric_service,
                        reason=(
                            "Metric service registration is stuck. Removing and redeploying the "
                            "metric service."
                        ),
                    )
                    return False

                await update_metric_service(
                    db,
                    metric_service,
                    status=METRIC_SERVICE_STATUS.REGISTERING.value,
                    status_message="Metric service is running but has not registered yet.",
                )
                return False

            is_healthy = await self._metric_service_healthcheck(
                metric_service.ip, metric_service.port
            )
            if is_healthy:
                self._clear_metric_service_unhealthy_tracker()
            elif self._should_redeploy_unhealthy_metric_service():
                await self._redeploy_metric_service_container(
                    db,
                    metric_service,
                    reason=(
                        "Metric service healthcheck kept failing. Removing and "
                        "redeploying it."
                    ),
                )
                return False

            await update_metric_service(
                db,
                metric_service,
                status=(
                    METRIC_SERVICE_STATUS.AVAILABLE.value
                    if is_healthy
                    else METRIC_SERVICE_STATUS.UNAVAILABLE.value
                ),
                status_message=(
                    "Metric service is healthy."
                    if is_healthy
                    else "Metric service healthcheck failed."
                ),
            )
            return is_healthy
        finally:
            client.close()

    async def remove_metric_service_container(self) -> None:
        if self.id is None:
            return

        client = get_docker_client(self, timeout=DOCKER_CONTROL_CLIENT_TIMEOUT)
        try:
            try:
                container = await asyncio.to_thread(
                    client.containers.get, self.get_metric_service_container_name()
                )
            except docker_sdk.errors.NotFound:
                return

            await asyncio.to_thread(container.remove, force=True)
        finally:
            client.close()

    async def check_host_health(self, db: AsyncSession | None = None):
        try:
            if await self.is_host_reachable():
                LOGGER.debug(f"host {self.name} is reachable")
                client = get_docker_client(self, timeout=DOCKER_CONTROL_CLIENT_TIMEOUT)
                try:
                    version = await asyncio.to_thread(client.version)
                finally:
                    client.close()

                if version:
                    LOGGER.info(f"Docker Host {self.name} is reachable")
                    if db is None:
                        return DOCKER_HOST_STATUS.AVAILABLE.value
                    if await self._check_metric_service_health(db):
                        return DOCKER_HOST_STATUS.AVAILABLE.value
                    return DOCKER_HOST_STATUS.UNAVAILABLE.value
            else:
                self._clear_metric_service_unhealthy_tracker()
                LOGGER.info(f"host {self.name} is not reachable")
                await self._mark_metric_service_unavailable(
                    db, "Docker host is not reachable."
                )
        except Exception as e:
            self._clear_metric_service_unhealthy_tracker()
            LOGGER.error(e)
            await self._mark_metric_service_unavailable(
                db, f"Docker host healthcheck failed: {e}"
            )
        return DOCKER_HOST_STATUS.UNAVAILABLE.value

    async def is_host_reachable(self, timeout: float = 2.0) -> bool:
        if self.is_core_host():
            socket_path = os.getenv("DOCKER_SOCKET_PATH", "/var/run/docker.sock")
            if os.path.exists(socket_path):
                return True
            # socket absent – fall back to TCP probe
        host, port = self.get_host_and_docker_port()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def update_availability(self, db: AsyncSession):
        old_availability = self.status
        new_availability = await self.check_host_health(db)
        if old_availability != new_availability:
            LOGGER.debug(
                f"Host {self.name} changed its availability from {old_availability} to {new_availability}"
            )
            await set_host_status(db, self, new_availability)
            LOGGER.debug(f"Changed status from host {self.name} to {new_availability}")


async def set_host_status(
    db: AsyncSession, host: DockerHostSystem, status: DOCKER_HOST_STATUS
):
    host.status = status
    await db.commit()
    await db.refresh(host)


async def get_host_by_id(db: AsyncSession, id: int):
    stmt = select(DockerHostSystem).where(DockerHostSystem.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_hosts(db: AsyncSession):
    stmt = select(DockerHostSystem)
    result = await db.execute(stmt)
    return result.scalars().all()


async def add_host_system(db: AsyncSession, host: DockerHostSystem):
    db.add(host)
    await db.commit()
    await db.refresh(host)
    host.status = await host.check_host_health(db)
    await db.commit()
    await db.refresh(host)


async def remove_host(db: AsyncSession, host_id: int):
    host: DockerHostSystem = await get_host_by_id(db, host_id)
    if host is None:
        return False

    try:
        await host.remove_metric_service_container()
    except Exception as exc:
        LOGGER.error(
            f"Failed to remove metric service container from host {host.name}: {exc}"
        )
        raise RuntimeError(
            f"Could not remove metric service container from host {host.name}."
        ) from exc

    await db.delete(host)
    await db.commit()
    return True
