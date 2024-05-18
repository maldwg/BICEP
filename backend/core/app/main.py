from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import ids

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(ids.router)

@app.get("/")
async def main():
    return {"message": "Hello World"}