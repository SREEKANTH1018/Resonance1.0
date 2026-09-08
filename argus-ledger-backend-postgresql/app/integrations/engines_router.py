from fastapi import APIRouter, HTTPException

from .engines import engine_names, engine_status, get_engine

# Wire this into your FastAPI app the same way app/integrations/router.py is:
#     from app.integrations.engines_router import router as engines_router
#     app.include_router(engines_router)

router = APIRouter(prefix="/engines", tags=["engines"])


@router.get("/status")
async def status():
    # For each engine: mode, whether it is enabled, and the exact env vars still
    # missing. This is the artifact to send your teammate for the handoff.
    return {"engines": engine_status()}


@router.post("/{name}/infer")
async def infer(name: str, payload: dict):
    try:
        engine = get_engine(name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown engine '{name}'. Known: {engine_names()}",
        )
    return await engine.infer(payload)
