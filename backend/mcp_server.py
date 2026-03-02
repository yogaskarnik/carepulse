"""
CarePulse MCP Server - Exposes Nokia Network APIs as MCP Tools
Enables Gemini AI to autonomously monitor patients and trigger safety responses
"""
import asyncio
import json
from typing import Any, Dict, List
from dotenv import load_dotenv
import os

# Import CarePulse modules
from nokia_client_rapidapi import NokiaRapidAPIClient
from ai_service import AnomalyDetector
from database import DatabaseManager
from models import Patient, Geofence

load_dotenv()

# Initialize services
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "network-as-code.p-eu.rapidapi.com")
RAPIDAPI_HEADER_HOST = os.getenv("RAPIDAPI_HEADER_HOST", "network-as-code.nokia.rapidapi.com")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./carepulse.db")

nokia_client = NokiaRapidAPIClient(
    use_mock=USE_MOCK,
    rapidapi_key=RAPIDAPI_KEY,
    rapidapi_host=RAPIDAPI_HOST,
    rapidapi_header_host=RAPIDAPI_HEADER_HOST
)

ai_detector = AnomalyDetector(use_gemini=bool(GEMINI_API_KEY), api_key=GEMINI_API_KEY)
db_manager = DatabaseManager(DATABASE_URL)


class CarePulseMCPTools:
    """MCP Tools for CarePulse - Exposes Nokia APIs as callable functions"""

    @staticmethod
    async def get_patient_location(phone_number: str) -> Dict[str, Any]:
        """
        Get real-time location of a patient using Nokia Location Retrieval API.

        Args:
            phone_number: Patient's phone number in E.164 format (e.g., +34640030646)

        Returns:
            Dictionary with latitude, longitude, accuracy, and timestamp
        """
        try:
            location = await nokia_client.get_location(phone_number)
            return {
                "success": True,
                "phone_number": phone_number,
                "location": location,
                "message": f"Patient located at {location['latitude']:.4f}°N, {location['longitude']:.4f}°E"
            }
        except Exception as e:
            return {
                "success": False,
                "phone_number": phone_number,
                "error": str(e),
                "message": "Unable to retrieve location - device may be offline"
            }

    @staticmethod
    async def check_device_status(phone_number: str) -> Dict[str, Any]:
        """
        Check device connectivity status using Nokia Device Status API.

        Args:
            phone_number: Patient's phone number in E.164 format

        Returns:
            Dictionary with connection status, network type, signal strength, battery level
        """
        try:
            status = await nokia_client.get_device_status(phone_number)
            return {
                "success": True,
                "phone_number": phone_number,
                "status": status,
                "message": f"Device {'connected' if status['connected'] else 'disconnected'} - {status['network_type']} network"
            }
        except Exception as e:
            return {
                "success": False,
                "phone_number": phone_number,
                "error": str(e),
                "message": "Unable to check device status"
            }

    @staticmethod
    async def check_sim_swap(phone_number: str) -> Dict[str, Any]:
        """
        Detect suspicious SIM card swaps using Nokia SIM Swap Detection API.
        Critical for fraud prevention and security.

        Args:
            phone_number: Patient's phone number in E.164 format

        Returns:
            Dictionary indicating if SIM was recently swapped
        """
        try:
            swap_info = await nokia_client.check_sim_swap(phone_number)
            return {
                "success": True,
                "phone_number": phone_number,
                "sim_swap_info": swap_info,
                "message": "⚠️ CRITICAL: Recent SIM swap detected!" if swap_info['swapped'] else "✅ No recent SIM swap detected"
            }
        except Exception as e:
            return {
                "success": False,
                "phone_number": phone_number,
                "error": str(e),
                "message": "Unable to check SIM swap status"
            }

    @staticmethod
    async def trigger_emergency_qos(phone_number: str, duration_seconds: int = 600) -> Dict[str, Any]:
        """
        Activate emergency network priority (QoS) for critical situations.
        Ensures high-quality connectivity during emergencies.

        Args:
            phone_number: Patient's phone number in E.164 format
            duration_seconds: How long to maintain priority (default 600s = 10 minutes)

        Returns:
            Dictionary with QoS session details
        """
        try:
            qos_session = await nokia_client.create_qos_session(
                phone_number=phone_number,
                duration_seconds=duration_seconds,
                profile="emergency"
            )
            return {
                "success": True,
                "phone_number": phone_number,
                "qos_session": qos_session,
                "message": f"🚀 Emergency network priority activated for {duration_seconds} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "phone_number": phone_number,
                "error": str(e),
                "message": "Unable to activate emergency QoS"
            }

    @staticmethod
    async def create_safe_zone(phone_number: str, name: str, latitude: float, longitude: float, radius_meters: int = 500) -> Dict[str, Any]:
        """
        Create a geofence (safe zone) around a location using Nokia Geofencing API.
        Alerts when patient enters or exits the defined area.

        Args:
            phone_number: Patient's phone number in E.164 format
            name: Name of the safe zone (e.g., "Home", "Hospital")
            latitude: Center latitude of the zone
            longitude: Center longitude of the zone
            radius_meters: Radius of the zone in meters (default 500m)

        Returns:
            Dictionary with geofence details
        """
        try:
            geofence = await nokia_client.create_geofence(
                phone_number=phone_number,
                area_name=name,
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters
            )
            return {
                "success": True,
                "phone_number": phone_number,
                "geofence": geofence,
                "message": f"🗺️ Safe zone '{name}' created at {latitude:.4f}°N, {longitude:.4f}°E (radius: {radius_meters}m)"
            }
        except Exception as e:
            return {
                "success": False,
                "phone_number": phone_number,
                "error": str(e),
                "message": "Unable to create safe zone"
            }

    @staticmethod
    async def analyze_patient_safety(phone_number: str) -> Dict[str, Any]:
        """
        Comprehensive safety analysis combining all Nokia APIs + AI.
        Returns risk score, factors, and recommendations.

        Args:
            phone_number: Patient's phone number in E.164 format

        Returns:
            Dictionary with anomaly score, risk level, factors, and AI insights
        """
        try:
            # Get all data
            location = await nokia_client.get_location(phone_number)
            device_status = await nokia_client.get_device_status(phone_number)
            sim_swap = await nokia_client.check_sim_swap(phone_number)

            # Run AI analysis
            analysis = await ai_detector.analyze_location_pattern(
                current_location=location,
                location_history=[],  # Simplified for MCP demo
                device_status=device_status,
                sim_swap_info=sim_swap,
                geofences=[]
            )

            return {
                "success": True,
                "phone_number": phone_number,
                "location": location,
                "device_status": device_status,
                "sim_swap_info": sim_swap,
                "analysis": analysis,
                "message": f"Risk Level: {analysis['risk_level'].upper()} (Score: {analysis['anomaly_score']}/100)"
            }
        except Exception as e:
            return {
                "success": False,
                "phone_number": phone_number,
                "error": str(e),
                "message": "Unable to perform safety analysis"
            }


