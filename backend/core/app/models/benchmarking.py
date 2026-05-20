from datetime import datetime
from app.bicep_utils.models.ids_base import Alert
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base
from sqlalchemy.future import select
from sqlalchemy.orm import relationship, selectinload
from app.database import engine


BENCHMARK_JOB_STATUS_QUEUED = "queued"
BENCHMARK_JOB_STATUS_RUNNING = "running"
BENCHMARK_JOB_STATUS_COMPLETED = "completed"
BENCHMARK_JOB_STATUS_CANCELLED = "cancelled"
BENCHMARK_JOB_STATUS_FAILED = "failed"

BENCHMARK_ITEM_STATUS_PENDING = "pending"
BENCHMARK_ITEM_STATUS_RUNNING = "running"
BENCHMARK_ITEM_STATUS_COMPLETED = "completed"
BENCHMARK_ITEM_STATUS_CANCELLED = "cancelled"
BENCHMARK_ITEM_STATUS_FAILED = "failed"

BENCHMARK_TARGET_CONTAINER = "container"
BENCHMARK_TARGET_ENSEMBLE = "ensemble"


def get_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


class BenchmarkingIntermediateResult(Base):
    __tablename__ = "benchmarking_intermediate_result"
    
    id = Column(Integer, primary_key=True, index=True)
    ensemble_name = Column(String(256))
    ensemble_uuid = Column(String(64))
    container_name = Column(String(128))
    start_time = Column(String(256))
    stop_time = Column(String(256))
    
async def get_all_intermediate_results_for_ensemble_and_id(db: AsyncSession, uuid: str, ensemble_name: str):
    stmt = select(BenchmarkingIntermediateResult).where(
                                                        BenchmarkingIntermediateResult.ensemble_name == ensemble_name,
                                                        BenchmarkingIntermediateResult.ensemble_uuid == uuid
                                                    )
    result = await db.execute(stmt)
    return result.scalars().all()  
async def save_intermedaite_result(db: AsyncSession, intermediate_result: BenchmarkingIntermediateResult):
    db.add(intermediate_result)
    await db.commit() 
    await db.refresh(intermediate_result) 
    
class BenchmarkingResultTransferObject():
    def __init__(self, dataset_id: int, alerts: list[Alert], start_time: datetime, stop_time: datetime):
        self.dataset_id = dataset_id
        self.alerts = alerts
        self.start_time = start_time
        self.stop_time = stop_time
        self.runtime = (datetime.strptime(stop_time, "%d-%m-%Y %H:%M:%S.%f") - datetime.strptime(start_time, "%d-%m-%Y %H:%M:%S.%f")).total_seconds()
        
class BenchmarkingResult(Base):
    __tablename__ = "benchmarking_result"

    id = Column(Integer, primary_key=True, index=True)
    dataset_name = Column(String(256))
    ids_name = Column(String(256))
    ensembling_method = Column(String(256))
    configuration_name = Column(String(256))
    ruleset_name = Column(String(256))
    start_time = Column(String(256))
    stop_time = Column(String(256))
    runtime = Column(Float)
    prec = Column(Float)
    detection_rate = Column(Float)
    f1_score = Column(Float)
    acc = Column(Float)
    fpr = Column(Float)
    fnr = Column(Float)
    fdr = Column(Float)
    avg_cpu_usage = Column(Float)
    avg_memory_usage = Column(Float)
    resource_query_mode = Column(String(32))
    resource_query_targets = Column(Text)

async def add_benchmarking_result(db: AsyncSession, result: BenchmarkingResult):
    db.add(result)
    await db.commit() 
    await db.refresh(result)  
    
async def get_all_benchmarking_results(db: AsyncSession):
    stmt = select(BenchmarkingResult)
    result = await db.execute(stmt)
    return result.scalars().all()  


async def get_benchmarking_result_by_id(db: AsyncSession, result_id: int):
    stmt = select(BenchmarkingResult).where(BenchmarkingResult.id == result_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


class BenchmarkingJob(Base):
    __tablename__ = "benchmarking_job"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(32), nullable=False, default=BENCHMARK_JOB_STATUS_QUEUED)
    total_runs = Column(Integer, nullable=False, default=0)
    completed_runs = Column(Integer, nullable=False, default=0)
    settle_seconds = Column(Integer, nullable=False, default=5)
    repeat_count = Column(Integer, nullable=False, default=1)
    stop_requested = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(64), nullable=False, default=get_timestamp)
    started_at = Column(String(64))
    completed_at = Column(String(64))
    error = Column(Text)

    items = relationship(
        "BenchmarkingJobItem",
        back_populates="job",
        cascade="all, delete",
        lazy="selectin",
        order_by="BenchmarkingJobItem.position",
    )


