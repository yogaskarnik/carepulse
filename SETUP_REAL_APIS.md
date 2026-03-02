# 🚀 Setting Up Real Nokia Network as Code APIs

This guide will help you switch from mock data to real Nokia Network as Code APIs for your hackathon project.

## Prerequisites

- ✅ Nokia Network as Code account (https://networkascode.nokia.io)
- ✅ Mobile device with active SIM card
- ✅ Phone number in E.164 format (e.g., +34612345678)
- ✅ Backend server running (Python/FastAPI)

---

## Step 1: Get Nokia API Credentials

### 1.1 Create Nokia Account
1. Go to https://networkascode.nokia.io
2. Sign up or log in
3. Complete any required verification

### 1.2 Create Application
1. Navigate to **Developer Portal** → **Applications**
2. Click **"Create New Application"**
3. Name it: `CarePulse Hackathon`
4. Description: `AI-powered safety network for elderly care`

### 1.3 Subscribe to APIs
Subscribe to all 5 required APIs:

| API Name | Purpose | Priority |
|----------|---------|----------|
| 📍 Location Retrieval | Real-time GPS tracking | High |
| 🗺️ Geofencing | Safe zone monitoring | High |
| 📱 Device Status | Network/battery status | High |
| 🔐 SIM Swap Detection | Fraud prevention | Medium |
| ⚡ QoS on Demand | Emergency priority | High |

### 1.4 Get Credentials
1. Go to **Application Details**
2. Copy your **API Token** (looks like: `eyJhbGciOiJSUzI1...`)
3. Copy your **Organization ID** (if displayed)

---

## Step 2: Get Google Gemini API Key (Recommended)

1. Visit: https://aistudio.google.com/app/apikey
2. Click **"Create API Key"**
3. Copy the key (looks like: `AIzaSyC...`)

**Note:** Without Gemini, the system will use basic pattern detection instead of AI analysis.

---

## Step 3: Configure Backend

### 3.1 Update .env File

Edit `backend/.env`:

```bash
# Operating Mode - SWITCH TO PRODUCTION
USE_MOCK=false

# Nokia Network as Code API
NOKIA_API_TOKEN=your_actual_token_here
NOKIA_ORG_ID=your_org_id_here

# Google Gemini API
GEMINI_API_KEY=your_gemini_key_here

# Database (SQLite is fine for hackathon)
DATABASE_URL=sqlite:///./carepulse.db
```

**Replace:**
- `your_actual_token_here` → Your Nokia API token
- `your_org_id_here` → Your Nokia organization ID
- `your_gemini_key_here` → Your Gemini API key

### 3.2 Save and Verify

```bash
cd backend
cat .env  # Verify your credentials are set correctly
```

---

## Step 4: Test API Connection

Run the test script to verify everything works:

```bash
cd backend
python test_nokia_api.py
```

**Enter your phone number** when prompted (e.g., `+34612345678`)

### Expected Output:

```
🧪 CarePulse API Connection Test
============================================================
Mode: PRODUCTION
API Token: ✅ Set
Org ID: ✅ Set
============================================================

📱 Enter the phone number to test (E.164 format)
Phone number: +34612345678

✅ Client initialized successfully

------------------------------------------------------------
📍 Testing API #1: Location Retrieval
------------------------------------------------------------
✅ SUCCESS!
   Latitude: 41.385063
   Longitude: 2.173404
   Accuracy: 50 meters

... (tests for all 5 APIs)

✅ Test complete!
```

---

## Step 5: Restart Backend

Restart the backend to apply changes:

```bash
# Stop current backend (Ctrl+C)
# Then restart:
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Step 6: Use Real Data in Dashboard

### 6.1 Add Patient with Real Phone Number

1. Open dashboard: http://localhost:5500/frontend/index.html
2. Click **"Add Patient"**
3. Fill in details:
   - **Full Name**: Test Patient
   - **Phone Number**: `+34612345678` (YOUR real phone number)
   - Emergency contacts (optional)
4. Click **"Create Patient"**

### 6.2 Monitor Patient

1. Click on the patient in sidebar
2. Click **"Update Now"** button
3. Watch real data populate:
   - ✅ Real GPS location on map
   - ✅ Real network type (5G/4G/3G)
   - ✅ Real battery level
   - ✅ Real signal strength
   - ✅ AI risk analysis

### 6.3 Create Safe Zones

1. Click **"+"** next to Safe Zones
2. Add zones based on real locations:
   - Home address
   - Workplace
   - Hospital/Clinic
3. System will detect when device enters/exits zones

---

## Step 7: Test Features

### Real-Time Tracking
- Dashboard updates every 30 seconds automatically
- WebSocket connection shows live updates
- Map displays actual device location

### Geofencing
- Walk outside a safe zone with the device
- System should detect and show alert

### Device Status
- Check battery level matches device
- Network type should match (5G/4G/3G)
- Signal strength should reflect actual signal

### AI Analysis
- System learns normal patterns over time
- Unusual locations trigger risk scores
- Recommendations based on actual behavior

---

## Troubleshooting

### ❌ "API Token not set"
- Check `.env` file has `NOKIA_API_TOKEN=...`
- No spaces around `=`
- Token starts with `eyJ...` or similar

### ❌ "403 Forbidden" or "401 Unauthorized"
- Token expired or invalid
- Generate new token from Nokia portal
- Check you subscribed to all 5 APIs

### ❌ "Phone number format invalid"
- Must use E.164 format: `+[country code][number]`
- Examples: `+34612345678`, `+14155551234`
- Remove spaces and dashes

### ❌ "Location not available"
- Device must have GPS/location enabled
- Device must be connected to mobile network
- May take 30-60 seconds for first reading

### ❌ Mock data still showing
- Verify `USE_MOCK=false` in `.env`
- Restart backend after changing `.env`
- Check backend logs for "Mode: production"

---

## Production Checklist

Before demo/submission:

- [ ] `USE_MOCK=false` in `.env`
- [ ] All 5 Nokia APIs tested and working
- [ ] Real phone number added as patient
- [ ] Location showing on map correctly
- [ ] Safe zones created for demo locations
- [ ] AI analysis generating recommendations
- [ ] WebSocket connection stable
- [ ] Export data functionality works

---

## API Rate Limits

**Important for Hackathon:**

- Nokia APIs have rate limits (typically 100-1000 calls/day)
- Auto-refresh is every 30 seconds (120 updates/hour)
- For 24-hour hackathon: ~2,880 location calls
- Use mock mode during development, real APIs for demo

**Conserve API calls:**
- Develop features with `USE_MOCK=true`
- Switch to `USE_MOCK=false` only for testing/demo
- Each "Update Now" click = 5 API calls (one per API)

---

## Support

If you encounter issues:

1. **Nokia API Issues**: https://networkascode.nokia.io/support
2. **Check logs**: Backend terminal shows detailed error messages
3. **Test script**: Run `python test_nokia_api.py` to isolate issues
4. **Gemini issues**: Can run without AI (`GEMINI_API_KEY` optional)

---

## Next Steps

✅ **APIs working?** → Focus on demo scenario:
   - Show patient at home (inside safe zone)
   - Move outside safe zone → trigger alert
   - Show AI recommendations
   - Export report as CSV

✅ **Ready for judges?** → Prepare talking points:
   - "Real Nokia APIs, not mock data"
   - "5 Network as Code APIs integrated"
   - "AI learns patterns, not just rules"
   - "From 6 hours to find patient, to 30 seconds"

Good luck with your hackathon! 🚀
