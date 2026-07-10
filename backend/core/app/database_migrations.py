from sqlalchemy import text

from app.database import engine
from app.logger import LOGGER


FEATURE_SCHEMA_STATEMENTS = (
    "ALTER TABLE dataset ADD COLUMN IF NOT EXISTS evaluation_mode "
    "VARCHAR(32) NOT NULL DEFAULT 'binary'",
    "ALTER TABLE dataset ADD COLUMN IF NOT EXISTS class_counts TEXT",
    "ALTER TABLE benchmarking_result ADD COLUMN IF NOT EXISTS evaluation_mode "
    "VARCHAR(32) NOT NULL DEFAULT 'binary'",
    "ALTER TABLE benchmarking_job_item ADD COLUMN IF NOT EXISTS avg_cpu_usage FLOAT",
    "ALTER TABLE benchmarking_job_item ADD COLUMN IF NOT EXISTS avg_memory_usage FLOAT",
    "ALTER TABLE benchmarking_job_item ADD COLUMN IF NOT EXISTS resource_query_mode VARCHAR(32)",
    "ALTER TABLE benchmarking_job_item ADD COLUMN IF NOT EXISTS resource_query_targets TEXT",
    """
    CREATE TABLE IF NOT EXISTS benchmarking_class_result (
        id INT AUTO_INCREMENT PRIMARY KEY,
        benchmarking_result_id INT NOT NULL,
        class_label VARCHAR(256) NOT NULL,
        support INT NOT NULL,
        detected INT NOT NULL,
        missed INT NOT NULL,
        detection_rate FLOAT NOT NULL,
        FOREIGN KEY (benchmarking_result_id)
            REFERENCES benchmarking_result(id) ON DELETE CASCADE
    )
    """,
)


async def apply_feature_schema_migrations() -> None:
    """Apply idempotent schema additions needed by current feature releases."""
    if engine is None:
        return

    async with engine.begin() as connection:
        for statement in FEATURE_SCHEMA_STATEMENTS:
            await connection.execute(text(statement))
    LOGGER.info("Database feature schema is up to date.")
