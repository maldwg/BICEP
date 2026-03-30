"""
IDS System Models - Polymorphic base class and subclasses for NIDS, HIDS, CIDS.
"""

import asyncio
import os
import httpx
from http.client import HTTPResponse
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.ids_tool import get_ids_by_id
from app.models.ensemble_ids import EnsembleIds
from app.models.ids_component import IdsComponent
from app.utils import (
    STATUS,
    start_network_analysis,
    start_static_analysis,
    stop_analysis,
    get_core_host_ip,
)
from app.validation.models import IdsContainerUpdate
from app.database import Base
from app.logger import LOGGER
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession


class IdsSystem(Base):
    """Base class for all IDS deployments. Uses SQLAlchemy single-table inheritance."""

    __tablename__ = "ids_system"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)
    description = Column(String(2048))
    configuration_id = Column(Integer, ForeignKey("configuration.id"))
    ids_tool_id = Column(Integer, ForeignKey("ids_tool.id"))
    ruleset_id = Column(Integer, ForeignKey("configuration.id"))
    runtime_configuration_id = Column(
        Integer, ForeignKey("configuration.id"), nullable=True
    )
    host_system_id = Column(Integer, ForeignKey("docker_host_system.id"))

    # Polymorphic discriminator
    type = Column(String(32), nullable=False, default="NIDS")

    __mapper_args__ = {"polymorphic_identity": "IDS", "polymorphic_on": type}

    host_system = relationship(
        "DockerHostSystem", back_populates="container", lazy="selectin"
    )
    ensemble_ids = relationship("EnsembleIds", cascade="all, delete", lazy="selectin")
    components = relationship(
        IdsComponent,
        back_populates="container",
        cascade="all, delete",
        lazy="selectin",
    )

    # ==================== LIFECYCLE METHODS ====================

    async def setup(self, db: AsyncSession, **kwargs):
        """Setup the IDS system. Override in subclasses for type-specific behavior."""
        from app.models.configuration import get_config_by_id

        ids_tool = await get_ids_by_id(db, self.ids_tool_id)
        self.name = f"{ids_tool.name}-{self.port}"
        config = await get_config_by_id(db, self.configuration_id)
        ruleset = None
        if ids_tool.requires_ruleset:
            ruleset = await get_config_by_id(db, self.ruleset_id)

        runtime_config = None
        if self.runtime_configuration_id:
            runtime_config = await get_config_by_id(db, self.runtime_configuration_id)

        self.status = STATUS.SETTING_UP.value
        db.add(self)
        await db.commit()
        await db.refresh(self)
        try:
            await self._deploy(
                ids_tool, config, ruleset, db, runtime_config=runtime_config, **kwargs
            )
        except Exception as e:
            LOGGER.error(f"Setup failed: {e}")
            try:
                await self.teardown(db)
            except Exception as teardown_error:
                LOGGER.error(f"Teardown during failed setup also failed: {teardown_error}")
                await db.delete(self)
                await db.commit()
            raise
        self.status = STATUS.IDLE.value
        await db.commit()
        await db.refresh(self)

    async def _deploy(self, ids_tool, config, ruleset, db, **kwargs):
        """Deploy the IDS. Override in subclasses for different deployment strategies."""
        from app.docker import start_docker_container

        await start_docker_container(self, ids_tool, config, ruleset, db)

    async def teardown(self, db: AsyncSession):
        """Remove the IDS system and its Docker container."""
        from app.docker import remove_docker_container

        try:
            await remove_docker_container(self)
        except Exception as e:
            LOGGER.error(f"Teardown error: {e}")
        await db.delete(self)
        await db.commit()

    # ==================== CONFIGURATION METHODS ====================

    async def update_config(self, db: AsyncSession, config_id: int):
        """Update the configuration file."""
        from app.models.configuration import Configuration
        from app.docker import inject_config

        stmt = select(Configuration).where(Configuration.id == config_id)
        result = await db.execute(stmt)
        config_file = result.scalar_one_or_none()
        if config_file:
            await inject_config(self, config_file)

    async def update_ruleset(self, db: AsyncSession, ruleset_id: int):
        """Update the ruleset file."""
        from app.models.configuration import Configuration
        from app.docker import inject_ruleset

        stmt = select(Configuration).where(Configuration.id == ruleset_id)
        result = await db.execute(stmt)
        ruleset_file = result.scalar_one_or_none()
        if ruleset_file:
            await inject_ruleset(self, ruleset_file)

    # ==================== ANALYSIS METHODS ====================

    async def start_static_analysis(self, form_data, dataset):
        """Start static analysis. Override in subclasses for type-specific behavior."""
        response: HTTPResponse = await start_static_analysis(self, form_data, dataset)
        return response

    async def start_network_analysis(self, data):
        """Start network analysis. Override in subclasses for type-specific behavior."""
        response = await start_network_analysis(self, data)
        return response

    async def stop_analysis(self):
        """Stop the current analysis."""
        result = await stop_analysis(self)
        return result

    # ==================== UTILITY METHODS ====================

    async def is_busy(self) -> bool:
        """Check if the IDS is currently running an analysis."""
        return self.status == STATUS.ACTIVE.value

    async def is_available(self) -> bool:
        """Check if the IDS container is healthy and available."""
        from app.docker import check_container_health

        return await check_container_health(self)

    def get_container_http_url(self) -> str:
        """Get the HTTP URL for communicating with this IDS."""
        target_port = self.port
        # Check for CIDS sensor component
        if self.components:
            for component in self.components:
                if component.role == "SENSOR" and component.port:
                    target_port = component.port
                    break

        if "Core" in self.host_system.name or self.host_system.host == "localhost":
            core_host = get_core_host_ip()
            return f"http://{core_host}:{target_port}"
        else:
            return f"http://{self.host_system.host}:{target_port}"


