"""
Nokia Network as Code Client for CarePulse
Supports: Location Retrieval, Geofencing, Device Status, SIM Swap, QoD
"""
import os
import httpx
from typing import Optional, List, Dict
import random
from datetime import datetime, timedelta
import uuid

class MockNokiaAPI:
    """Mock API for development and testing"""

    def __init__(self):
        self.geofences: Dict[str, dict] = {}
        self.qos_sessions: Dict[str, dict] = {}

    async def get_location(self, phone_number: str) -> dict:
        """Location Retrieval API"""
        base_lat = 41.3851
        base_lng = 2.1734
        offset = random.uniform(-0.05, 0.05)

        return {
            "latitude": round(base_lat + offset, 6),
            "longitude": round(base_lng + offset, 6),
            "accuracy": random.randint(10, 50),
            "timestamp": datetime.now().isoformat()
        }

    async def create_geofence(self, phone_number: str, area_name: str,
                             latitude: float, longitude: float, radius_meters: int) -> dict:
        """Geofencing API - Create geofence"""
        geofence_id = str(uuid.uuid4())
        self.geofences[geofence_id] = {
            "id": geofence_id,
            "phone_number": phone_number,
            "area_name": area_name,
            "latitude": latitude,
            "longitude": longitude,
            "radius_meters": radius_meters,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        return self.geofences[geofence_id]

    async def check_geofence(self, geofence_id: str, current_lat: float, current_lng: float) -> dict:
        """Check if location is inside geofence"""
        if geofence_id not in self.geofences:
            raise ValueError(f"Geofence {geofence_id} not found")

        geofence = self.geofences[geofence_id]
        distance = self._calculate_distance(
            current_lat, current_lng,
            geofence["latitude"], geofence["longitude"]
        )

        inside = distance <= geofence["radius_meters"]
        return {
            "inside_area": inside,
            "distance_meters": round(distance, 1),
            "geofence_name": geofence["area_name"]
        }

    async def get_device_status(self, phone_number: str) -> dict:
        """Device Status API"""
        network_types = ["5G", "5G", "4G", "4G", "3G"]
        return {
            "connected": True,
            "network_type": random.choice(network_types),
            "roaming": random.random() < 0.1,
            "signal_strength": random.randint(60, 100),
            "battery_level": random.randint(20, 100),
            "connectivity_status": "online"
        }

    async def check_sim_swap(self, phone_number: str) -> dict:
        """SIM Swap Detection API"""
        swapped_recently = random.random() < 0.05
        days_ago = random.randint(1, 3) if swapped_recently else random.randint(180, 730)
        last_swap_date = datetime.now() - timedelta(days=days_ago)

        return {
            "swapped": swapped_recently,
            "last_swap_date": last_swap_date.isoformat() if swapped_recently else None,
            "days_since_swap": days_ago
        }

    async def create_qos_session(self, phone_number: str, duration_seconds: int = 300,
                                 profile: str = "emergency") -> dict:
        """Quality of Service on Demand API"""
        session_id = f"qos-{uuid.uuid4()}"

        qos_profiles = {
            "emergency": {"latency_ms": 20, "bandwidth_mbps": 10.0, "priority": "high"},
            "video": {"latency_ms": 50, "bandwidth_mbps": 5.0, "priority": "medium"},
            "standard": {"latency_ms": 100, "bandwidth_mbps": 2.0, "priority": "normal"}
        }

        profile_config = qos_profiles.get(profile, qos_profiles["standard"])

        self.qos_sessions[session_id] = {
            "session_id": session_id,
            "phone_number": phone_number,
            "status": "active",
            "profile": profile,
            "allocated_latency_ms": profile_config["latency_ms"],
            "allocated_bandwidth_mbps": profile_config["bandwidth_mbps"],
            "priority": profile_config["priority"],
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=duration_seconds)).isoformat()
        }
        return self.qos_sessions[session_id]

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters using Haversine formula (simplified)"""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371000
        phi1, phi2 = radians(lat1), radians(lat2)
        delta_phi = radians(lat2 - lat1)
        delta_lambda = radians(lng2 - lng1)

        a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c


class NokiaClient:
    """Nokia Network as Code client with mock and production modes"""

    def __init__(self, use_mock: bool = True, api_url: Optional[str] = None,
                 api_token: Optional[str] = None, organization_id: Optional[str] = None):
        self.use_mock = use_mock

        if use_mock:
            self.mock = MockNokiaAPI()
        else:
            if not api_token:
                raise ValueError("API token required for production mode")

            self.api_url = api_url or "https://networkascode.nokia.io/api"
            self.api_token = api_token
            self.organization_id = organization_id

            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }
            if organization_id:
                headers["X-Organization-ID"] = organization_id

            self.client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=15.0
            )

    async def get_location(self, phone_number: str) -> dict:
        """Get current location of device"""
        if self.use_mock:
            return await self.mock.get_location(phone_number)
        else:
            response = await self.client.post("/location/retrieve", json={
                "device": {"phoneNumber": phone_number}
            })
            response.raise_for_status()
            return response.json()

    async def create_geofence(self, phone_number: str, area_name: str,
                             latitude: float, longitude: float, radius_meters: int) -> dict:
        """Create a geofence area"""
        if self.use_mock:
            return await self.mock.create_geofence(phone_number, area_name,
                                                   latitude, longitude, radius_meters)
        else:
            response = await self.client.post("/geofencing/create", json={
                "device": {"phoneNumber": phone_number},
                "area": {
                    "name": area_name,
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius_meters
                }
            })
            response.raise_for_status()
            return response.json()

    async def check_geofence(self, geofence_id: str, current_lat: float, current_lng: float) -> dict:
        """Check if current location is inside geofence"""
        if self.use_mock:
            return await self.mock.check_geofence(geofence_id, current_lat, current_lng)
        else:
            response = await self.client.post(f"/geofencing/{geofence_id}/check", json={
                "location": {"latitude": current_lat, "longitude": current_lng}
            })
            response.raise_for_status()
            return response.json()

    async def get_device_status(self, phone_number: str) -> dict:
        """Get device connectivity status"""
        if self.use_mock:
            return await self.mock.get_device_status(phone_number)
        else:
            response = await self.client.post("/device/status", json={
                "device": {"phoneNumber": phone_number}
            })
            response.raise_for_status()
            return response.json()

    async def check_sim_swap(self, phone_number: str) -> dict:
        """Check if SIM was recently swapped"""
        if self.use_mock:
            return await self.mock.check_sim_swap(phone_number)
        else:
            response = await self.client.post("/sim-swap/check", json={
                "phoneNumber": phone_number
            })
            response.raise_for_status()
            return response.json()

    async def create_qos_session(self, phone_number: str, duration_seconds: int = 300,
                                 profile: str = "emergency") -> dict:
        """Create QoS session for priority network access"""
        if self.use_mock:
            return await self.mock.create_qos_session(phone_number, duration_seconds, profile)
        else:
            response = await self.client.post("/qos/create", json={
                "device": {"phoneNumber": phone_number},
                "duration": duration_seconds,
                "profile": profile
            })
            response.raise_for_status()
            return response.json()

    async def close(self):
        """Close HTTP client"""
        if not self.use_mock and hasattr(self, 'client'):
            await self.client.aclose()
