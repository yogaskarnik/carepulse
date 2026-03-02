"""
CarePulse Backend - AI-Powered Safety Network for Vulnerable Adults
Connected to care. Detects risks early, alerts caregivers, responds fast.
FastAPI application with WebSocket support
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import json
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

try:
    # Try RapidAPI client first (for MWC Hackathon 2026)
    from nokia_client_rapidapi import NokiaRapidAPIClient as NokiaClient
    USE_RAPIDAPI = True
except ImportError:
    # Fallback to direct Nokia client
    from nokia_client import NokiaClient
    USE_RAPIDAPI = False
from ai_service import AnomalyDetector
from database import DatabaseManager, get_db
from models import Patient, Geofence, Alert, AlertSeverity, LocationHistory, AnomalyScore

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"

# RapidAPI credentials (for MWC Hackathon 2026)
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "network-as-code.p-eu.rapidapi.com")
RAPIDAPI_HEADER_HOST = os.getenv("RAPIDAPI_HEADER_HOST", "network-as-code.nokia.rapidapi.com")

# Direct Nokia API credentials (fallback)
NOKIA_API_TOKEN = os.getenv("NOKIA_API_TOKEN")
NOKIA_ORG_ID = os.getenv("NOKIA_ORG_ID")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./carepulse.db")


class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, patient_id: int):
        await websocket.accept()
        if patient_id not in self.active_connections:
            self.active_connections[patient_id] = []
        self.active_connections[patient_id].append(websocket)

    def disconnect(self, websocket: WebSocket, patient_id: int):
        if patient_id in self.active_connections:
            self.active_connections[patient_id].remove(websocket)

    async def send_update(self, patient_id: int, message: dict):
        if patient_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[patient_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)

            for conn in disconnected:
                self.active_connections[patient_id].remove(conn)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Nokia client based on available credentials
    if USE_RAPIDAPI or RAPIDAPI_KEY:
        # Use RapidAPI client
        print(f"🚀 Initializing RapidAPI client (Mock: {USE_MOCK})")
        app.state.nokia_client = NokiaClient(
            use_mock=USE_MOCK,
            rapidapi_key=RAPIDAPI_KEY,
            rapidapi_host=RAPIDAPI_HOST,
            rapidapi_header_host=RAPIDAPI_HEADER_HOST
        )
    else:
        # Use direct Nokia API client
        print(f"🚀 Initializing Direct Nokia API client (Mock: {USE_MOCK})")
        app.state.nokia_client = NokiaClient(
            use_mock=USE_MOCK,
            api_token=NOKIA_API_TOKEN,
            organization_id=NOKIA_ORG_ID
        )

    app.state.ai_detector = AnomalyDetector(
        use_gemini=not USE_MOCK and bool(GEMINI_API_KEY),  # Enable if API key is set
        api_key=GEMINI_API_KEY
    )
    app.state.db_manager = DatabaseManager(DATABASE_URL)
    await app.state.db_manager.init_db()

    yield

    await app.state.nokia_client.close()


app = FastAPI(
    title="CarePulse API",
    description="Connected to care. An AI-powered safety network that detects risks early, alerts caregivers, and responds fast in emergencies for vulnerable adults.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    phone_number: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    date_of_birth: Optional[datetime] = None
    medical_notes: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @field_validator('medical_notes', 'emergency_contact_name', 'emergency_contact_phone', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v


class GeofenceCreate(BaseModel):
    patient_id: int
    name: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: int = Field(..., ge=50, le=10000)


class MonitoringRequest(BaseModel):
    patient_id: int


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CarePulse",
        "version": "1.0.0",
        "mode": "mock" if USE_MOCK else "production",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/patients")
async def create_patient(patient: PatientCreate, db=Depends(get_db)):
    """Create a new patient profile"""
    try:
        db_patient = Patient(
            caregiver_id=None,
            full_name=patient.full_name,
            phone_number=patient.phone_number,
            date_of_birth=patient.date_of_birth,
            medical_notes=patient.medical_notes,
            emergency_contact_name=patient.emergency_contact_name,
            emergency_contact_phone=patient.emergency_contact_phone
        )
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)

        return {
            "id": db_patient.id,
            "full_name": db_patient.full_name,
            "phone_number": db_patient.phone_number,
            "created_at": db_patient.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/patients")
async def list_patients(db=Depends(get_db)):
    """List all patients"""
    patients = db.query(Patient).filter(Patient.active == True).all()
    return [
        {
            "id": p.id,
            "full_name": p.full_name,
            "phone_number": p.phone_number,
            "emergency_contact_name": p.emergency_contact_name,
            "created_at": p.created_at.isoformat()
        }
        for p in patients
    ]


@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: int, db=Depends(get_db)):
    """Get patient details"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    geofences = db.query(Geofence).filter(
        Geofence.patient_id == patient_id,
        Geofence.active == True
    ).all()

    recent_alerts = db.query(Alert).filter(
        Alert.patient_id == patient_id
    ).order_by(Alert.created_at.desc()).limit(10).all()

    return {
        "id": patient.id,
        "full_name": patient.full_name,
        "phone_number": patient.phone_number,
        "medical_notes": patient.medical_notes,
        "emergency_contact_name": patient.emergency_contact_name,
        "emergency_contact_phone": patient.emergency_contact_phone,
        "geofences": [
            {
                "id": g.id,
                "name": g.name,
                "latitude": g.latitude,
                "longitude": g.longitude,
                "radius_meters": g.radius_meters
            }
            for g in geofences
        ],
        "recent_alerts": [
            {
                "id": a.id,
                "severity": a.severity.value,
                "message": a.message,
                "created_at": a.created_at.isoformat()
            }
            for a in recent_alerts
        ]
    }


