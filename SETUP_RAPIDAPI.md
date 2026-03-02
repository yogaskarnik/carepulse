# 🚀 Setting Up Nokia Network as Code via RapidAPI

Based on your screenshot, you're accessing Nokia APIs through **RapidAPI** with the "MWC hackathon 2026" organization.

---

## Step 1: Get Your RapidAPI Key

### Option A: From the API Page (Easiest)

1. **On the page you showed in the screenshot:**
   - Look for the **"Code Snippets"** or **"Test Endpoints"** tab (usually at the top)
   - Click on any endpoint (e.g., "retrieveLocation")
   - You'll see example code on the right side

2. **Find the headers section**, it will look like:
   ```javascript
   headers: {
     'X-RapidAPI-Key': 'abc123xyz...',  // ← THIS IS YOUR KEY!
     'X-RapidAPI-Host': 'network-as-code-nokia.p.rapidapi.com'
   }
   ```

3. **Copy the X-RapidAPI-Key value**

### Option B: From RapidAPI Dashboard

1. Go to: https://rapidapi.com/developer/apps
2. Find your app/subscription for "Nokia Network as Code"
3. Click on it
4. Copy the **X-RapidAPI-Key**

---

## Step 2: Configure Backend

### Update .env file:

```bash
cd backend
cp .env.rapidapi .env  # Use RapidAPI template
nano .env              # Or use your text editor
```

**Edit these values:**

```bash
# Switch to production mode
USE_MOCK=false

# RapidAPI credentials
RAPIDAPI_KEY=your_actual_key_from_rapidapi_here
RAPIDAPI_HOST=network-as-code-nokia.p.rapidapi.com

# Optional: Google Gemini for AI
GEMINI_API_KEY=your_gemini_key_here

# Database (SQLite is fine)
DATABASE_URL=sqlite:///./carepulse.db
```

---

## Step 3: Update main.py to use RapidAPI Client

Edit `backend/main.py`:

Find this line (around line 20):
```python
from nokia_client import NokiaClient
```

**Change it to:**
```python
from nokia_client_rapidapi import NokiaRapidAPIClient as NokiaClient
```

Find this section (around line 66-70):
```python
app.state.nokia_client = NokiaClient(
    use_mock=USE_MOCK,
    api_token=NOKIA_API_TOKEN,
    organization_id=NOKIA_ORG_ID
)
```

**Change it to:**
```python
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "network-as-code-nokia.p.rapidapi.com")

app.state.nokia_client = NokiaClient(
    use_mock=USE_MOCK,
    rapidapi_key=RAPIDAPI_KEY,
    rapidapi_host=RAPIDAPI_HOST
)
```

---

## Step 4: Available APIs

Based on your screenshot, you have access to:

### ✅ Available APIs:

| API | Version | Status | CarePulse Feature |
|-----|---------|--------|-------------------|
| 📍 **Location Retrieval** | v0.2.0 | ✅ Implemented | Live location tracking |
| 🗺️ **Geofencing** | v0.3.0 | ✅ Implemented | Safe zones |
| 📱 **Device Reachability Status** | v1 | ✅ Implemented | Device connectivity |
| 🌍 **Device Roaming Status** | v1 | ✅ Implemented | Roaming detection |
| 📍 **Location Verification** | v1.0.0 & v0.2.0 | ⚠️ Not used yet | Alternative to retrieval |

### ⚠️ Not Available (using mock data):

| API | Status | CarePulse Feature |
|-----|--------|-------------------|
| 🔐 **SIM Swap Detection** | ❌ Not in catalog | Fraud detection (simulated) |
| ⚡ **QoS on Demand** | ❌ Not in catalog | Emergency priority (simulated) |
| 🔋 **Device Status (Battery/Network)** | ❌ Not in catalog | Battery/Signal (simulated) |

**Note:** Scroll down in your API catalog sidebar to check if SIM Swap or QoS APIs are available below. If found, let me know and I'll add support!

---

## Step 5: Test the Connection

Create a test script:

```bash
cd backend
python test_rapidapi.py
```

If that file doesn't exist, create it:

```python
# test_rapidapi.py
import asyncio
import os
from dotenv import load_dotenv
from nokia_client_rapidapi import NokiaRapidAPIClient

load_dotenv()

async def test():
    client = NokiaRapidAPIClient(
        use_mock=False,
        rapidapi_key=os.getenv("RAPIDAPI_KEY"),
        rapidapi_host=os.getenv("RAPIDAPI_HOST")
    )

    phone = input("Enter phone number (+34...): ")

    print("\n📍 Testing Location Retrieval...")
    location = await client.get_location(phone)
    print(f"   Location: {location}")

    print("\n📱 Testing Device Reachability...")
    device = await client.get_device_status(phone)
    print(f"   Device: {device}")

    print("\n🌍 Testing Roaming Status...")
    roaming = await client.check_roaming(phone)
    print(f"   Roaming: {roaming}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(test())
```

---