# Define tools for Gemini function calling
CAREPULSE_TOOLS = [
    {
        "name": "get_patient_location",
        "description": "Get real-time GPS location of a patient using Nokia Location Retrieval API. Returns latitude, longitude, accuracy, and timestamp.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Patient's phone number in E.164 format (e.g., +34640030646)"
                }
            },
            "required": ["phone_number"]
        }
    },
    {
        "name": "check_device_status",
        "description": "Check device connectivity and network status using Nokia Device Status API. Returns connection status, network type (5G/4G), signal strength, and battery level.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Patient's phone number in E.164 format"
                }
            },
            "required": ["phone_number"]
        }
    },
    {
        "name": "check_sim_swap",
        "description": "Detect suspicious SIM card swaps using Nokia SIM Swap Detection API. Critical for fraud prevention and security alerts.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Patient's phone number in E.164 format"
                }
            },
            "required": ["phone_number"]
        }
    },
    {
        "name": "trigger_emergency_qos",
        "description": "Activate emergency network priority (QoS on Demand) for critical situations. Ensures high-quality connectivity during emergencies by boosting bandwidth and reducing latency.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Patient's phone number in E.164 format"
                },
                "duration_seconds": {
                    "type": "integer",
                    "description": "Duration to maintain priority in seconds (default 600)",
                    "default": 600
                }
            },
            "required": ["phone_number"]
        }
    },
    {
        "name": "create_safe_zone",
        "description": "Create a geofence (virtual boundary) around a location using Nokia Geofencing API. Triggers alerts when patient enters or exits the defined area.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Patient's phone number in E.164 format"
                },
                "name": {
                    "type": "string",
                    "description": "Name of the safe zone (e.g., 'Home', 'Hospital')"
                },
                "latitude": {
                    "type": "number",
                    "description": "Center latitude of the zone"
                },
                "longitude": {
                    "type": "number",
                    "description": "Center longitude of the zone"
                },
                "radius_meters": {
                    "type": "integer",
                    "description": "Radius of the zone in meters (default 500)",
                    "default": 500
                }
            },
            "required": ["phone_number", "name", "latitude", "longitude"]
        }
    },
    {
        "name": "analyze_patient_safety",
        "description": "Comprehensive safety analysis combining all Nokia APIs + AI. Returns risk score (0-100), risk level, detected factors, and actionable recommendations.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Patient's phone number in E.164 format"
                }
            },
            "required": ["phone_number"]
        }
    }
]


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a CarePulse MCP tool"""
    tools = CarePulseMCPTools()

    tool_map = {
        "get_patient_location": tools.get_patient_location,
        "check_device_status": tools.check_device_status,
        "check_sim_swap": tools.check_sim_swap,
        "trigger_emergency_qos": tools.trigger_emergency_qos,
        "create_safe_zone": tools.create_safe_zone,
        "analyze_patient_safety": tools.analyze_patient_safety
    }

    if tool_name not in tool_map:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    try:
        result = await tool_map[tool_name](**arguments)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# Export tools and execution function
__all__ = ['CAREPULSE_TOOLS', 'execute_tool', 'CarePulseMCPTools']


if __name__ == "__main__":
    print("🤖 CarePulse MCP Server")
    print("=" * 50)
    print(f"Available Tools: {len(CAREPULSE_TOOLS)}")
    for tool in CAREPULSE_TOOLS:
        print(f"  - {tool['name']}: {tool['description'][:60]}...")
    print("\nTools ready for Gemini AI Agent integration!")
