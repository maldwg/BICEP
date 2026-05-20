from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.benchmarking_queue import start_benchmarking_worker
from app.database import get_db
from app.logger import LOGGER
from app.models.benchmarking import (
    BENCHMARK_JOB_STATUS_CANCELLED,
    BENCHMARK_JOB_STATUS_COMPLETED,
    BENCHMARK_JOB_STATUS_FAILED,
    BENCHMARK_TARGET_CONTAINER,
    BENCHMARK_TARGET_ENSEMBLE,
    BenchmarkingJob,
    BenchmarkingJobItem,
    add_benchmarking_job,
    get_all_benchmarking_jobs,
    get_benchmarking_job_by_id,
    serialize_benchmarking_job,
)
from app.models.configuration import get_config_by_id
from app.models.dataset import get_dataset_by_id
from app.models.ensemble import get_ensemble_by_id
from app.models.ids_system import get_ids_system_by_id
from app.models.ids_tool import get_ids_by_id


router = APIRouter(prefix="/benchmarking")


class BenchmarkTargetSelection(BaseModel):
    target_type: Literal["container", "ensemble"]
    target_id: int
    configuration_ids: list[int] = Field(default_factory=list)
    ruleset_ids: list[int] = Field(default_factory=list)


class BenchmarkJobCreate(BaseModel):
    targets: list[BenchmarkTargetSelection]
    dataset_ids: list[int]
    settle_seconds: int = Field(default=5, ge=0, le=300)
    repeat_count: int = Field(default=1, ge=1, le=100)


@router.post("/jobs")
async def create_benchmarking_job(job_data: BenchmarkJobCreate, db=Depends(get_db)):
    if not job_data.targets:
        return JSONResponse({"error": "Select at least one IDS or ensemble."}, status_code=400)
    if not job_data.dataset_ids:
        return JSONResponse({"error": "Select at least one dataset."}, status_code=400)

    try:
        datasets = []
        for dataset_id in _unique(job_data.dataset_ids):
            dataset = await get_dataset_by_id(db, dataset_id)
            if dataset is None:
                return JSONResponse(
                    {"error": f"Dataset {dataset_id} was not found."}, status_code=404
                )
            datasets.append(dataset)

        items: list[BenchmarkingJobItem] = []
        position = 1
        for target in job_data.targets:
            created_items = await _create_items_for_target(
                db, target, datasets, position, job_data.repeat_count
            )
            items.extend(created_items)
            position += len(created_items)

        if not items:
            return JSONResponse(
                {"error": "The selected benchmark scope did not create any runs."},
                status_code=400,
            )

        job = BenchmarkingJob(
            settle_seconds=job_data.settle_seconds,
            repeat_count=job_data.repeat_count,
        )
        job = await add_benchmarking_job(db, job, items)
        serialized_job = serialize_benchmarking_job(job)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        LOGGER.error(f"Could not create benchmarking job: {exc}")
        return JSONResponse({"error": str(exc)}, status_code=500)

    await start_benchmarking_worker()
    return JSONResponse({"content": serialized_job}, status_code=202)


@router.get("/jobs")
async def list_benchmarking_jobs(limit: int = 20, db=Depends(get_db)):
    limit = max(1, min(limit, 100))
    jobs = await get_all_benchmarking_jobs(db, limit=limit)
    return {"content": [serialize_benchmarking_job(job) for job in jobs]}


@router.get("/jobs/{job_id}")
async def get_benchmarking_job(job_id: int, db=Depends(get_db)):
    job = await get_benchmarking_job_by_id(db, job_id)
    if job is None:
        return JSONResponse({"error": f"Benchmarking job {job_id} was not found."}, status_code=404)
    return {"content": serialize_benchmarking_job(job)}


@router.post("/jobs/{job_id}/stop")
async def stop_benchmarking_job(job_id: int, db=Depends(get_db)):
    job = await get_benchmarking_job_by_id(db, job_id)
    if job is None:
        return JSONResponse({"error": f"Benchmarking job {job_id} was not found."}, status_code=404)

    if job.status in [
        BENCHMARK_JOB_STATUS_COMPLETED,
        BENCHMARK_JOB_STATUS_CANCELLED,
        BENCHMARK_JOB_STATUS_FAILED,
    ]:
        return {"content": serialize_benchmarking_job(job)}

    job.stop_requested = True
    await db.commit()
    await db.refresh(job)
    await start_benchmarking_worker()
    return {"content": serialize_benchmarking_job(job)}


