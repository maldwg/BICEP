from pathlib import Path

import pytest

from app import defaults


def test_ensure_default_maltrail_config_file(monkeypatch, tmp_path):
    monkeypatch.setenv("RUNTIME_STORE_BASE_PATH", str(tmp_path))

    config_path = defaults.ensure_default_maltrail_config_file()

    saved_config = Path(config_path)
    assert saved_config == tmp_path / "uuid9" / "maltrail.conf"
    assert saved_config.exists()
    assert "MONITOR_INTERFACE any" in saved_config.read_text(encoding="utf-8")
    assert "LOG_DIR /opt/logs" in saved_config.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_ensure_default_maltrail_assets_without_database(monkeypatch, tmp_path):
    monkeypatch.setenv("RUNTIME_STORE_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(defaults, "SessionLocal", None)

    await defaults.ensure_default_maltrail_assets()

    assert (tmp_path / "uuid9" / "maltrail.conf").exists()