class NidsSystem(IdsSystem):
    """Network Intrusion Detection System - single container deployment for network traffic analysis."""

    __mapper_args__ = {"polymorphic_identity": "NIDS"}

    async def start_network_analysis(self, data):
        """NIDS-specific network analysis with packet capture."""
        LOGGER.info(f"Starting NIDS network analysis on {self.name}")
        return await super().start_network_analysis(data)

    async def start_static_analysis(self, form_data, dataset):
        """NIDS static analysis using PCAP files."""
        LOGGER.info(f"Starting NIDS static analysis on {self.name}")
        return await super().start_static_analysis(form_data, dataset)


class HidsSystem(IdsSystem):
    """Host Intrusion Detection System - log-based analysis."""

    __mapper_args__ = {"polymorphic_identity": "HIDS"}

    async def start_static_analysis(self, form_data, dataset):
        """HIDS-specific static/log analysis."""
        LOGGER.info(f"Starting HIDS static analysis on {self.name}")
        return await super().start_static_analysis(form_data, dataset)

    async def start_network_analysis(self, data):
        """HIDS typically doesn't do network analysis, but can monitor host network."""
        LOGGER.warning(
            f"HIDS {self.name} starting network analysis (typically log-based)"
        )
        return await super().start_network_analysis(data)


