import asyncio
from fastapi.responses import Response

from app.database import SessionLocal
from app.logger import LOGGER
from app.models.benchmarking import (
    BENCHMARK_ITEM_STATUS_CANCELLED,
    BENCHMARK_ITEM_STATUS_COMPLETED,
    BENCHMARK_ITEM_STATUS_FAILED,
    BENCHMARK_ITEM_STATUS_PENDING,
    BENCHMARK_ITEM_STATUS_RUNNING,
    BENCHMARK_JOB_STATUS_CANCELLED,
    BENCHMARK_JOB_STATUS_COMPLETED,
    BENCHMARK_JOB_STATUS_FAILED,
    BENCHMARK_JOB_STATUS_QUEUED,
    BENCHMARK_JOB_STATUS_RUNNING,
    BENCHMARK_TARGET_CONTAINER,
    BENCHMARK_TARGET_ENSEMBLE,
    BenchmarkingJob,
    BenchmarkingJobItem,
    get_benchmarking_job_by_id,
    get_next_runnable_benchmarking_job,
    get_timestamp,
    refresh_benchmarking_job_progress,
)
from app.models.configuration import get_config_by_id
from app.models.ensemble import get_ensemble_by_id, update_ensemble_status
from app.models.ids_system import get_ids_system_by_id, update_ids_status
from app.utils import STATUS
from app.validation.models import StaticAnalysisData, stop_analysisData


POLL_INTERVAL_SECONDS = 2

_worker_task: asyncio.Task | None = None
_worker_start_lock = asyncio.Lock()


async def start_benchmarking_worker():
    global _worker_task
    async with _worker_start_lock:
        if _worker_task is None or _worker_task.done():
            _worker_task = asyncio.create_task(_run_benchmarking_worker())


async def stop_benchmarking_worker():
    global _worker_task
    if _worker_task is None or _worker_task.done():
        return
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass


async def _run_benchmarking_worker():
    while True:
        if SessionLocal is None:
            LOGGER.error("Benchmarking queue cannot start without a database session.")
            return

        async with SessionLocal() as db:
            job = await get_next_runnable_benchmarking_job(db)

        if job is None:
            return

        await _run_job(job.id)


async def _run_job(job_id: int):
    while True:
        async with SessionLocal() as db:
            job = await get_benchmarking_job_by_id(db, job_id)
            if job is None:
                return

            if job.stop_requested:
                running_item = next(
                    (
                        item
                        for item in job.items
                        if item.status == BENCHMARK_ITEM_STATUS_RUNNING
                    ),
                    None,
                )
                if running_item:
                    await _stop_active_item_if_needed(job_id, running_item.id)
                await _cancel_remaining_job_items(db, job)
                return

            if job.status == BENCHMARK_JOB_STATUS_QUEUED:
                job.status = BENCHMARK_JOB_STATUS_RUNNING
                job.started_at = job.started_at or get_timestamp()
                await db.commit()

            next_item = _get_next_pending_item(job)
            if next_item is None:
                await _finish_job(db, job)
                return

            next_item.status = BENCHMARK_ITEM_STATUS_RUNNING
            next_item.started_at = get_timestamp()
            next_item.error = None
            job.status = BENCHMARK_JOB_STATUS_RUNNING
            await db.commit()
            item_id = next_item.id

        try:
            item_completed = await _execute_item(job_id, item_id)
        except Exception as exc:
            LOGGER.error(f"Benchmark item {item_id} failed: {exc}")
            item_completed = False
            async with SessionLocal() as db:
                job = await get_benchmarking_job_by_id(db, job_id)
                if job:
                    item = _find_item(job, item_id)
                    if item:
                        item.status = BENCHMARK_ITEM_STATUS_FAILED
                        item.completed_at = get_timestamp()
                        item.error = str(exc)
                    await refresh_benchmarking_job_progress(db, job)

        async with SessionLocal() as db:
            job = await get_benchmarking_job_by_id(db, job_id)
            if job is None:
                return
            await refresh_benchmarking_job_progress(db, job)
            should_stop = job.stop_requested
            has_more_work = _get_next_pending_item(job) is not None
            settle_seconds = job.settle_seconds

        if should_stop:
            await _stop_active_item_if_needed(job_id, item_id)
            async with SessionLocal() as db:
                job = await get_benchmarking_job_by_id(db, job_id)
                if job:
                    await _cancel_remaining_job_items(db, job)
            return

        if item_completed and has_more_work and settle_seconds > 0:
            await _sleep_until_next_run_or_stop(job_id, settle_seconds)


