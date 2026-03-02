"""
Quick test script to verify CarePulse APIs work
Run this to test the backend: python test_api.py
"""
import asyncio
import httpx

API_BASE = "http://localhost:8000/api"

async def test_health():
    """Test health endpoint"""
    print("\n🔍 Testing health endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200

async def test_create_patient():
    """Test patient creation"""
    print("\n🔍 Testing patient creation...")
    patient_data = {
        "full_name": "Test Patient",
        "phone_number": "+34612345678",
        "emergency_contact_name": "Test Contact",
        "emergency_contact_phone": "+34699887766"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE}/patients", json=patient_data)
        print(f"✅ Create patient: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Patient ID: {data['id']}")
            print(f"   Name: {data['full_name']}")
            return data['id']
        else:
            print(f"   Error: {response.text}")
            return None

async def test_list_patients():
    """Test listing patients"""
    print("\n🔍 Testing list patients...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/patients")
        print(f"✅ List patients: {response.status_code}")
        data = response.json()
        print(f"   Found {len(data)} patients")
        return len(data) > 0

async def test_create_geofence(patient_id):
    """Test geofence creation"""
    print("\n🔍 Testing geofence creation...")
    geofence_data = {
        "patient_id": patient_id,
        "name": "Test Home",
        "latitude": 41.3851,
        "longitude": 2.1734,
        "radius_meters": 500
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE}/geofences", json=geofence_data)
        print(f"✅ Create geofence: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Geofence ID: {data['id']}")
            print(f"   Name: {data['name']}")
            return True
        else:
            print(f"   Error: {response.text}")
            return False

async def test_monitor_patient(patient_id):
    """Test patient monitoring"""
    print("\n🔍 Testing patient monitoring...")
    monitor_data = {"patient_id": patient_id}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{API_BASE}/monitor", json=monitor_data)
        print(f"✅ Monitor patient: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Location: {data['location']['latitude']}, {data['location']['longitude']}")
            print(f"   Risk Level: {data['anomaly_analysis']['risk_level']}")
            print(f"   Anomaly Score: {data['anomaly_analysis']['anomaly_score']}/100")
            print(f"   Device Status: {data['device_status']['network_type']}")
            return True
        else:
            print(f"   Error: {response.text}")
            return False

async def run_all_tests():
    """Run all API tests"""
    print("=" * 60)
    print("CarePulse API Test Suite")
    print("=" * 60)

    try:
        # Test 1: Health check
        if not await test_health():
            print("\n❌ Health check failed! Is the backend running?")
            print("   Start it with: python main.py")
            return

        # Test 2: Create patient
        patient_id = await test_create_patient()
        if not patient_id:
            print("\n❌ Patient creation failed!")
            return

        # Test 3: List patients
        if not await test_list_patients():
            print("\n❌ List patients failed!")
            return

        # Test 4: Create geofence
        if not await test_create_geofence(patient_id):
            print("\n❌ Geofence creation failed!")
            return

        # Test 5: Monitor patient
        if not await test_monitor_patient(patient_id):
            print("\n❌ Patient monitoring failed!")
            return

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n🎉 CarePulse backend is working correctly!")
        print("📱 Open the frontend at http://localhost:8080")
        print("📖 API docs at http://localhost:8000/docs")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("\nMake sure:")
        print("1. Backend is running: python main.py")
        print("2. Dependencies installed: pip install -r requirements.txt")
        print("3. .env file configured")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
