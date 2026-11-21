from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import engine
import llm
from router import route


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on application startup."""
    db.init_db()
    yield


app = FastAPI(title="AquaCompute", lifespan=lifespan)


class ChatRequest(BaseModel):
    prompt: str
    region: str = "IN"


@app.get("/health")
def health() -> dict:
    """Return application health status."""
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    """Process a chat prompt with tier routing, LLM generation, and footprint estimation."""
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")

    routing = route(req.prompt)
    tier = routing["tier"]
    model_info = llm.TIER_MODELS[tier]

    try:
        answer = llm.ask(req.prompt, model_info["id"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    in_tokens = answer["input_tokens"]
    out_tokens = answer["output_tokens"]

    fp = engine.estimate(tier, in_tokens, out_tokens, req.region)
    baseline = engine.estimate("large", in_tokens, out_tokens, req.region)

    db.save_run(
        {
            "prompt": req.prompt,
            "tier": tier,
            "model_name": model_info["name"],
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "reason": routing["reason"],
            "energy_kwh": fp["energy_kwh"],
            "direct_water_l": fp["direct_water_l"],
            "indirect_water_l": fp["indirect_water_l"],
            "water_l": fp["water_l"],
            "carbon_g": fp["carbon_g"],
            "baseline_water_l": baseline["water_l"],
        }
    )

    return {
        "reply": answer["text"],
        "routing": {
            "tier": tier,
            "model_name": model_info["name"],
            "model_id": model_info["id"],
            "reason": routing["reason"],
            "estimated_tokens": routing["tokens"],
        },
        "usage": {
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
        },
        "footprint": fp,
    }


@app.get("/history")
def history() -> dict:
    """Return historical runs and cumulative footprint totals."""
    runs = db.list_runs()
    total_reqs = len(runs)
    total_energy = round(sum(r["energy_kwh"] for r in runs), 6)
    total_water = round(sum(r["water_l"] for r in runs), 6)
    total_carbon = round(sum(r["carbon_g"] for r in runs), 4)
    total_baseline = round(sum(r["baseline_water_l"] for r in runs), 6)

    saved_percent = (
        round((1.0 - (total_water / total_baseline)) * 100)
        if total_reqs > 0 and total_baseline > 0
        else 0
    )

    return {
        "runs": runs,
        "totals": {
            "requests": total_reqs,
            "energy_kwh": total_energy,
            "water_l": total_water,
            "carbon_g": total_carbon,
            "baseline_water_l": total_baseline,
            "saved_percent": saved_percent,
        },
    }


# Mount static files for the frontend after API routes
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
frontend_dir.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
