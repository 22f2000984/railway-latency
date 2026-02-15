from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI()

# Configure CORS middleware - MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load telemetry data
def load_telemetry_data():
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "telemetry_data.json"),
        "api/telemetry_data.json",
        "telemetry_data.json",
    ]
    
    for path in possible_paths:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            continue
    return []

# Request model
class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# Calculate statistics for a region
def calculate_region_stats(data: List[dict], region: str, threshold_ms: float) -> dict:
    region_data = [d for d in data if d.get("region") == region]
    
    if not region_data:
        return {
            "avg_latency": 0,
            "p95_latency": 0,
            "avg_uptime": 0,
            "breaches": 0
        }
    
    latencies = [d.get("latency_ms", 0) for d in region_data]
    uptimes = [d.get("uptime_pct", 0) for d in region_data]
    
    # Average latency
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    # P95 latency (95th percentile)
    sorted_latencies = sorted(latencies)
    p95_index = int(len(sorted_latencies) * 0.95)
    if p95_index >= len(sorted_latencies):
        p95_index = len(sorted_latencies) - 1
    p95_latency = sorted_latencies[p95_index] if sorted_latencies else 0
    
    # Average uptime
    avg_uptime = sum(uptimes) / len(uptimes) if uptimes else 0
    
    # Breaches (count of records above threshold)
    breaches = sum(1 for lat in latencies if lat > threshold_ms)
    
    return {
        "avg_latency": round(avg_latency, 2),
        "p95_latency": round(p95_latency, 2),
        "avg_uptime": round(avg_uptime, 2),
        "breaches": breaches
    }

# Handle OPTIONS preflight request explicitly
@app.options("/")
async def options_handler():
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/")
async def root():
    return {"message": "Railway Latency API", "status": "healthy"}

@app.post("/")
async def process_telemetry(request: TelemetryRequest):
    data = load_telemetry_data()
    
    result = {}
    for region in request.regions:
        result[region] = calculate_region_stats(data, region, request.threshold_ms)
    
    return result