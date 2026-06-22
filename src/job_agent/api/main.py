from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from job_agent.api.routes import jobs

app = FastAPI(title="求职分析与投递助手", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
