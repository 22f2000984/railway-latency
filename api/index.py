from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI()

# Configure CORS middleware
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

# Calculate P95 using linear interpolation (numpy-style)
def calculate_p95(values: List[float]) -> float:
    if not values:
        return 0
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    # Use linear interpolation method (same as numpy.percentile default)
    index = 0.95 * (n - 1)
    lower = int(index)
    upper = lower + 1
    fraction = index - lower
    
    if upper >= n:
        return sorted_values[-1]
    
    return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])

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
    
    # P95 latency (95th percentile with interpolation)
    p95_latency = calculate_p95(latencies)
    
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

@app.get("/")
async def root():
    return {"message": "Railway Latency API", "status": "healthy"}

@app.post("/")
async def process_telemetry(request: TelemetryRequest):
    data = load_telemetry_data()
    
    regions_result = {}
    for region in request.regions:
        regions_result[region] = calculate_region_stats(data, region, request.threshold_ms)
    
    return {"regions": regions_result}