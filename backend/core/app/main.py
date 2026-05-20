import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    benchmarking_jobs,
    benchmarking_metrics,
    crud,
    ensemble,
    ids,
    metric_services,
    monitoring,
)
from app.database import SessionLocal, get_db
from contextlib import asynccontextmanager
from app.models.docker_host_system import get_all_hosts
from app.defaults import ensure_default_maltrail_assets
from app.benchmarking_queue import start_benchmarking_worker, stop_benchmarking_worker
from app.models.benchmarking import (
    ensure_benchmarking_queue_tables,
    mark_interrupted_benchmarking_jobs_as_queued,
)

HOST_AVAILABILITY_CHECK_INTERVAL_SECONDS = int(
    os.getenv("HOST_AVAILABILITY_CHECK_INTERVAL", "5")
)
availability_update_lock = asyncio.Lock()


async def update_availability():

    async with availability_update_lock:
        try:
            db_gen = get_db()
            db = await anext(db_gen)
            try:
                hosts = await get_all_hosts(db=db)
                for host in hosts:
                    await host.update_availability(db)
            finally:
                await db_gen.aclose()
        except Exception as e:
            print(e)


async def update_availability_loop():
    while True:
        await update_availability()
        await asyncio.sleep(HOST_AVAILABILITY_CHECK_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_default_maltrail_assets()
    if SessionLocal is not None:
        await ensure_benchmarking_queue_tables()
        db_gen = get_db()
        db = await anext(db_gen)
        try:
            await mark_interrupted_benchmarking_jobs_as_queued(db)
        finally:
            await db_gen.aclose()
        await start_benchmarking_worker()
    availability_task = asyncio.create_task(update_availability_loop())
    try:
        yield
    finally:
        availability_task.cancel()
        await stop_benchmarking_worker()
        try:
            await availability_task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




app.include_router(ids.router)
app.include_router(crud.router)
app.include_router(ensemble.router)
app.include_router(monitoring.router)
app.include_router(benchmarking_metrics.router)
app.include_router(benchmarking_jobs.router)
app.include_router(metric_services.router)