class BenchmarkingJobItem(Base):
    __tablename__ = "benchmarking_job_item"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("benchmarking_job.id"), nullable=False)
    position = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default=BENCHMARK_ITEM_STATUS_PENDING)
    target_type = Column(String(32), nullable=False)
    target_id = Column(Integer, nullable=False)
    target_name = Column(String(256), nullable=False)
    dataset_id = Column(Integer, nullable=False)
    dataset_name = Column(String(256), nullable=False)
    configuration_id = Column(Integer)
    configuration_name = Column(String(256))
    ruleset_id = Column(Integer)
    ruleset_name = Column(String(256))
    repeat_index = Column(Integer, nullable=False, default=1)
    repeat_total = Column(Integer, nullable=False, default=1)
    started_at = Column(String(64))
    completed_at = Column(String(64))
    error = Column(Text)

    job = relationship("BenchmarkingJob", back_populates="items")


def serialize_benchmarking_job_item(item: BenchmarkingJobItem) -> dict:
    return {
        "id": item.id,
        "job_id": item.job_id,
        "position": item.position,
        "status": item.status,
        "target_type": item.target_type,
        "target_id": item.target_id,
        "target_name": item.target_name,
        "dataset_id": item.dataset_id,
        "dataset_name": item.dataset_name,
        "configuration_id": item.configuration_id,
        "configuration_name": item.configuration_name,
        "ruleset_id": item.ruleset_id,
        "ruleset_name": item.ruleset_name,
        "repeat_index": item.repeat_index,
        "repeat_total": item.repeat_total,
        "started_at": item.started_at,
        "completed_at": item.completed_at,
        "error": item.error,
    }


def serialize_benchmarking_job(job: BenchmarkingJob) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "total_runs": job.total_runs,
        "completed_runs": job.completed_runs,
        "settle_seconds": job.settle_seconds,
        "repeat_count": job.repeat_count,
        "stop_requested": job.stop_requested,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error": job.error,
        "items": [serialize_benchmarking_job_item(item) for item in job.items],
    }


async def add_benchmarking_job(
    db: AsyncSession, job: BenchmarkingJob, items: list[BenchmarkingJobItem]
) -> BenchmarkingJob:
    job.total_runs = len(items)
    job.items = items
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_benchmarking_job_by_id(db: AsyncSession, job_id: int):
    stmt = (
        select(BenchmarkingJob)
        .options(selectinload(BenchmarkingJob.items))
        .where(BenchmarkingJob.id == job_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_benchmarking_jobs(db: AsyncSession, limit: int = 20):
    stmt = (
        select(BenchmarkingJob)
        .options(selectinload(BenchmarkingJob.items))
        .order_by(BenchmarkingJob.id.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_next_runnable_benchmarking_job(db: AsyncSession):
    stmt = (
        select(BenchmarkingJob)
        .options(selectinload(BenchmarkingJob.items))
        .where(
            BenchmarkingJob.status.in_(
                [BENCHMARK_JOB_STATUS_QUEUED, BENCHMARK_JOB_STATUS_RUNNING]
            )
        )
        .order_by(BenchmarkingJob.id.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def mark_interrupted_benchmarking_jobs_as_queued(db: AsyncSession):
    stmt = (
        select(BenchmarkingJob)
        .options(selectinload(BenchmarkingJob.items))
        .where(BenchmarkingJob.status == BENCHMARK_JOB_STATUS_RUNNING)
    )
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    for job in jobs:
        job.status = BENCHMARK_JOB_STATUS_QUEUED
        job.error = "Core restarted while this benchmark was running; pending work was queued again."
        for item in job.items:
            if item.status == BENCHMARK_ITEM_STATUS_RUNNING:
                item.status = BENCHMARK_ITEM_STATUS_PENDING
                item.started_at = None
                item.error = "Core restarted before this run completed."
    if jobs:
        await db.commit()


async def refresh_benchmarking_job_progress(db: AsyncSession, job: BenchmarkingJob):
    completed_statuses = {
        BENCHMARK_ITEM_STATUS_COMPLETED,
        BENCHMARK_ITEM_STATUS_CANCELLED,
        BENCHMARK_ITEM_STATUS_FAILED,
    }
    job.completed_runs = len(
        [item for item in job.items if item.status in completed_statuses]
    )
    await db.commit()
    await db.refresh(job)


async def ensure_benchmarking_queue_tables():
    if engine is None:
        return

    async with engine.begin() as connection:
        await connection.run_sync(BenchmarkingJob.__table__.create, checkfirst=True)
        await connection.run_sync(BenchmarkingJobItem.__table__.create, checkfirst=True)
        await connection.execute(
            text(
                "ALTER TABLE benchmarking_job "
                "ADD COLUMN IF NOT EXISTS repeat_count INT NOT NULL DEFAULT 1"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE benchmarking_job_item "
                "ADD COLUMN IF NOT EXISTS repeat_index INT NOT NULL DEFAULT 1"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE benchmarking_job_item "
                "ADD COLUMN IF NOT EXISTS repeat_total INT NOT NULL DEFAULT 1"
            )
        )
