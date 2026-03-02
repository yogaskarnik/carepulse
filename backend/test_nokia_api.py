"""
Test script to verify Nokia Network as Code API connection
Run this after setting up your .env file with real credentials
"""
import asyncio
import os
from dotenv import load_dotenv
from nokia_client import NokiaClient

load_dotenv()

async def test_apis():
    """Test all 5 Nokia APIs with a real phone number"""

    # Get configuration
    use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
    api_token = os.getenv("NOKIA_API_TOKEN")
    org_id = os.getenv("NOKIA_ORG_ID")

    print("=" * 60)
    print("🧪 CarePulse API Connection Test")
    print("=" * 60)
    print(f"Mode: {'MOCK' if use_mock else 'PRODUCTION'}")
    print(f"API Token: {'✅ Set' if api_token else '❌ Not set'}")
    print(f"Org ID: {'✅ Set' if org_id else '❌ Not set'}")
    print("=" * 60)

    if use_mock:
        print("\n⚠️  WARNING: Running in MOCK mode")
        print("Set USE_MOCK=false in .env to test real APIs\n")
    elif not api_token:
        print("\n❌ ERROR: NOKIA_API_TOKEN not set in .env")
        print("Get your token from: https://networkascode.nokia.io\n")
        return

    # Prompt for phone number
    print("\n📱 Enter the phone number to test (E.164 format, e.g., +34612345678)")
    phone_number = input("Phone number: ").strip()

    if not phone_number.startswith('+'):
        print("❌ Phone number must start with + (E.164 format)")
        return

    # Initialize client
    try:
        client = NokiaClient(
            use_mock=use_mock,
            api_token=api_token,
            organization_id=org_id
        )
        print(f"\n✅ Client initialized successfully")
    except Exception as e:
        print(f"\n❌ Failed to initialize client: {e}")
        return

    # Test API #1: Location Retrieval
    print("\n" + "-" * 60)
    print("📍 Testing API #1: Location Retrieval")
    print("-" * 60)
    try:
        location = await client.get_location(phone_number)
        print(f"✅ SUCCESS!")
        print(f"   Latitude: {location.get('latitude')}")
        print(f"   Longitude: {location.get('longitude')}")
        print(f"   Accuracy: {location.get('accuracy')} meters")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test API #3: Device Status
    print("\n" + "-" * 60)
    print("📱 Testing API #3: Device Status")
    print("-" * 60)
    try:
        device = await client.get_device_status(phone_number)
        print(f"✅ SUCCESS!")
        print(f"   Connected: {device.get('connected')}")
        print(f"   Network: {device.get('network_type')}")
        print(f"   Battery: {device.get('battery_level')}%")
        print(f"   Signal: {device.get('signal_strength')}%")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test API #4: SIM Swap Detection
    print("\n" + "-" * 60)
    print("🔐 Testing API #4: SIM Swap Detection")
    print("-" * 60)
    try:
        sim_swap = await client.check_sim_swap(phone_number)
        print(f"✅ SUCCESS!")
        print(f"   Recently Swapped: {sim_swap.get('swapped')}")
        print(f"   Days Since Swap: {sim_swap.get('days_since_swap')}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test API #2: Geofencing (Create)
    print("\n" + "-" * 60)
    print("🗺️  Testing API #2: Geofencing")
    print("-" * 60)
    try:
        # Use the location from API #1 if available
        test_lat = location.get('latitude', 41.3851)
        test_lng = location.get('longitude', 2.1734)

        geofence = await client.create_geofence(
            phone_number=phone_number,
            area_name="Test Safe Zone",
            latitude=test_lat,
            longitude=test_lng,
            radius_meters=500
        )
        print(f"✅ SUCCESS!")
        print(f"   Geofence ID: {geofence.get('id')}")
        print(f"   Name: {geofence.get('area_name')}")
        print(f"   Radius: {geofence.get('radius_meters')}m")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test API #5: QoS on Demand
    print("\n" + "-" * 60)
    print("⚡ Testing API #5: QoS on Demand")
    print("-" * 60)
    try:
        qos = await client.create_qos_session(
            phone_number=phone_number,
            duration_seconds=300,
            profile="emergency"
        )
        print(f"✅ SUCCESS!")
        print(f"   Session ID: {qos.get('session_id')}")
        print(f"   Profile: {qos.get('profile')}")
        print(f"   Priority: {qos.get('priority')}")
        print(f"   Bandwidth: {qos.get('allocated_bandwidth_mbps')} Mbps")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Close client
    await client.close()

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. If all tests passed, you're ready to use real APIs!")
    print("2. Add the phone number as a patient in the dashboard")
    print("3. Click 'Update Now' to fetch real-time data")
    print("4. The system will now use actual network data")
    print("\n")

if __name__ == "__main__":
    asyncio.run(test_apis())
