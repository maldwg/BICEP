from __future__ import annotations

import asyncio


class ComposeDeploymentService:
    def __init__(self, get_host_by_id, spec_manager, host_operations):
        self._get_host_by_id = get_host_by_id
        self._spec_manager = spec_manager
        self._host_operations = host_operations

    async def deploy(
        self,
        ids_container,
        config,
        ruleset,
        db_session,
        cids_configurations,
        env_vars=None,
    ) -> None:
        compose_data = self._spec_manager.load_compose_data(await config.read_content())
        service_runtime_configs = await self._spec_manager.resolve_service_runtime_configs(
            db_session,
            compose_data,
            cids_configurations or [],
        )
        ids_container._deployment_hosts = []
        prepared_deployments = []

        try:
            services_by_host = self._spec_manager.group_services_by_host(
                compose_data,
                cids_configurations,
                ids_container.host_system.id,
            )

            for host_id, services in services_by_host.items():
                host_system = await self._get_host_by_id(db_session, host_id)
                ids_container._deployment_hosts.append(host_system)

                deployment = self._spec_manager.prepare_host_deployment(
                    compose_data=compose_data,
                    services=services,
                    ids_container=ids_container,
                    host_system=host_system,
                    service_runtime_configs=service_runtime_configs,
                )
                if deployment is None:
                    continue

                prepared_deployments.append(deployment)
                await self._spec_manager.write_deployment_files(deployment, ruleset)

                if deployment.runtime_config_files:
                    await self._host_operations.copy_runtime_configs(deployment)

                await self._host_operations.start_project(
                    deployment=deployment,
                    ids_container=ids_container,
                    db_session=db_session,
                    env_vars=env_vars,
                )
        except Exception:
            cleanup_ok = await self._cleanup_failed_deployment(
                ids_container,
                prepared_deployments,
            )
            if cleanup_ok:
                ids_container._deployment_cleanup_done = True
            raise

        await db_session.commit()

    async def teardown(self, ids_system) -> None:
        components_by_host = self._host_operations.group_components_by_host(
            ids_system.components
        )
        hosts_to_teardown = {}

        for components in components_by_host.values():
            host_system = components[0].host_system
            hosts_to_teardown[host_system.id] = (host_system, components)

        for host_system in getattr(ids_system, "_deployment_hosts", []):
            hosts_to_teardown.setdefault(host_system.id, (host_system, []))

        await asyncio.gather(
            *(
                self._host_operations.teardown_project(
                    host_system=host_system,
                    components=components,
                    paths=self._spec_manager.build_paths(
                        ids_system.id, host_system.name
                    ),
                )
                for host_system, components in hosts_to_teardown.values()
            )
        )

    async def _cleanup_failed_deployment(self, ids_container, prepared_deployments) -> bool:
        components_by_host = self._host_operations.group_components_by_host(
            ids_container.components
        )
        results = await asyncio.gather(
            *(
                self._host_operations.teardown_project(
                    host_system=deployment.host_system,
                    components=components_by_host.get(
                        deployment.host_system.id,
                        [],
                    ),
                    paths=deployment.paths,
                )
                for deployment in prepared_deployments
            ),
            return_exceptions=True,
        )
        return all(result is True for result in results)