class CidsSystem(IdsSystem):
    """Centralized IDS - Docker Compose multi-component deployment."""

    __mapper_args__ = {"polymorphic_identity": "CIDS"}

    async def _deploy(self, ids_tool, config, ruleset, db, **kwargs):
        """CIDS uses Docker Compose for multi-component deployment."""
        from app.cids_deployment import start_cids_deployment

        cids_configurations = kwargs.get("cids_configurations")
        env_vars = kwargs.get("env_vars", {})
        await start_cids_deployment(
            self,
            ids_tool,
            config,
            ruleset,
            db,
            cids_configurations,
            env_vars=env_vars,
        )

        # Refresh the components relationship to reflect the newly deployed components
        await db.refresh(self, attribute_names=["components"])

        # Wait for all containers to become healthy
        import time

        timeout = 120
        start_time = time.time()
        while True:
            if await self.is_available():
                LOGGER.info(f"CIDS {self.id} is healthy after deployment")
                break
            if time.time() - start_time > timeout:
                LOGGER.error(f"CIDS {self.id} did not become healthy within {timeout}s")
                raise Exception(f"CIDS did not become healthy within {timeout}s")
            await asyncio.sleep(3)

        from app.docker import inject_ruleset,inject_config
        await inject_config(self, config)

        if ruleset:
            await inject_ruleset(self, ruleset)

    async def is_available(self) -> bool:
        """Check CIDS health via compose state and a quick sensor health probe."""
        from python_on_whales import DockerClient
        from collections import defaultdict

        if not self.components:
            return False

        # Group components by host
        components_by_host = defaultdict(list)
        for component in self.components:
            components_by_host[component.host_system_id].append(component)

        for components in components_by_host.values():
            host_system = components[0].host_system
            host_name_safe = host_system.name.replace(" ", "_").lower()
            project_name = f"bicep_cids_{self.id}_{host_name_safe}"
            work_dir = f"/tmp/{project_name}"
            compose_file = os.path.join(work_dir, "docker-compose.yaml")

            host_ip, docker_port = host_system.get_host_and_docker_port()
            docker_host_url = f"tcp://{host_ip}:{docker_port}"

            try:
                if not os.path.exists(compose_file):
                    LOGGER.warning(f"Compose file missing for {project_name}")
                    return False

                client = DockerClient(
                    host=docker_host_url,
                    compose_files=[compose_file],
                    compose_project_name=project_name,
                )
                containers = client.compose.ps()

                if not containers:
                    return False

                for c in containers:
                    health = c.state.health.status if c.state.health else None
                    if health and health != "healthy":
                        return False
                    if not c.state.running:
                        return False

            except Exception as e:
                LOGGER.error(f"CIDS healthcheck error on {host_system.name}: {e}")
                return False

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.get_container_http_url()}/healthcheck")
            if response.status_code != 200:
                return False
        except Exception:
            return False

        return True

    async def teardown(self, db: AsyncSession):
        """CIDS teardown: use docker compose down to remove all containers at once."""
        from python_on_whales import DockerClient
        from python_on_whales.exceptions import DockerException
        from collections import defaultdict

        LOGGER.info(
            f"Tearing down CIDS {self.name} ({len(self.components)} components)"
        )

        # Group components by host to run compose down per host
        components_by_host = defaultdict(list)
        for component in self.components:
            components_by_host[component.host_system_id].append(component)

        for components in components_by_host.values():
            host_system = components[0].host_system
            host_name_safe = host_system.name.replace(" ", "_").lower()
            project_name = f"bicep_cids_{self.id}_{host_name_safe}"

            host_ip, docker_port = host_system.get_host_and_docker_port()
            docker_host_url = f"tcp://{host_ip}:{docker_port}"

            try:
                # Use only project name — no compose file needed for teardown.
                # This avoids env var interpolation errors (e.g. MOUNT_PATH not set).
                client = DockerClient(
                    host=docker_host_url,
                    compose_project_name=project_name,
                )
                try:
                    client.compose.down(volumes=True, timeout=15)
                    LOGGER.info(
                        f"Compose down completed for {project_name} on {host_system.name}"
                    )
                except DockerException as e:
                    LOGGER.warning(f"Compose down failed for {project_name}: {e}")
                    # Fall back to individual container removal
                    import docker as docker_sdk

                    docker_client = docker_sdk.DockerClient(base_url=docker_host_url)
                    for component in components:
                        try:
                            container = docker_client.containers.get(component.name)
                            container.stop(timeout=10)
                            container.remove()
                            LOGGER.info(f"Removed {component.name}")
                        except docker_sdk.errors.NotFound:
                            LOGGER.warning(f"{component.name} not found, skipping")
                        except Exception as inner_e:
                            LOGGER.error(f"Error removing {component.name}: {inner_e}")
                    docker_client.close()
            except Exception as e:
                LOGGER.error(f"Teardown error on {host_system.name}: {e}")

            for component in components:
                await db.delete(component)

        await db.delete(self)
        await db.commit()

    def get_container_http_url(self) -> str:
        """CIDS routes to the sensor component for analysis requests."""
        if self.components:
            for component in self.components:
                if component.role == "SENSOR":
                    if component.host_system or not self.host_system:
                        return component.get_http_url()

                    host = self.host_system.host
                    if "Core" in self.host_system.name or host == "localhost":
                        host = get_core_host_ip()
                    return f"http://{host}:{component.port}"
        return super().get_container_http_url()

    async def start_network_analysis(self, data):
        """CIDS network analysis routes to sensor nodes."""
        LOGGER.info(f"Starting CIDS network analysis on {self.name}")
        return await super().start_network_analysis(data)

    async def start_static_analysis(self, form_data, dataset):
        """CIDS static analysis routes to sensor nodes."""
        LOGGER.info(f"Starting CIDS static analysis on {self.name}")
        return await super().start_static_analysis(form_data, dataset)

    async def update_config(self, db: AsyncSession, config_id: int):
        """CIDS: Propagate config to all components and restart them."""
        from app.models.configuration import Configuration
        from app.docker import inject_config_to_url

        stmt = select(Configuration).where(Configuration.id == config_id)
        result = await db.execute(stmt)
        config_file = result.scalar_one_or_none()
        if not config_file:
            return

        for component in self.components:
            if component.port:
                component_url = component.get_http_url()
                await inject_config_to_url(
                    component_url, config_file, self.id, component.name
                )

        # Restart all components for changes to take effect
        await self._restart_components()

    async def update_ruleset(self, db: AsyncSession, ruleset_id: int):
        """CIDS: Propagate ruleset to all components and restart them."""
        from app.models.configuration import Configuration
        from app.docker import inject_ruleset_to_url

        stmt = select(Configuration).where(Configuration.id == ruleset_id)
        result = await db.execute(stmt)
        ruleset_file = result.scalar_one_or_none()
        if not ruleset_file:
            return

        for component in self.components:
            if component.port:
                component_url = component.get_http_url()
                await inject_ruleset_to_url(component_url, ruleset_file)

        await self._restart_components()

    async def _restart_components(self):
        """Restart all CIDS components via Docker API."""
        from app.docker import restart_docker_container

        for component in self.components:
            await restart_docker_container(component)