async def _execute_item(job_id: int, item_id: int) -> bool:
    if not await _wait_until_target_ready(job_id, item_id):
        await _mark_item_cancelled(item_id, "Benchmark job was stopped before this run started.")
        return False

    async with SessionLocal() as db:
        job = await get_benchmarking_job_by_id(db, job_id)
        item = _find_item(job, item_id) if job else None
        if item is None:
            return False
        if job.stop_requested:
            await _mark_item_cancelled(item_id, "Benchmark job was stopped before this run started.")
            return False

        if item.target_type == BENCHMARK_TARGET_CONTAINER:
            response = await _start_container_item(db, item)
        elif item.target_type == BENCHMARK_TARGET_ENSEMBLE:
            response = await _start_ensemble_item(db, item)
        else:
            raise ValueError(f"Unknown benchmark target type: {item.target_type}")

        if response.status_code != 200:
            error_text = getattr(response, "body", b"").decode("utf-8", errors="ignore")
            await _mark_item_failed(item_id, error_text or "Benchmark run could not be started.")
            return False

    completed = await _wait_until_target_completed(job_id, item_id)
    if completed:
        await _mark_item_completed(item_id)
        return True

    await _stop_active_item_if_needed(job_id, item_id)
    await _mark_item_cancelled(item_id, "Benchmark job was stopped while this run was active.")
    return False


async def _start_container_item(db, item: BenchmarkingJobItem) -> Response:
    from app.routers.ids import start_static_container_analysis

    container = await get_ids_system_by_id(db, item.target_id)
    if container is None:
        raise ValueError(f"Container {item.target_id} is not available.")

    await _apply_container_configuration(db, container, item)
    return await start_static_container_analysis(
        StaticAnalysisData(container_id=item.target_id, dataset_id=item.dataset_id),
        db=db,
    )


async def _start_ensemble_item(db, item: BenchmarkingJobItem) -> Response:
    from app.routers.ensemble import start_static_ensemble_analysis

    ensemble = await get_ensemble_by_id(db, item.target_id)
    if ensemble is None:
        raise ValueError(f"Ensemble {item.target_id} is not available.")

    return await start_static_ensemble_analysis(
        StaticAnalysisData(ensemble_id=item.target_id, dataset_id=item.dataset_id),
        db=db,
    )


async def _apply_container_configuration(db, container, item: BenchmarkingJobItem):
    if item.configuration_id and item.configuration_id != container.configuration_id:
        configuration = await get_config_by_id(db, item.configuration_id)
        if configuration is None:
            raise ValueError(f"Configuration {item.configuration_id} was not found.")
        await container.update_config(db, item.configuration_id)
        container.configuration_id = item.configuration_id

    if item.ruleset_id and item.ruleset_id != container.ruleset_id:
        ruleset = await get_config_by_id(db, item.ruleset_id)
        if ruleset is None:
            raise ValueError(f"Ruleset {item.ruleset_id} was not found.")
        await container.update_ruleset(db, item.ruleset_id)
        container.ruleset_id = item.ruleset_id

    await db.commit()
    await db.refresh(container)


async def _wait_until_target_ready(job_id: int, item_id: int) -> bool:
    while True:
        async with SessionLocal() as db:
            job = await get_benchmarking_job_by_id(db, job_id)
            item = _find_item(job, item_id) if job else None
            if job is None or item is None:
                return False
            if job.stop_requested:
                return False

            if item.target_type == BENCHMARK_TARGET_CONTAINER:
                container = await get_ids_system_by_id(db, item.target_id)
                if container is None:
                    raise ValueError(f"Container {item.target_id} is not available.")
                if container.status == STATUS.IDLE.value:
                    return True
            elif item.target_type == BENCHMARK_TARGET_ENSEMBLE:
                ensemble = await get_ensemble_by_id(db, item.target_id)
                if ensemble is None:
                    raise ValueError(f"Ensemble {item.target_id} is not available.")
                containers = await ensemble.get_assigned_containers(db)
                all_idle = all(container.status == STATUS.IDLE.value for container in containers)
                if ensemble.status == STATUS.IDLE.value and all_idle:
                    return True

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _sleep_until_next_run_or_stop(job_id: int, settle_seconds: int):
    for _ in range(settle_seconds):
        async with SessionLocal() as db:
            job = await get_benchmarking_job_by_id(db, job_id)
            if job is None or job.stop_requested:
                return
        await asyncio.sleep(1)


