from __future__ import annotations

import asyncio


class ComposeAvailabilityChecker:
    def __init__(
        self,
        docker_sdk_module,
        host_operations,
        logger,
        http_client_cls,
    ):
        self._docker_sdk = docker_sdk_module
        self._host_operations = host_operations
        self._logger = logger
        self._http_client_cls = http_client_cls

    async def is_available(self, ids_system) -> bool:
        if not ids_system.components:
            return False

        if not await self._all_components_are_healthy(ids_system):
            return False

        return await self._all_sensor_endpoints_are_available(ids_system)

    def _host_components_are_healthy(self, host_system, components) -> bool:
        client = self._docker_sdk.DockerClient(
            base_url=self._host_operations.get_docker_host_url(host_system)
        )
        try:
            for component in components:
                container = client.containers.get(component.name)
                state = container.attrs.get("State", {})
                if not state.get("Running"):
                    return False

                health = state.get("Health")
                if health is not None and health.get("Status") != "healthy":
                    return False

            return True
        except self._docker_sdk.errors.NotFound:
            return False
        except Exception as exc:
            self._logger.error(f"CIDS healthcheck error on {host_system.name}: {exc}")
            return False
        finally:
            client.close()

    async def _all_components_are_healthy(self, ids_system) -> bool:
        components_by_host = self._host_operations.group_components_by_host(
            ids_system.components
        )
        checks = []

        for components in components_by_host.values():
            host_system = components[0].host_system or ids_system.host_system
            if host_system is None:
                return False
            checks.append(
                asyncio.to_thread(
                    self._host_components_are_healthy,
                    host_system,
                    components,
                )
            )

        return all(await asyncio.gather(*checks))

    async def _sensor_endpoint_is_available(self, client, base_url: str) -> bool:
        try:
            response = await client.get(f"{base_url}/healthcheck")
            return response.status_code == 200
        except Exception:
            return False

    async def _all_sensor_endpoints_are_available(self, ids_system) -> bool:
        sensor_urls = list(
            dict.fromkeys(
                component.get_http_url()
                for component in ids_system.components
                if component.role == "SENSOR" and component.port
            )
        )
        if not sensor_urls:
            sensor_urls = [ids_system.get_container_http_url()]

        async with self._http_client_cls(timeout=3.0) as client:
            return all(
                await asyncio.gather(
                    *(
                        self._sensor_endpoint_is_available(client, sensor_url)
                        for sensor_url in sensor_urls
                    )
                )
            )
