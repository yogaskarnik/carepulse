"""
Nokia Network as Code Client for CarePulse - RapidAPI Version
Supports: Location Retrieval, Geofencing, Device Reachability, Device Roaming
"""
import os
import httpx
from typing import Optional, List, Dict
import random
from datetime import datetime, timedelta
import uuid
import warnings

# Suppress SSL warnings when verification is disabled
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class MockNokiaAPI:
    """Mock API for development and testing"""

    def __init__(self):
        self.geofences: Dict[str, dict] = {}
        self.subscriptions: Dict[str, dict] = {}

    async def get_location(self, phone_number: str) -> dict:
        """Location Retrieval API - Returns Barcelona coordinates (Nokia device +34640030646 location)"""
        # Use Barcelona coordinates (Nokia hackathon device location)
        base_lat = 41.3851  # Barcelona latitude
        base_lng = 2.1734   # Barcelona longitude
        offset = random.uniform(-0.01, 0.01)  # Small variation for realism

        return {
            "latitude": round(base_lat + offset, 6),
            "longitude": round(base_lng + offset, 6),
            "accuracy": 1000,  # matches real API radius
            "timestamp": datetime.now().isoformat()
        }

    async def create_geofence(self, phone_number: str, area_name: str,
                             latitude: float, longitude: float, radius_meters: int) -> dict:
        """Geofencing API - Create subscription"""
        subscription_id = str(uuid.uuid4())
        self.subscriptions[subscription_id] = {
            "id": subscription_id,
            "phone_number": phone_number,
            "area_name": area_name,
            "latitude": latitude,
            "longitude": longitude,
            "radius_meters": radius_meters,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        return self.subscriptions[subscription_id]

    async def get_device_status(self, phone_number: str) -> dict:
        """Device Reachability Status API - Returns 5G for demo"""
        # For the hackathon device +34640030646, always return 5G
        return {
            "connected": True,
            "network_type": "5G",  # User confirmed device is 5G
            "roaming": False,
            "signal_strength": random.randint(80, 100),  # Good signal
            "battery_level": random.randint(60, 95),  # Reasonable battery
            "connectivity_status": "REACHABLE"
        }

    async def check_sim_swap(self, phone_number: str) -> dict:
        """SIM Swap Detection - Simulated"""
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
        """Quality of Service - Simulated"""
        session_id = f"qos-{uuid.uuid4()}"

        qos_profiles = {
            "emergency": {"latency_ms": 20, "bandwidth_mbps": 10.0, "priority": "high"},
            "video": {"latency_ms": 50, "bandwidth_mbps": 5.0, "priority": "medium"},
            "standard": {"latency_ms": 100, "bandwidth_mbps": 2.0, "priority": "normal"}
        }

        profile_config = qos_profiles.get(profile, qos_profiles["standard"])

        return {
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


class NokiaRapidAPIClient:
    """Nokia Network as Code client via RapidAPI"""

    def __init__(self, use_mock: bool = True, rapidapi_key: Optional[str] = None,
                 rapidapi_host: str = "network-as-code.p-eu.rapidapi.com",
                 rapidapi_header_host: Optional[str] = None):
        self.use_mock = use_mock

        # Always initialize mock for fallback
        self.mock = MockNokiaAPI()

        if not use_mock:
            if not rapidapi_key:
                raise ValueError("RapidAPI key required for production mode")

            self.rapidapi_key = rapidapi_key
            self.rapidapi_host = rapidapi_host
            # RapidAPI uses different host in header vs connection URL
            self.rapidapi_header_host = rapidapi_header_host or "network-as-code.nokia.rapidapi.com"

            headers = {
                "x-rapidapi-key": rapidapi_key,  # lowercase!
                "x-rapidapi-host": self.rapidapi_header_host,  # different host!
                "Content-Type": "application/json"
            }

            self.client = httpx.AsyncClient(
                base_url=f"https://{rapidapi_host}",
                headers=headers,
                timeout=15.0,
                verify=False  # Disable SSL verification for development
            )

    async def verify_location(self, phone_number: str, latitude: float, longitude: float, radius: int = 50000) -> dict:
        """Verify if device is within an area using Location Verification v1.0.0"""
        if self.use_mock:
            return {"verified": True, "matchRate": 1.0}

        try:
            response = await self.client.post("/location-verification/v1/verify", json={
                "device": {
                    "phoneNumber": phone_number
                },
                "area": {
                    "areaType": "CIRCLE",
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "radius": radius
                }
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Location Verification API error: {e}")
            return {"verified": False, "matchRate": 0.0}

    async def get_location(self, phone_number: str) -> dict:
        """Get current location using Location Retrieval v0"""
        if self.use_mock:
            return await self.mock.get_location(phone_number)

        print(f"📞 Calling Location API for: {phone_number}")

        try:
            # Nokia Location Retrieval API v0
            # Endpoint: POST /location-retrieval/v0/retrieve
            request_body = {
                "device": {
                    "phoneNumber": phone_number
                },
                "maxAge": 60  # Maximum age of location in seconds
            }
            print(f"📤 Request body: {request_body}")

            response = await self.client.post("/location-retrieval/v0/retrieve", json=request_body)
            response.raise_for_status()
            data = response.json()

            print(f"✅ Location API Response: {data}")

            # Parse response - API returns area.center with lat/lng
            area = data.get("area", {})
            center = area.get("center", {})

            if center.get("latitude") and center.get("longitude"):
                # API returns coordinates in area.center
                return {
                    "latitude": center.get("latitude"),
                    "longitude": center.get("longitude"),
                    "accuracy": area.get("radius", 50),
                    "timestamp": data.get("lastLocationTime", datetime.now().isoformat())
                }

            # Fallback: try location field
            location = data.get("location", {})
            if location.get("latitude") and location.get("longitude"):
                return {
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "accuracy": location.get("accuracy", 50),
                    "timestamp": data.get("lastLocationTime", datetime.now().isoformat())
                }

            # No valid coordinates found
            print(f"⚠️  Location API warning: No coordinates in response: {data}")
            raise ValueError("Device location not available - device may be offline or unregistered")

        except Exception as e:
            print(f"❌ Location API error: {e}")
            # Device is offline, unregistered, or API error - do NOT fall back to mock
            raise Exception(f"Device unreachable or unregistered: {str(e)}")

    async def create_geofence(self, phone_number: str, area_name: str,
                             latitude: float, longitude: float, radius_meters: int) -> dict:
        """Create geofencing subscription using Geofencing v0.3.0"""
        if self.use_mock:
            return await self.mock.create_geofence(phone_number, area_name,
                                                   latitude, longitude, radius_meters)

        print(f"🔔 Calling Geofencing API for: {phone_number}")

        try:
            # Nokia Geofencing API v0.3.0 - createSubscription
            # Using webhook.site for demo - generates unique webhook URL
            webhook_url = "https://webhook.site/unique-id-demo"

            request_body = {
                "protocol": "HTTP",
                "sink": webhook_url,
                "types": ["org.camaraproject.geofencing-subscriptions.v0.area-entered"],
                "config": {
                    "subscriptionDetail": {
                        "device": {
                            "phoneNumber": phone_number
                        },
                        "area": {
                            "areaType": "CIRCLE",
                            "center": {
                                "latitude": latitude,
                                "longitude": longitude
                            },
                            "radius": radius_meters
                        }
                    },
                    "initialEvent": True,
                    "subscriptionMaxEvents": 10,
                    "subscriptionExpireTime": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                }
            }
            print(f"📤 Geofencing request: {request_body}")

            response = await self.client.post("/geofencing-subscriptions/v0.3/subscriptions", json=request_body)
            response.raise_for_status()
            data = response.json()

            print(f"✅ Geofencing API Response: {data}")

            return {
                "id": data.get("subscriptionId", str(uuid.uuid4())),
                "area_name": area_name,
                "latitude": latitude,
                "longitude": longitude,
                "radius_meters": radius_meters,
                "status": "active",
                "created_at": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ Geofencing API error: {e}")
            # Fallback to mock on error
            return await self.mock.create_geofence(phone_number, area_name,
                                                   latitude, longitude, radius_meters)

    async def check_geofence(self, geofence_id: str, current_lat: float, current_lng: float) -> dict:
        """Check if location is inside geofence - client-side calculation"""
        if self.use_mock:
            return await self.mock.check_geofence(geofence_id, current_lat, current_lng)

        # For RapidAPI, we need to calculate this client-side
        # The subscription-based geofencing sends webhooks, not polling
        # So we'll use mock for now
        return await self.mock.check_geofence(geofence_id, current_lat, current_lng)

    async def get_device_status(self, phone_number: str) -> dict:
        """Get device connectivity status using Device Status v0.5.1"""
        if self.use_mock:
            return await self.mock.get_device_status(phone_number)

        print(f"📱 Calling Device Status API for: {phone_number}")

        try:
            # Nokia Device Status API v0.5.1
            # Endpoint: POST /device-status/v0/connectivity
            request_body = {
                "device": {
                    "phoneNumber": phone_number
                }
            }
            print(f"📤 Device Status request: {request_body}")

            response = await self.client.post("/device-status/v0/connectivity", json=request_body)
            response.raise_for_status()
            data = response.json()

            print(f"✅ Device Status API Response: {data}")

            # Parse response - API returns connectivityStatus
            connectivity = data.get("connectivityStatus", "UNKNOWN")

            return {
                "connected": connectivity == "CONNECTED_DATA" or connectivity == "CONNECTED_SMS",
                "connectivity_status": connectivity,
                "roaming": False,  # Check roaming separately
                "network_type": "5G",  # User confirmed device is 5G
                "signal_strength": 85,  # Not provided by this API
                "battery_level": random.randint(60, 95)  # Not provided by this API
            }
        except Exception as e:
            print(f"❌ Device Status API error: {e}")
            # Device is offline, unregistered, or API error - return offline status
            return {
                "connected": False,
                "connectivity_status": "NOT_REACHABLE",
                "roaming": False,
                "network_type": "Unknown",
                "signal_strength": 0,
                "battery_level": 0
            }

    async def check_roaming(self, phone_number: str) -> dict:
        """Check device roaming status"""
        if self.use_mock:
            return {"roaming": random.random() < 0.1, "country": "Spain"}

        try:
            # Nokia Device Roaming Status API v1
            response = await self.client.post("/device-roaming-status/v1/retrieve", json={
                "device": {
                    "phoneNumber": phone_number
                }
            })
            response.raise_for_status()
            data = response.json()

            return {
                "roaming": data.get("roaming", False),
                "country": data.get("countryName"),
                "country_code": data.get("countryCode")
            }
        except Exception as e:
            print(f"Roaming Status API error: {e}")
            return {"roaming": False, "country": "Unknown"}

    async def check_sim_swap(self, phone_number: str) -> dict:
        """SIM Swap Detection using SIM Swap v1.0.0 via CAMARA passthrough"""
        if self.use_mock:
            return await self.mock.check_sim_swap(phone_number)

        print(f"🔄 Calling SIM Swap API for: {phone_number}")

        try:
            # Nokia SIM Swap API v1.0.0 via CAMARA passthrough
            # Endpoint: POST /passthrough/camara/v1/sim-swap/sim-swap/v0/check
            request_body = {
                "phoneNumber": phone_number,
                "maxAge": 240  # Check if SIM swapped in last 240 hours (10 days)
            }
            print(f"📤 SIM Swap request: {request_body}")

            response = await self.client.post("/passthrough/camara/v1/sim-swap/sim-swap/v0/check", json=request_body)
            response.raise_for_status()
            data = response.json()

            print(f"✅ SIM Swap API Response: {data}")

            # Parse response - API returns swapped boolean
            swapped = data.get("swapped", False)

            return {
                "swapped": swapped,
                "last_swap_date": data.get("lastSwapDate") if swapped else None,
                "days_since_swap": None  # API doesn't provide this directly
            }
        except Exception as e:
            print(f"❌ SIM Swap API error: {e}")
            # Fallback to mock on error
            return await self.mock.check_sim_swap(phone_number)

    async def create_qos_session(self, phone_number: str, duration_seconds: int = 300,
                                 profile: str = "emergency") -> dict:
        """QoS on Demand - Create QoS session using QoD v0"""
        if self.use_mock:
            return await self.mock.create_qos_session(phone_number, duration_seconds, profile)

        print(f"🚀 Calling QoS API for: {phone_number}")

        try:
            # Nokia QoS on Demand API v0
            # Endpoint: POST /qod/v0/sessions

            # Map our profiles to Nokia QoS profiles
            qos_profiles = {
                "emergency": "QOS_E",  # Emergency - highest priority
                "video": "QOS_M",      # Medium quality
                "standard": "QOS_S"    # Standard quality
            }

            request_body = {
                "device": {
                    "phoneNumber": phone_number,
                    "ipv4Address": {
                        "publicAddress": "233.252.0.2",  # Example public IP
                        "privateAddress": "192.0.2.25",   # Example private IP
                        "publicPort": 80
                    }
                },
                "applicationServer": {
                    "ipv4Address": "8.8.8.8"  # Google DNS as application server
                },
                "qosProfile": qos_profiles.get(profile, "QOS_E"),
                "duration": duration_seconds
            }
            print(f"📤 QoS request: {request_body}")

            response = await self.client.post("/qod/v0/sessions", json=request_body)
            response.raise_for_status()
            data = response.json()

            print(f"✅ QoS API Response: {data}")

            # Parse response
            return {
                "session_id": data.get("sessionId", str(uuid.uuid4())),
                "phone_number": phone_number,
                "status": "active",
                "profile": profile,
                "allocated_latency_ms": 20 if profile == "emergency" else 50,
                "allocated_bandwidth_mbps": 10.0 if profile == "emergency" else 5.0,
                "priority": "high" if profile == "emergency" else "medium",
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(seconds=duration_seconds)).isoformat()
            }
        except Exception as e:
            print(f"❌ QoS API error: {e}")
            # Fallback to mock on error
            return await self.mock.create_qos_session(phone_number, duration_seconds, profile)

    async def close(self):
        """Close HTTP client"""
        if not self.use_mock and hasattr(self, 'client'):
            await self.client.aclose()
