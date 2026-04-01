"""
IDS System Models - Polymorphic base class and subclasses for NIDS, HIDS, CIDS.
"""

from http.client import HTTPResponse
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.ids_tool import get_ids_by_id
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
    ids_tool = relationship("IdsTool", lazy="selectin", back_populates="container")
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
        self.ids_tool = ids_tool
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
        from app.deployment import deploy_ids

        await deploy_ids(
            self,
            ids_tool,
            config,
            ruleset,
            db,
            runtime_configuration=kwargs.get("runtime_config"),
            cids_configurations=kwargs.get("cids_configurations"),
            env_vars=kwargs.get("env_vars"),
        )

    async def teardown(self, db: AsyncSession):
        """Remove the IDS system and its Docker container."""
        from app.deployment import teardown_ids

        await teardown_ids(self, db)

    # ==================== CONFIGURATION METHODS ====================

    async def update_config(self, db: AsyncSession, config_id: int):
        """Update the configuration file."""
        from app.deployment import update_ids_config

        await update_ids_config(self, db, config_id)

    async def update_ruleset(self, db: AsyncSession, ruleset_id: int):
        """Update the ruleset file."""
        from app.deployment import update_ids_ruleset

        await update_ids_ruleset(self, db, ruleset_id)

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

    async def is_available(self, db: AsyncSession | None = None) -> bool:
        """Check if the IDS container is healthy and available."""
        from app.deployment import is_ids_available

        return await is_ids_available(self, db)

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
    if old_ruleset_id != new_ruleset_id and new_ruleset_id is not None:
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


def get_ids_system_model(ids_type: str | None):
    ids_type_normalized = (ids_type or "").upper()
    ids_system_models = {
        "NIDS": NidsSystem,
        "HIDS": HidsSystem,
        "CIDS": CidsSystem,
    }
    return ids_system_models.get(ids_type_normalized, IdsSystem)