## Step 6: Expected API Responses

### Location Retrieval v0.2.0

**Request:**
```json
{
  "device": {
    "phoneNumber": "+34612345678"
  },
  "maxAge": 60
}
```

**Response:**
```json
{
  "lastLocationTime": "2026-03-02T15:30:00Z",
  "location": {
    "latitude": 41.385063,
    "longitude": 2.173404,
    "accuracy": 50
  }
}
```

### Geofencing v0.3.0

**Request (createSubscription):**
```json
{
  "device": {
    "phoneNumber": "+34612345678"
  },
  "area": {
    "areaType": "CIRCLE",
    "center": {
      "latitude": 41.3851,
      "longitude": 2.1734
    },
    "radius": 500
  },
  "type": "ENTER-EXIT",
  "webhook": {
    "notificationUrl": "https://your-webhook.com/geofence",
    "notificationAuthToken": "token123"
  }
}
```

**Response:**
```json
{
  "subscriptionId": "abc-123-def-456",
  "startsAt": "2026-03-02T15:30:00Z",
  "expiresAt": "2026-03-03T15:30:00Z"
}
```

### Device Reachability Status v1

**Request:**
```json
{
  "device": {
    "phoneNumber": "+34612345678"
  }
}
```

**Response:**
```json
{
  "connectivityStatus": "REACHABLE"
}
```

Possible values: `REACHABLE`, `NOT_REACHABLE`, `UNKNOWN`

### Device Roaming Status v1

**Request:**
```json
{
  "device": {
    "phoneNumber": "+34612345678"
  }
}
```

**Response:**
```json
{
  "roaming": false,
  "countryCode": 214,
  "countryName": "Spain"
}
```

---

## Step 7: Important Geofencing Notes

⚠️ **Geofencing is webhook-based, not polling-based!**

The Nokia Geofencing API v0.3.0 requires:
1. A **webhook URL** (public HTTPS endpoint)
2. When device enters/exits zone → Nokia sends POST to your webhook
3. You can't "check" geofence status on-demand

### Options for Hackathon:

**Option A: Use ngrok for webhook**
```bash
# Install ngrok
ngrok http 8000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Use: https://abc123.ngrok.io/webhook/geofence
```

**Option B: Client-side geofence checking**
- Fetch location with Location Retrieval API
- Calculate distance client-side
- Already implemented in our code as fallback

For hackathon demo, **Option B is easier** (already works!).

---

## Step 8: Restart Backend

```bash
cd backend
python main.py
```

Look for:
```
INFO:     Started server process
INFO:     Waiting for application startup.
Mode: production
Using RapidAPI for Nokia Network as Code
```

---

## Step 9: Test in Dashboard

1. Open: http://localhost:5500/frontend/index.html
2. Add patient with **real phone number** (e.g., `+34612345678`)
3. Click "Update Now"
4. You should see:
   - ✅ Real GPS location on map
   - ✅ Device reachability status
   - ✅ Roaming status (if applicable)
   - ⚠️ Battery/Signal will be simulated (not available in API)
   - ⚠️ SIM Swap will be simulated (not available in API)

---

## Troubleshooting

### ❌ "401 Unauthorized"
- Check RAPIDAPI_KEY in .env is correct
- Make sure you copied the full key (no spaces)
- Key should start with something like `abc123...`

### ❌ "403 Forbidden"
- Your RapidAPI account might not have access to this API
- Check your subscription on RapidAPI dashboard
- Ensure you're in "MWC hackathon 2026" organization

### ❌ "404 Not Found"
- Check endpoint paths in `nokia_client_rapidapi.py`
- API versions might be different
- Try updating endpoint paths based on API documentation

### ❌ Phone number format error
- Must use E.164: `+34612345678`
- Include country code
- No spaces or dashes

### ❌ "Device not found" or "No location data"
- Device must be connected to mobile network
- GPS must be enabled
- May take 30-60 seconds for first reading
- Try with a different phone number

---

## Rate Limits

RapidAPI typically has rate limits:
- **Free tier**: ~100 requests/day
- **Hackathon tier**: Check your dashboard
- Auto-refresh uses ~120 calls/hour (30-second intervals)

**Tip:** Keep `USE_MOCK=true` during development, switch to `false` only for testing/demo.

---

## Next Steps

1. ✅ Get RapidAPI key from the code snippets section
2. ✅ Update `.env` with credentials
3. ✅ Update `main.py` to import RapidAPI client
4. ✅ Test with `test_rapidapi.py`
5. ✅ Restart backend
6. ✅ Add real patient in dashboard
7. ✅ Demo with real location data!

---

## For Judges/Demo

When presenting:
- ✅ "Using real Nokia Network as Code APIs via RapidAPI"
- ✅ "4 APIs integrated: Location, Geofencing, Reachability, Roaming"
- ✅ "Real-time tracking with actual network data"
- ⚠️ "SIM Swap and QoS simulated (not available in current API catalog)"

Good luck with your hackathon! 🚀
