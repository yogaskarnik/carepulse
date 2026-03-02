"""
Quick test script for RapidAPI connection
Run this to verify your RapidAPI key works
"""
import asyncio
import os
from dotenv import load_dotenv
from nokia_client_rapidapi import NokiaRapidAPIClient

load_dotenv()

async def test():
    print("=" * 60)
    print("🧪 CarePulse RapidAPI Connection Test")
    print("=" * 60)

    # Check configuration
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    rapidapi_host = os.getenv("RAPIDAPI_HOST", "network-as-code.p-eu.rapidapi.com")
    rapidapi_header_host = os.getenv("RAPIDAPI_HEADER_HOST", "network-as-code.nokia.rapidapi.com")
    use_mock = os.getenv("USE_MOCK", "true").lower() == "true"

    print(f"Mode: {'MOCK' if use_mock else 'PRODUCTION'}")
    print(f"RapidAPI Key: {'✅ Set' if rapidapi_key else '❌ Not set'}")
    print(f"Connection Host: {rapidapi_host}")
    print(f"Header Host: {rapidapi_header_host}")
    print("=" * 60)

    if use_mock:
        print("\n⚠️  WARNING: Running in MOCK mode")
        print("Set USE_MOCK=false in .env to test real APIs\n")
    elif not rapidapi_key:
        print("\n❌ ERROR: RAPIDAPI_KEY not set in .env")
        print("\nTo get your key:")
        print("1. Go to the Nokia API page on RapidAPI")
        print("2. Click 'Code Snippets' or 'Test Endpoint'")
        print("3. Find X-RapidAPI-Key in the headers")
        print("4. Copy and add to .env file\n")
        return

    # Get phone number
    print("\n📱 Enter phone number to test (E.164 format)")
    print("   Example: +34612345678")
    phone = input("   Phone: ").strip()

    if not phone.startswith('+'):
        print("❌ Phone number must start with + (E.164 format)")
        return

    # Initialize client
    try:
        client = NokiaRapidAPIClient(
            use_mock=use_mock,
            rapidapi_key=rapidapi_key,
            rapidapi_host=rapidapi_host,
            rapidapi_header_host=rapidapi_header_host
        )
        print(f"\n✅ Client initialized successfully\n")
    except Exception as e:
        print(f"\n❌ Failed to initialize client: {e}\n")
        return

    # Test Location Retrieval
    print("-" * 60)
    print("📍 Testing Location Retrieval v0.2.0")
    print("-" * 60)
    location = None
    try:
        location = await client.get_location(phone)
        print(f"✅ SUCCESS!")
        print(f"   Latitude: {location.get('latitude')}")
        print(f"   Longitude: {location.get('longitude')}")
        print(f"   Accuracy: {location.get('accuracy')} meters")
        print(f"   Timestamp: {location.get('timestamp')}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test Device Reachability
    print("\n" + "-" * 60)
    print("📱 Testing Device Reachability Status v1")
    print("-" * 60)
    try:
        device = await client.get_device_status(phone)
        print(f"✅ SUCCESS!")
        print(f"   Connected: {device.get('connected')}")
        print(f"   Status: {device.get('connectivity_status')}")
        print(f"   Network: {device.get('network_type')}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test Roaming Status
    print("\n" + "-" * 60)
    print("🌍 Testing Device Roaming Status v1")
    print("-" * 60)
    try:
        roaming = await client.check_roaming(phone)
        print(f"✅ SUCCESS!")
        print(f"   Roaming: {roaming.get('roaming')}")
        print(f"   Country: {roaming.get('country')}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test Geofencing
    print("\n" + "-" * 60)
    print("🗺️  Testing Geofencing v0.3.0")
    print("-" * 60)
    try:
        if location.get('latitude') and location.get('longitude'):
            geofence = await client.create_geofence(
                phone_number=phone,
                area_name="Test Zone",
                latitude=location['latitude'],
                longitude=location['longitude'],
                radius_meters=500
            )
            print(f"✅ SUCCESS!")
            print(f"   Geofence ID: {geofence.get('id')}")
            print(f"   Area: {geofence.get('area_name')}")
            print(f"   Radius: {geofence.get('radius_meters')}m")
        else:
            print(f"⚠️  SKIPPED: No location data to create geofence")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Close client
    await client.close()

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60)

    if not use_mock:
        print("\n✅ Real API tests passed! Next steps:")
        print("1. Restart backend: python main.py")
        print("2. Open dashboard: http://localhost:5500/frontend/index.html")
        print("3. Add patient with phone number: " + phone)
        print("4. Click 'Update Now' to see real data\n")
    else:
        print("\n⚠️  Running in mock mode. To test real APIs:")
        print("1. Set USE_MOCK=false in .env")
        print("2. Add your RAPIDAPI_KEY to .env")
        print("3. Run this test again\n")

if __name__ == "__main__":
    asyncio.run(test())