# ==================== QUERY FUNCTIONS ====================


async def get_ids_system_by_id(db: AsyncSession, id: int) -> IdsSystem | None:
    """Get an IDS system by ID."""
    stmt = select(IdsSystem).where(IdsSystem.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_container(db: AsyncSession) -> list[IdsSystem]:
    """Get all IDS systems."""
    stmt = select(IdsSystem)
    result = await db.execute(stmt)
    return result.scalars().all()


async def remove_container_by_id(db: AsyncSession, id: int):
    """Remove an IDS system by ID."""
    container = await get_ids_system_by_id(db, id)
    if container:
        await db.delete(container)
        await db.commit()


async def update_container(db: AsyncSession, container: IdsContainerUpdate):
    """Update an IDS system's configuration."""
    stmt = select(IdsSystem).where(IdsSystem.id == container.id)
    result = await db.execute(stmt)
    container_db: IdsSystem = result.scalar_one_or_none()
    if not container_db:
        return None
    old_config_id = container_db.configuration_id
    new_config_id = container.configuration_id
    if old_config_id != new_config_id:
        await container_db.update_config(db, new_config_id)
    old_ruleset_id = container_db.ruleset_id
    new_ruleset_id = container.ruleset_id
    if old_ruleset_id != new_config_id and new_ruleset_id is not None:
        await container_db.update_ruleset(db, new_ruleset_id)
    for key, value in container.model_dump().items():
        setattr(container_db, key, value)
    await db.commit()
    await db.refresh(container_db)


async def update_ids_status(
    db: AsyncSession, status: STATUS, container: IdsSystem
):
    """Update the status of an IDS system."""
    container.status = status
    await db.commit()
    await db.refresh(container)
