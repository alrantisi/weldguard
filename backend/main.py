import os
import json
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio

app = FastAPI(title="WeldGuard Backend API")

# --- CORS Middleware ---
# Mengizinkan frontend/dashboard untuk fetch API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Untuk production, ganti dengan origin spesifik
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Path Configurations ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "snapshots")
DATA_FILE = os.path.join(BASE_DIR, "data.json")

os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

# --- Mount Static Files ---
# Untuk menyajikan gambar snapshot
app.mount("/snapshots", StaticFiles(directory=SNAPSHOTS_DIR), name="snapshots")

# --- In-Memory Database ---
# Format JSON:
# {
#   "stations": {
#      "LAS-01": {"status": "safe", "machine": "ON", "last_update": "...", "apd_status": {...}},
#      ...
#   },
#   "incidents": [
#      {"id": "INC-001", "station": "LAS-01", "type": "Helm Tidak Terdeteksi", ...}
#   ]
# }

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "stations": {
            # Mock initial station
            "LAS-01": {
                "name": "Stasiun Las 1",
                "worker": "Ahmad Fauzi",
                "uid": "A1B2C3D4",
                "status": "idle",
                "machine": "OFF",
                "last_update": "",
                "apd_status": {
                    "welding_helmet": False,
                    "face_shield": False,
                    "safety_glasses": False
                }
            }
        },
        "incidents": []
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()

# --- Pydantic Models ---
class IncidentPayload(BaseModel):
    station: str
    timestamp: str
    missing_apd: List[str]
    snapshot_file: str
    severity: str
    type: str

class StationStatusPayload(BaseModel):
    station: str
    timestamp: str
    is_violation: bool
    apd_status: dict
    machine: str

# --- State untuk Video Streaming ---
latest_frames = {}
frame_events = {}

# --- API Endpoints ---

@app.get("/api/status")
def get_status():
    """Mengembalikan status semua stasiun."""
    return {"status": "success", "data": db["stations"]}

@app.post("/api/status")
def update_status(payload: StationStatusPayload):
    """Menerima update status real-time dari inference engine."""
    station_id = payload.station
    
    if station_id not in db["stations"]:
        # Register new station if not exists
        db["stations"][station_id] = {
            "name": f"Stasiun {station_id}",
            "worker": "Unknown Worker",
            "uid": "-",
        }
        
    station = db["stations"][station_id]
    station["status"] = "danger" if payload.is_violation else "safe"
    station["machine"] = payload.machine
    station["last_update"] = payload.timestamp
    station["apd_status"] = payload.apd_status
    
    # Save sporadically or let it be in-memory for speed
    save_data(db)
    
    return {"status": "success", "message": "Status updated"}

@app.get("/api/incidents")
def get_incidents():
    """Mengembalikan log insiden terbaru."""
    # Return sorted by timestamp descending
    incidents = sorted(db["incidents"], key=lambda x: x.get("time", ""), reverse=True)
    return {"status": "success", "data": incidents}

@app.post("/api/incidents")
def add_incident(payload: IncidentPayload):
    """Menerima laporan insiden dari inference engine."""
    incident_id = f"INC-{len(db['incidents']) + 1:03d}"
    
    # Dapatkan nama pekerja dari station
    worker_name = "Unknown Worker"
    uid = "-"
    if payload.station in db["stations"]:
        worker_name = db["stations"][payload.station].get("worker", "Unknown Worker")
        uid = db["stations"][payload.station].get("uid", "-")
    
    new_incident = {
        "id": incident_id,
        "time": payload.timestamp.replace("T", " ")[:19], # Format: YYYY-MM-DD HH:MM:SS
        "station": payload.station,
        "worker": worker_name,
        "uid": uid,
        "type": payload.type,
        "severity": payload.severity,
        "snapshot": f"/snapshots/{payload.snapshot_file}"
    }
    
    db["incidents"].append(new_incident)
    save_data(db)
    
    return {"status": "success", "message": "Incident logged", "incident_id": incident_id}

@app.get("/api/stats")
def get_stats():
    """Mengembalikan statistik untuk dashboard KPI."""
    stations = db["stations"].values()
    active_stations = sum(1 for s in stations if s.get("status") in ["safe", "danger"])
    total_stations = len(stations) or 1
    
    # Hitung compliance (stasiun safe / stasiun aktif)
    safe_stations = sum(1 for s in stations if s.get("status") == "safe")
    compliance = 0
    if active_stations > 0:
        compliance = int((safe_stations / active_stations) * 100)
    elif len(db["incidents"]) == 0:
        compliance = 100
        
    # Insiden hari ini
    today = datetime.now().strftime("%Y-%m-%d")
    incidents_today = sum(1 for inc in db["incidents"] if inc.get("time", "").startswith(today))
    
    return {
        "status": "success", 
        "data": {
            "active_stations": active_stations,
            "total_stations": total_stations,
            "compliance_score": compliance,
            "incidents_today": incidents_today,
            "active_workers": 5 # Mock for now
        }
    }

@app.post("/api/frame/{station_id}")
async def upload_frame(station_id: str, request: Request):
    """Menerima live frame JPEG dari Inference Engine"""
    body = await request.body()
    latest_frames[station_id] = body
    if station_id in frame_events:
        frame_events[station_id].set()
    return {"status": "success"}

async def frame_generator(station_id: str):
    """Generator untuk menghasilkan stream MJPEG untuk banyak klien"""
    last_frame = None
    timeout_counter = 0
    
    while True:
        frame = latest_frames.get(station_id)
        if frame and frame != last_frame:
            last_frame = frame
            timeout_counter = 0
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            timeout_counter += 1
            if timeout_counter > 40:  # ~2 detik (40 * 0.05s) tidak ada frame baru
                break
        await asyncio.sleep(0.05)

@app.get("/api/video_feed/{station_id}")
async def video_feed(station_id: str):
    """Streaming video feed untuk HTML `img src`"""
    return StreamingResponse(
        frame_generator(station_id), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Starting WeldGuard Backend API...")
    print("Mendengarkan di port 8000")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