@app.delete("/api/patients/{patient_id}")
async def delete_patient(patient_id: int, db=Depends(get_db)):
    """Delete a patient (hard delete - permanently removes from database)"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        patient_name = patient.full_name

        # Delete associated geofences first (foreign key constraint)
        db.query(Geofence).filter(Geofence.patient_id == patient_id).delete()

        # Delete associated alerts
        db.query(Alert).filter(Alert.patient_id == patient_id).delete()

        # Delete associated location history
        db.query(LocationHistory).filter(LocationHistory.patient_id == patient_id).delete()

        # Delete associated anomaly scores
        db.query(AnomalyScore).filter(AnomalyScore.patient_id == patient_id).delete()

        # Finally delete the patient
        db.delete(patient)
        db.commit()

        return {
            "message": "Patient deleted successfully",
            "patient_id": patient_id,
            "full_name": patient_name
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/geofences")
async def create_geofence(geofence: GeofenceCreate, db=Depends(get_db)):
    """Create a safe zone (geofence) for a patient"""
    patient = db.query(Patient).filter(Patient.id == geofence.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        nokia_client: NokiaClient = app.state.nokia_client
        nokia_response = await nokia_client.create_geofence(
            phone_number=patient.phone_number,
            area_name=geofence.name,
            latitude=geofence.latitude,
            longitude=geofence.longitude,
            radius_meters=geofence.radius_meters
        )

        db_geofence = Geofence(
            patient_id=geofence.patient_id,
            nokia_geofence_id=nokia_response.get("id"),
            name=geofence.name,
            latitude=geofence.latitude,
            longitude=geofence.longitude,
            radius_meters=geofence.radius_meters
        )
        db.add(db_geofence)
        db.commit()
        db.refresh(db_geofence)

        return {
            "id": db_geofence.id,
            "name": db_geofence.name,
            "latitude": db_geofence.latitude,
            "longitude": db_geofence.longitude,
            "radius_meters": db_geofence.radius_meters,
            "created_at": db_geofence.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/monitor")
async def monitor_patient(request: MonitoringRequest, db=Depends(get_db)):
    """Get current location and run anomaly detection for a patient"""
    patient = db.query(Patient).filter(Patient.id == request.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        nokia_client: NokiaClient = app.state.nokia_client
        ai_detector: AnomalyDetector = app.state.ai_detector

        # Try to get location - will raise exception if device is offline/unregistered
        try:
            location_data = await nokia_client.get_location(patient.phone_number)
        except Exception as e:
            # Device is offline, unregistered, or unreachable
            print(f"⚠️  Device {patient.phone_number} is unreachable: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Device offline or unregistered. Please verify the phone number is registered with Nokia Network as Code."
            )

        device_status = await nokia_client.get_device_status(patient.phone_number)
        sim_swap_info = await nokia_client.check_sim_swap(patient.phone_number)

        location_history_records = db.query(LocationHistory).filter(
            LocationHistory.patient_id == request.patient_id
        ).order_by(LocationHistory.timestamp.desc()).limit(50).all()

        location_history = [
            {
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timestamp": loc.timestamp.isoformat()
            }
            for loc in reversed(location_history_records)
        ]

        geofences = db.query(Geofence).filter(
            Geofence.patient_id == request.patient_id,
            Geofence.active == True
        ).all()

        geofence_data = [
            {
                "id": g.id,
                "name": g.name,
                "latitude": g.latitude,
                "longitude": g.longitude,
                "radius_meters": g.radius_meters
            }
            for g in geofences
        ]

        anomaly_analysis = await ai_detector.analyze_location_pattern(
            current_location=location_data,
            location_history=location_history,
            device_status=device_status,
            sim_swap_info=sim_swap_info,
            geofences=geofence_data
        )

        new_location = LocationHistory(
            patient_id=request.patient_id,
            latitude=location_data["latitude"],
            longitude=location_data["longitude"],
            accuracy=location_data.get("accuracy"),
            timestamp=datetime.now()
        )
        db.add(new_location)

        new_anomaly_score = AnomalyScore(
            patient_id=request.patient_id,
            score=anomaly_analysis["anomaly_score"],
            factors=json.dumps(anomaly_analysis["risk_factors"]),
            latitude=location_data["latitude"],
            longitude=location_data["longitude"]
        )
        db.add(new_anomaly_score)

        if anomaly_analysis["risk_level"] in ["high", "critical"]:
            severity = AlertSeverity.CRITICAL if anomaly_analysis["risk_level"] == "critical" else AlertSeverity.HIGH
            alert = Alert(
                patient_id=request.patient_id,
                severity=severity,
                alert_type="anomaly_detected",
                message=f"Anomaly detected: {', '.join(anomaly_analysis['risk_factors'][:2])}",
                latitude=location_data["latitude"],
                longitude=location_data["longitude"]
            )
            db.add(alert)

            if anomaly_analysis["risk_level"] == "critical":
                qos_session = await nokia_client.create_qos_session(
                    phone_number=patient.phone_number,
                    duration_seconds=600,
                    profile="emergency"
                )
                anomaly_analysis["qos_session"] = qos_session

        db.commit()

        await manager.send_update(request.patient_id, {
            "type": "location_update",
            "location": location_data,
            "device_status": device_status,
            "anomaly_analysis": anomaly_analysis,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "patient_id": request.patient_id,
            "location": location_data,
            "device_status": device_status,
            "sim_swap_info": sim_swap_info,
            "anomaly_analysis": anomaly_analysis,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/patient/{patient_id}")
async def websocket_endpoint(websocket: WebSocket, patient_id: int):
    """WebSocket endpoint for real-time patient monitoring"""
    await manager.connect(websocket, patient_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, patient_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
