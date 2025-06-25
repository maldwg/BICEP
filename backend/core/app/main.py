from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import crud, ids, ensemble
from fastapi_utils.tasks import repeat_every
from app.database import get_db
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await update_availability()
    yield

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

@repeat_every(seconds=15)
@crud.router.patch("/host/{id}/availability")
async def update_availability():
    from app.models.docker_host_system import get_all_hosts
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
    
        