from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import numpy as np
from pathlib import Path
from typing import List

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    # allow_methods=["POST","OPTIONS","GET"],
    llow_methods=["*"],
    allow_headers=["*"],
)


class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float


class RegionMetrics(BaseModel):
    avg_latency: float
    p95_latency: float
    avg_uptime: float
    breaches: int


def load_telemetry_data():
    """Load telemetry data from JSON file."""
    data_path = Path(__file__).parent / "telemetry_data.json"
    with open(data_path, "r") as f:
        return json.load(f)


def calculate_metrics(records: list, threshold_ms: float) -> RegionMetrics:
    """Calculate metrics for a list of telemetry records."""
    if not records:
        return RegionMetrics(
            avg_latency=0.0,
            p95_latency=0.0,
            avg_uptime=0.0,
            breaches=0
        )
    
    latencies = [r["latency_ms"] for r in records]
    uptimes = [r["uptime_pct"] for r in records]
    
    avg_latency = round(np.mean(latencies), 2)
    p95_latency = round(np.percentile(latencies, 95), 2)
    avg_uptime = round(np.mean(uptimes), 2)
    breaches = sum(1 for lat in latencies if lat > threshold_ms)
    
    return RegionMetrics(
        avg_latency=avg_latency,
        p95_latency=p95_latency,
        avg_uptime=avg_uptime,
        breaches=breaches
    )


@app.post("/")
async def process_telemetry(request: TelemetryRequest):
    """
    Process telemetry data and return metrics per region.
    """
    telemetry_data = load_telemetry_data()
    
    results = {}
    
    for region in request.regions:
        region_records = [
            record for record in telemetry_data 
            if record["region"].lower() == region.lower()
        ]
        metrics = calculate_metrics(region_records, request.threshold_ms)
        results[region] = metrics.model_dump()
    
    return results