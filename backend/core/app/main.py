from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import crud, ids, ensemble
app = FastAPI()

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


@app.on_event("startup")
async def startup_event():
    app.state.background_tasks = set()
    app.state.stream_metric_tasks = {}


app.include_router(ids.router)
app.include_router(crud.router)
app.include_router(ensemble.router)
