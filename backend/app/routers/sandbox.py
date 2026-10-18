"""
backend/app/routers/sandbox.py

API router for Novelty 5: Interactive Leftover Combos Sandbox
"""

from fastapi import APIRouter
from backend.app.services.sandbox_engine import sandbox_engine, SandboxSimulateRequest, SandboxSimulationResponse

router = APIRouter(
    prefix="/sandbox",
    tags=["sandbox"],
)

@router.post(
    "/simulate",
    response_model=SandboxSimulationResponse,
    summary="Simulate live ingredient toggles, objective weight sliders, and recommendation clusters",
)
def simulate_sandbox(request: SandboxSimulateRequest) -> SandboxSimulationResponse:
    return sandbox_engine.simulate(request)
