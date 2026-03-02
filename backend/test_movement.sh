#!/bin/bash
# Movement Test Script

echo "=========================================="
echo "🔍 NOKIA LOCATION API - MOVEMENT TEST"
echo "=========================================="
echo ""
echo "📍 BASELINE (before moving):"
echo "   Latitude:  41.3993°N"
echo "   Longitude: 2.1925°E"
echo "   Time: 16:34:27"
echo ""
echo "Fetching NEW location from Nokia API..."
echo ""

RESPONSE=$(curl -s -X POST http://localhost:8000/api/monitor \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 5}')

NEW_LAT=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['location']['latitude'])")
NEW_LNG=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['location']['longitude'])")
NEW_TIME=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['location']['timestamp'])")

echo "📍 NEW LOCATION (after moving):"
echo "   Latitude:  ${NEW_LAT}°N"
echo "   Longitude: ${NEW_LNG}°E"
echo "   Time: ${NEW_TIME}"
echo ""

# Calculate if location changed
python3 << EOF
import math

lat1, lng1 = 41.3993, 2.1925  # Baseline
lat2, lng2 = $NEW_LAT, $NEW_LNG  # New location

# Haversine formula to calculate distance
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

distance = haversine(lat1, lng1, lat2, lng2)

print("========================================")
print(f"📏 DISTANCE MOVED: {distance:.1f} meters")
print("========================================")
print("")

if distance > 100:
    print("✅ RESULT: REAL LOCATION TRACKING!")
    print("   The device location changed significantly.")
    print("   Nokia API is tracking your ACTUAL device!")
elif distance > 20:
    print("⚠️  RESULT: Small movement detected")
    print("   Could be GPS drift or real movement.")
    print("   Try moving further and test again.")
else:
    print("❌ RESULT: Location unchanged")
    print("   Either you didn't move yet OR")
    print("   Nokia API is in simulator mode.")
print("")
EOF
