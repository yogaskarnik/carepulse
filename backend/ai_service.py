"""
AI-Powered Anomaly Detection for CarePulse
Uses Google Gemini for pattern analysis and risk assessment
"""
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
import httpx

# No SDK imports needed - using REST API directly via httpx
# This avoids all SSL certificate issues with gRPC in WSL/Linux


class AnomalyDetector:
    """AI-powered anomaly detection using Gemini and simple heuristics"""

    def __init__(self, use_gemini: bool = False, api_key: Optional[str] = None):
        self.use_gemini = use_gemini
        self.api_key = None
        self.http_client = None

        if self.use_gemini:
            if not api_key:
                api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                # Use REST API directly with httpx (bypasses SDK SSL issues)
                import httpx
                self.api_key = api_key
                self.http_client = httpx.AsyncClient(verify=False, timeout=30.0)
                self.model_name = 'gemini-1.5-flash'
                print("✅ Gemini REST API configured (SSL verification disabled for WSL)")
            else:
                self.use_gemini = False

    async def analyze_location_pattern(
        self,
        current_location: Dict[str, float],
        location_history: List[Dict],
        device_status: Dict,
        sim_swap_info: Dict,
        geofences: List[Dict],
        time_of_day: Optional[datetime] = None
    ) -> Dict:
        """
        Analyze current location against historical patterns
        Returns anomaly score (0-100) and risk factors
        """
        if time_of_day is None:
            time_of_day = datetime.now()

        anomaly_score = 0.0
        risk_factors = []

        if not location_history or len(location_history) < 3:
            return {
                "anomaly_score": 0,
                "risk_level": "low",
                "risk_factors": ["Insufficient historical data for pattern analysis"],
                "recommendations": ["Continue monitoring to establish baseline patterns"]
            }

        current_lat = current_location["latitude"]
        current_lng = current_location["longitude"]

        inside_any_geofence = False
        for geofence in geofences:
            distance = self._calculate_distance(
                current_lat, current_lng,
                geofence["latitude"], geofence["longitude"]
            )
            if distance <= geofence["radius_meters"]:
                inside_any_geofence = True
                break

        if geofences and not inside_any_geofence:
            anomaly_score += 40
            risk_factors.append("🚨 Outside all safe zones (geofences)")

        common_locations = self._find_common_locations(location_history)
        is_near_common_location = any(
            self._calculate_distance(current_lat, current_lng, loc["lat"], loc["lng"]) < 500
            for loc in common_locations
        )

        if not is_near_common_location and len(common_locations) > 0:
            anomaly_score += 25
            risk_factors.append("⚠️ Unusual location (not near common areas)")

        hour = time_of_day.hour
        if hour < 6 or hour > 22:
            anomaly_score += 15
            risk_factors.append("🌙 Unusual time of day (late night/early morning)")

        if sim_swap_info.get("swapped", False):
            days_since = sim_swap_info.get("days_since_swap", 999)
            if days_since < 7:
                anomaly_score += 50
                risk_factors.append("🚨 CRITICAL: Recent SIM swap detected")

        if not device_status.get("connected", True):
            anomaly_score += 30
            risk_factors.append("📵 Device connectivity issue detected")

        battery_level = device_status.get("battery_level", 100)
        if battery_level < 20:
            anomaly_score += 10
            risk_factors.append(f"🔋 Low battery: {battery_level}%")

        signal_strength = device_status.get("signal_strength", 100)
        if signal_strength < 40:
            anomaly_score += 10
            risk_factors.append("📶 Weak signal strength")

        if len(location_history) >= 5:
            movement_speed = self._calculate_movement_speed(location_history[-5:])
            if movement_speed > 80:
                anomaly_score += 20
                risk_factors.append(f"🚗 High movement speed: {movement_speed:.1f} km/h")
            elif movement_speed < 0.1:
                time_stationary = self._calculate_stationary_time(location_history)
                if time_stationary > 4:
                    anomaly_score += 15
                    risk_factors.append(f"⏱️ No movement for {time_stationary:.1f} hours")

        anomaly_score = min(anomaly_score, 100)

        if anomaly_score >= 70:
            risk_level = "critical"
        elif anomaly_score >= 50:
            risk_level = "high"
        elif anomaly_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        recommendations = self._generate_recommendations(anomaly_score, risk_factors)

        result = {
            "anomaly_score": round(anomaly_score, 1),
            "risk_level": risk_level,
            "risk_factors": risk_factors if risk_factors else ["No significant risk factors detected"],
            "recommendations": recommendations
        }

        if self.use_gemini and anomaly_score >= 30:
            try:
                gemini_analysis = await self._get_gemini_insights(result, location_history, device_status)
                result["ai_insights"] = gemini_analysis
            except Exception as e:
                result["ai_insights"] = f"AI analysis unavailable: {str(e)}"

        return result

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters using Haversine formula"""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371000
        phi1, phi2 = radians(lat1), radians(lat2)
        delta_phi = radians(lat2 - lat1)
        delta_lambda = radians(lng2 - lng1)

        a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def _find_common_locations(self, location_history: List[Dict], radius: int = 200) -> List[Dict]:
        """Find frequently visited locations (clustering)"""
        if not location_history:
            return []

        clusters = []
        for loc in location_history:
            lat, lng = loc["latitude"], loc["longitude"]
            found_cluster = False

            for cluster in clusters:
                distance = self._calculate_distance(lat, lng, cluster["lat"], cluster["lng"])
                if distance < radius:
                    cluster["count"] += 1
                    found_cluster = True
                    break

            if not found_cluster:
                clusters.append({"lat": lat, "lng": lng, "count": 1})

        return sorted(clusters, key=lambda x: x["count"], reverse=True)[:3]

    def _calculate_movement_speed(self, recent_locations: List[Dict]) -> float:
        """Calculate average speed in km/h from recent locations"""
        if len(recent_locations) < 2:
            return 0.0

        total_distance = 0.0
        total_time = 0.0

        for i in range(1, len(recent_locations)):
            prev = recent_locations[i - 1]
            curr = recent_locations[i]

            distance = self._calculate_distance(
                prev["latitude"], prev["longitude"],
                curr["latitude"], curr["longitude"]
            )
            total_distance += distance

            time_diff = (
                datetime.fromisoformat(curr.get("timestamp", datetime.now().isoformat())) -
                datetime.fromisoformat(prev.get("timestamp", datetime.now().isoformat()))
            ).total_seconds()
            total_time += time_diff

        if total_time == 0:
            return 0.0

        speed_ms = total_distance / total_time
        speed_kmh = speed_ms * 3.6
        return speed_kmh

    def _calculate_stationary_time(self, location_history: List[Dict], threshold: int = 50) -> float:
        """Calculate how long the person has been stationary (in hours)"""
        if len(location_history) < 2:
            return 0.0

        latest = location_history[-1]
        latest_time = datetime.fromisoformat(latest.get("timestamp", datetime.now().isoformat()))

        for i in range(len(location_history) - 2, -1, -1):
            prev = location_history[i]
            distance = self._calculate_distance(
                latest["latitude"], latest["longitude"],
                prev["latitude"], prev["longitude"]
            )

            if distance > threshold:
                prev_time = datetime.fromisoformat(prev.get("timestamp", datetime.now().isoformat()))
                hours = (latest_time - prev_time).total_seconds() / 3600
                return hours

        first_time = datetime.fromisoformat(location_history[0].get("timestamp", datetime.now().isoformat()))
        return (latest_time - first_time).total_seconds() / 3600

    def _generate_recommendations(self, anomaly_score: float, risk_factors: List[str]) -> List[str]:
        """Generate actionable recommendations based on risk factors"""
        recommendations = []

        if anomaly_score >= 70:
            recommendations.append("🚨 IMMEDIATE ACTION: Contact patient and verify safety")
            recommendations.append("📞 Consider initiating emergency call with QoS priority")
            recommendations.append("📍 Share location with emergency contacts")

        elif anomaly_score >= 50:
            recommendations.append("⚠️ Check in with patient to verify they are safe")
            recommendations.append("👀 Monitor closely for the next hour")

        elif anomaly_score >= 30:
            recommendations.append("📱 Consider sending a check-in message")
            recommendations.append("📊 Review recent activity patterns")

        else:
            recommendations.append("✅ Continue routine monitoring")

        for factor in risk_factors:
            if "SIM swap" in factor:
                recommendations.append("🔒 Verify patient identity before any sensitive actions")
            elif "battery" in factor.lower():
                recommendations.append("🔌 Remind patient to charge device")
            elif "geofence" in factor.lower():
                recommendations.append("🗺️ Verify if patient planned to leave safe zones")

        return recommendations

    async def _get_gemini_insights(self, analysis_result: Dict, location_history: List[Dict],
                                   device_status: Dict) -> str:
        """Get additional insights from Gemini AI using REST API"""
        prompt = f"""
You are an AI assistant helping caregivers monitor elderly patients for safety.

Current Analysis:
- Anomaly Score: {analysis_result['anomaly_score']}/100
- Risk Level: {analysis_result['risk_level']}
- Risk Factors: {', '.join(analysis_result['risk_factors'])}

Recent Location History: {len(location_history)} data points
Device Status: Connected={device_status.get('connected')}, Network={device_status.get('network_type')}, Battery={device_status.get('battery_level')}%

Provide a brief (2-3 sentences) assessment of the situation and any additional concerns or reassurances for the caregiver.
Focus on practical, actionable insights.
"""

        try:
            print("🤖 Calling Gemini REST API for AI insights...")

            # Call Gemini REST API directly
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

            request_body = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }

            response = await self.http_client.post(url, json=request_body)
            response.raise_for_status()
            data = response.json()

            # Parse response
            insight = data['candidates'][0]['content']['parts'][0]['text'].strip()

            print(f"✅ Gemini AI Response: {insight[:100]}...")
            return insight
        except Exception as e:
            error_msg = f"Unable to generate AI insights: {str(e)}"
            print(f"❌ Gemini API Error: {error_msg}")
            return error_msg

    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
