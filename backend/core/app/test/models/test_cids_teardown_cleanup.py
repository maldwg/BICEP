from unittest.mock import MagicMock, patch

from app.models.ids_system import (
    _cleanup_project_networks_and_volumes,
    _remove_work_dir,
)


def test_remove_work_dir_local_uses_shutil():
    host = MagicMock()
    host.host = "localhost"

    with patch("app.models.ids_system.shutil.rmtree") as mock_rmtree:
        _remove_work_dir(host, "/tmp/bicep_cids_7_localhost")

    mock_rmtree.assert_called_once_with("/tmp/bicep_cids_7_localhost", ignore_errors=True)


def test_cleanup_project_networks_and_volumes_removes_labeled_resources():
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.name = "leftover-container"
    mock_network = MagicMock()
    mock_network.name = "leftover-network"
    mock_volume = MagicMock()
    mock_volume.name = "leftover-volume"

    mock_client.containers.list.return_value = [mock_container]
    mock_client.networks.list.return_value = [mock_network]
    mock_client.volumes.list.return_value = [mock_volume]

    with patch("app.models.ids_system.docker.DockerClient", return_value=mock_client):
        _cleanup_project_networks_and_volumes("tcp://127.0.0.1:2375", "bicep_cids_7_localhost")

    mock_container.remove.assert_called_once_with(force=True, v=True)
    mock_network.remove.assert_called_once()
    mock_volume.remove.assert_called_once_with(force=True)
    mock_client.close.assert_called_once()
