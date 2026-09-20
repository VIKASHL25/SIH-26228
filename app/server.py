import os
import sys
import json

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

from cv_assurance.governance.engine import AssuranceEngine
from cv_assurance.provenance.crypto_binding import CryptographicProvenanceEngine, InferenceOutputPrediction
from cv_assurance.model.hasher import ModelHasher

app = FastAPI(
    title="Trustworthy CV Assurance Dashboard API",
    version="1.0.0"
)

# Initialize Core Engine
engine = AssuranceEngine()
prov_engine = CryptographicProvenanceEngine()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
DEMO_DIR = os.path.join(BASE_DIR, "demo_assets")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/demo_assets", StaticFiles(directory=DEMO_DIR), name="demo_assets")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/style.css")
async def get_style():
    return FileResponse(os.path.join(STATIC_DIR, "style.css"))

@app.get("/app.js")
async def get_app_js():
    return FileResponse(os.path.join(STATIC_DIR, "app.js"))

@app.get("/api/health")
async def health_check():
    return {"status": "online", "system": "Trustworthy CV Integrity Assurance Engine v1.0.0"}

@app.get("/api/run_demo_analysis")
async def run_demo_analysis():
    eval_coco = os.path.join(DEMO_DIR, "eval_coco", "annotations.json")
    ref_coco = os.path.join(DEMO_DIR, "reference_coco", "annotations.json")
    model_pt = os.path.join(DEMO_DIR, "sample_model.pt")

    if not os.path.exists(eval_coco):
        raise HTTPException(status_code=404, detail="Demo dataset files not generated.")

    report = engine.run_full_assurance(
        dataset_path=eval_coco,
        model_path=model_pt,
        ref_dataset_path=ref_coco
    )
    return JSONResponse(content=report.model_dump(mode='json'))

@app.post("/api/verify_inference_record")
async def verify_record_endpoint(record: dict):
    from cv_assurance.provenance.crypto_binding import ProtectedInferenceRecord
    try:
        rec = ProtectedInferenceRecord(**record)
        res = prov_engine.verify_record(rec)
        return JSONResponse(content=res.model_dump(mode='json'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/create_inference_record")
async def create_record_endpoint(
    image_hash: str = Form(...),
    model_hash: str = Form(...),
    predictions_json: str = Form(...)
):
    try:
        preds_list = json.loads(predictions_json)
        preds = [InferenceOutputPrediction(**p) for p in preds_list]
        rec = prov_engine.create_protected_record(
            image_path_or_hash=image_hash,
            model_hash=model_hash,
            config_dict={"resolution": [640, 640]},
            predictions=preds
        )
        return JSONResponse(content=rec.model_dump(mode='json'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
