import os
import shutil
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models.configuration import Configuration
from app.models.ids_tool import IdsTool


MALTRAIL_CONFIG_NAME = "maltrail.conf"
MALTRAIL_RUNTIME_CONFIG_DIR = "uuid9"
MALTRAIL_IMAGE_NAME = "ghcr.io/maldwg/bicep-maltrail"
MALTRAIL_IMAGE_TAG = "latest"


def get_default_maltrail_config_path() -> str:
    runtime_base_path = os.getenv("RUNTIME_STORE_BASE_PATH", "/opt/runtime_configurations")
    return os.path.join(runtime_base_path, MALTRAIL_RUNTIME_CONFIG_DIR, MALTRAIL_CONFIG_NAME)


def ensure_default_maltrail_config_file() -> str:
    destination_path = Path(get_default_maltrail_config_path())
    source_path = Path(__file__).resolve().parent / "default_configs" / MALTRAIL_CONFIG_NAME

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if not destination_path.exists():
        shutil.copyfile(source_path, destination_path)

    return str(destination_path)


async def ensure_default_maltrail_assets():
    config_path = ensure_default_maltrail_config_file()
    if SessionLocal is None:
        return

    async with SessionLocal() as db:
        result = await db.execute(select(IdsTool).where(IdsTool.name == "Maltrail"))
        if result.scalar_one_or_none() is None:
            db.add(
                IdsTool(
                    name="Maltrail",
                    ids_type="NIDS",
                    analysis_method="Threat-intel-based",
                    requires_ruleset=False,
                    image_name=MALTRAIL_IMAGE_NAME,
                    image_tag=MALTRAIL_IMAGE_TAG,
                    deployment_type="SINGLE_CONTAINER",
                    required_env_vars="",
                )
            )

        result = await db.execute(
            select(Configuration).where(Configuration.file_path == config_path)
        )
        if result.scalar_one_or_none() is None:
            db.add(
                Configuration(
                    name=MALTRAIL_CONFIG_NAME,
                    file_path=config_path,
                    file_type="RUNTIME",
                    description="default maltrail configuration",
                    config_type="RUNTIME",
                )
            )

        await db.commit()
