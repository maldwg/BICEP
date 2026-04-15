from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class DeploymentContext:
    ids_system: Any
    ids_tool: Any
    config: Any
    ruleset: Any = None
    db_session: AsyncSession | None = None
    runtime_configuration: Any = None
    cids_configurations: list[Any] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)


class DeploymentPlugin(ABC):
    deployment_type = ""
    startup_timeout = 90
    healthcheck_interval = 2

    async def deploy(self, context: DeploymentContext):
        await self.start(context)
        await self.wait_until_healthy(context)
        await self.configure(context)

    @abstractmethod
    async def start(self, context: DeploymentContext):
        """Create and start the deployment resources."""

    async def wait_until_healthy(self, context: DeploymentContext):
        from app.deployment.common import wait_for_condition

        healthy = await wait_for_condition(
            lambda: self.is_available(context.ids_system),
            timeout=self.startup_timeout,
            interval=self.healthcheck_interval,
        )
        if not healthy:
            raise Exception(
                f"{self.deployment_type} deployment for IDS {context.ids_system.id} "
                "did not become healthy in time."
            )

    async def configure(self, context: DeploymentContext):
        await self.inject_config(context.ids_system, context.config)
        if context.ruleset is not None:
            await self.inject_ruleset(context.ids_system, context.ruleset)

    @abstractmethod
    async def inject_config(self, ids_system, configuration):
        """Inject the main configuration into the running deployment."""

    @abstractmethod
    async def inject_ruleset(self, ids_system, ruleset):
        """Inject a ruleset into the running deployment."""

    @abstractmethod
    async def teardown(self, ids_system, db_session: AsyncSession, delete_system: bool = True):
        """Remove deployment resources and optionally delete the IDS system from the DB."""

    @abstractmethod
    async def is_available(self, ids_system) -> bool:
        """Return True when the deployment is healthy and reachable."""

    async def update_config(
        self, ids_system, db_session: AsyncSession, config_id: int
    ):
        from app.deployment.common import load_configuration

        config = await load_configuration(db_session, config_id)
        if config is not None:
            await self.inject_config(ids_system, config)

    async def update_ruleset(
        self, ids_system, db_session: AsyncSession, ruleset_id: int
    ):
        from app.deployment.common import load_configuration

        ruleset = await load_configuration(db_session, ruleset_id)
        if ruleset is not None:
            await self.inject_ruleset(ids_system, ruleset)

    async def update_components(
        self, ids_system, db_session: AsyncSession, components: list
    ):
        await self.update_config(ids_system, db_session, ids_system.configuration_id)