async def _create_items_for_target(
    db, target, datasets, start_position: int, repeat_count: int
):
    target_type = target.target_type.lower()
    if target_type == BENCHMARK_TARGET_CONTAINER:
        return await _create_container_items(
            db, target, datasets, start_position, repeat_count
        )
    if target_type == BENCHMARK_TARGET_ENSEMBLE:
        return await _create_ensemble_items(
            db, target, datasets, start_position, repeat_count
        )
    raise ValueError(f"Unsupported benchmark target type: {target.target_type}")


async def _create_container_items(db, target, datasets, start_position: int, repeat_count: int):
    container = await get_ids_system_by_id(db, target.target_id)
    if container is None:
        raise ValueError(f"Container {target.target_id} was not found.")
    if container.ensemble_ids:
        raise ValueError(
            f"Container {container.name} is part of an ensemble. Select the ensemble instead."
        )

    ids_tool = await get_ids_by_id(db, container.ids_tool_id)
    configuration_ids = _unique(target.configuration_ids) or [container.configuration_id]
    ruleset_ids = _unique(target.ruleset_ids) or (
        [container.ruleset_id] if container.ruleset_id else [None]
    )

    if ids_tool and ids_tool.requires_ruleset and ruleset_ids == [None]:
        raise ValueError(f"Container {container.name} requires at least one ruleset.")

    configuration_names = {}
    for configuration_id in configuration_ids:
        configuration = await get_config_by_id(db, configuration_id)
        if configuration is None:
            raise ValueError(f"Configuration {configuration_id} was not found.")
        configuration_names[configuration_id] = configuration.name

    ruleset_names = {None: None}
    for ruleset_id in [ruleset_id for ruleset_id in ruleset_ids if ruleset_id is not None]:
        ruleset = await get_config_by_id(db, ruleset_id)
        if ruleset is None:
            raise ValueError(f"Ruleset {ruleset_id} was not found.")
        ruleset_names[ruleset_id] = ruleset.name

    items = []
    position = start_position
    for configuration_id in configuration_ids:
        for ruleset_id in ruleset_ids:
            for dataset in datasets:
                for repeat_index in range(1, repeat_count + 1):
                    items.append(
                        BenchmarkingJobItem(
                            position=position,
                            target_type=BENCHMARK_TARGET_CONTAINER,
                            target_id=container.id,
                            target_name=container.name,
                            dataset_id=dataset.id,
                            dataset_name=dataset.name,
                            configuration_id=configuration_id,
                            configuration_name=configuration_names.get(configuration_id),
                            ruleset_id=ruleset_id,
                            ruleset_name=ruleset_names.get(ruleset_id),
                            repeat_index=repeat_index,
                            repeat_total=repeat_count,
                        )
                    )
                    position += 1
    return items


async def _create_ensemble_items(db, target, datasets, start_position: int, repeat_count: int):
    ensemble = await get_ensemble_by_id(db, target.target_id)
    if ensemble is None:
        raise ValueError(f"Ensemble {target.target_id} was not found.")

    containers = await ensemble.get_assigned_containers(db)
    if not containers:
        raise ValueError(f"Ensemble {ensemble.name} has no assigned IDS containers.")

    items = []
    position = start_position
    for dataset in datasets:
        for repeat_index in range(1, repeat_count + 1):
            items.append(
                BenchmarkingJobItem(
                    position=position,
                    target_type=BENCHMARK_TARGET_ENSEMBLE,
                    target_id=ensemble.id,
                    target_name=ensemble.name,
                    dataset_id=dataset.id,
                    dataset_name=dataset.name,
                    repeat_index=repeat_index,
                    repeat_total=repeat_count,
                )
            )
            position += 1
    return items


def _unique(values: list[int]) -> list[int]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