async def _wait_until_target_completed(job_id: int, item_id: int) -> bool:
    while True:
        async with SessionLocal() as db:
            job = await get_benchmarking_job_by_id(db, job_id)
            item = _find_item(job, item_id) if job else None
            if job is None or item is None:
                return False
            if job.stop_requested:
                return False

            if item.target_type == BENCHMARK_TARGET_CONTAINER:
                container = await get_ids_system_by_id(db, item.target_id)
                if container is None:
                    raise ValueError(f"Container {item.target_id} is not available.")
                if container.status == STATUS.IDLE.value:
                    return True
            elif item.target_type == BENCHMARK_TARGET_ENSEMBLE:
                ensemble = await get_ensemble_by_id(db, item.target_id)
                if ensemble is None:
                    raise ValueError(f"Ensemble {item.target_id} is not available.")
                containers = await ensemble.get_assigned_containers(db)
                all_idle = all(container.status == STATUS.IDLE.value for container in containers)
                if ensemble.status == STATUS.IDLE.value and all_idle:
                    return True

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _stop_active_item_if_needed(job_id: int, item_id: int):
    async with SessionLocal() as db:
        job = await get_benchmarking_job_by_id(db, job_id)
        item = _find_item(job, item_id) if job else None
        if item is None:
            return

        if item.target_type == BENCHMARK_TARGET_CONTAINER:
            from app.routers.ids import stop_analysis

            await stop_analysis(stop_analysisData(container_id=item.target_id), db=db)
        elif item.target_type == BENCHMARK_TARGET_ENSEMBLE:
            from app.routers.ensemble import stop_ensemble_analysis

            await stop_ensemble_analysis(stop_analysisData(ensemble_id=item.target_id), db=db)


async def _mark_item_completed(item_id: int):
    async with SessionLocal() as db:
        item = await _get_item_by_id(db, item_id)
        if item is None:
            return
        item.status = BENCHMARK_ITEM_STATUS_COMPLETED
        item.completed_at = get_timestamp()
        await db.commit()


async def _mark_item_cancelled(item_id: int, error: str):
    async with SessionLocal() as db:
        item = await _get_item_by_id(db, item_id)
        if item is None:
            return
        item.status = BENCHMARK_ITEM_STATUS_CANCELLED
        item.completed_at = get_timestamp()
        item.error = error
        await db.commit()


async def _mark_item_failed(item_id: int, error: str):
    async with SessionLocal() as db:
        item = await _get_item_by_id(db, item_id)
        if item is None:
            return
        item.status = BENCHMARK_ITEM_STATUS_FAILED
        item.completed_at = get_timestamp()
        item.error = error
        await db.commit()


async def _cancel_remaining_job_items(db, job: BenchmarkingJob):
    for item in job.items:
        if item.status in [BENCHMARK_ITEM_STATUS_PENDING, BENCHMARK_ITEM_STATUS_RUNNING]:
            item.status = BENCHMARK_ITEM_STATUS_CANCELLED
            item.completed_at = get_timestamp()
            item.error = "Benchmark job was stopped by the user."

    job.status = BENCHMARK_JOB_STATUS_CANCELLED
    job.completed_at = get_timestamp()
    await refresh_benchmarking_job_progress(db, job)


async def _finish_job(db, job: BenchmarkingJob):
    failed_items = [item for item in job.items if item.status == BENCHMARK_ITEM_STATUS_FAILED]
    cancelled_items = [
        item for item in job.items if item.status == BENCHMARK_ITEM_STATUS_CANCELLED
    ]
    if cancelled_items:
        job.status = BENCHMARK_JOB_STATUS_CANCELLED
    elif failed_items:
        job.status = BENCHMARK_JOB_STATUS_FAILED
        job.error = f"{len(failed_items)} benchmark run(s) failed."
    else:
        job.status = BENCHMARK_JOB_STATUS_COMPLETED
    job.completed_at = get_timestamp()
    await refresh_benchmarking_job_progress(db, job)


def _get_next_pending_item(job: BenchmarkingJob):
    return next(
        (item for item in job.items if item.status == BENCHMARK_ITEM_STATUS_PENDING),
        None,
    )


def _find_item(job: BenchmarkingJob | None, item_id: int):
    if job is None:
        return None
    return next((item for item in job.items if item.id == item_id), None)


async def _get_item_by_id(db, item_id: int):
    from sqlalchemy.future import select

    result = await db.execute(
        select(BenchmarkingJobItem).where(BenchmarkingJobItem.id == item_id)
    )
    return result.scalar_one_or_none()
