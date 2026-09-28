from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.routers import analytics, anomaly, behavior, clustering, datasets, evidence, graph, graph_analysis, risk
from app.services.graph import ensure_schema_constraints


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure Neo4j schema constraints on startup if Neo4j is reachable
    try:
        ensure_schema_constraints()
    except Exception as e:
        print(f"Notice: Neo4j schema constraint initialization deferred: {e}")
    yield


app = FastAPI(
    title="Bitcoin Transaction Intelligence & Investigation Platform",
    version="0.1.0",
    description="Offline-first foundation API for Bitcoin transaction and network metadata analysis.",
    lifespan=lifespan,
)

# Enable CORS for local development across frontend ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
@app.get("/api/v1/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="bitcoin-intelligence-backend",
    )


# Register API Routers
app.include_router(datasets.router)
app.include_router(analytics.router)
app.include_router(graph.router)
app.include_router(graph_analysis.router)
app.include_router(anomaly.router)
app.include_router(clustering.router)
app.include_router(behavior.router)
app.include_router(risk.router)
app.include_router(evidence.router)

