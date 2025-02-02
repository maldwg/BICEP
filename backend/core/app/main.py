from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import crud, ids, ensemble
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.background_tasks = set()
    app.state.stream_metric_tasks = {}
    yield
# @app.on_event("startup")
# async def startup_event():
#     app.state.background_tasks = set()
#     app.state.stream_metric_tasks = {}


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
