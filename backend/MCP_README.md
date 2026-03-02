# CarePulse MCP Integration

## Overview

CarePulse implements **Model Context Protocol (MCP)** to enable AI agents (specifically Google Gemini) to autonomously monitor patient safety using Nokia Network as Code APIs.

## Architecture

```
User Request
     ↓
Gemini AI Agent (MCP Client)
     ↓
Function Calling / Tool Use
     ↓
MCP Server (carepulse_tools)
     ↓
Nokia Network APIs (5 APIs)
     ↓
Real-time Patient Data
```

## MCP Tools Exposed

The following CarePulse tools are exposed via MCP:

### 1. `get_patient_location`
- **API**: Nokia Location Retrieval v0
- **Purpose**: Real-time GPS tracking
- **Returns**: Latitude, longitude, accuracy, timestamp

### 2. `check_device_status`
- **API**: Nokia Device Status v0.5.1
- **Purpose**: Network connectivity monitoring
- **Returns**: Connection status, network type (5G), signal strength, battery

### 3. `check_sim_swap`
- **API**: Nokia SIM Swap Detection v1.0.0
- **Purpose**: Fraud detection and security
- **Returns**: Whether SIM was recently swapped

### 4. `trigger_emergency_qos`
- **API**: Nokia QoS on Demand v0
- **Purpose**: Emergency network priority
- **Returns**: QoS session details with guaranteed bandwidth/latency

### 5. `create_safe_zone`
- **API**: Nokia Geofencing v0.3.0
- **Purpose**: Virtual boundary alerts
- **Returns**: Geofence subscription details

### 6. `analyze_patient_safety`
- **Purpose**: Comprehensive AI-powered safety analysis
- **Uses**: All above APIs + Gemini AI
- **Returns**: Risk score (0-100), risk level, factors, recommendations

## How It Works

### Agentic Workflow

1. **User makes request**: "Check if Maria is safe"
2. **Gemini decides autonomously**: Which tools to call, in what order
3. **MCP executes tools**: Calls Nokia APIs through MCP server
4. **Gemini analyzes results**: Makes intelligent decisions based on data
5. **Takes action if needed**: Activates emergency QoS, creates geofences, etc.

### Example Autonomous Flow

```
User: "Is Maria safe?"
  ↓
Gemini: "I'll check her location first"
  → Calls: get_patient_location(+34640030646)
  ← Result: 41.38°N, 2.17°E, Barcelona
  ↓
Gemini: "Let me check device connectivity"
  → Calls: check_device_status(+34640030646)
  ← Result: Connected, 5G, 85% signal, 75% battery
  ↓
Gemini: "Running comprehensive safety analysis"
  → Calls: analyze_patient_safety(+34640030646)
  ← Result: Risk Score 65 (HIGH) - Outside safe zones
  ↓
Gemini: "High risk detected! Activating emergency network"
  → Calls: trigger_emergency_qos(+34640030646, 600)
  ← Result: QoS activated for 10 minutes
  ↓
Gemini: "Maria is at high risk. She's outside her safe zones.
        I've activated emergency network priority.
        Recommendation: Contact her immediately."
```

## Why MCP + Gemini?

### Benefits

1. **True Agentic AI**: Gemini makes autonomous decisions, not following hardcoded rules
2. **Scalable**: Add new tools without changing agent code
3. **Intelligent**: AI understands context and makes smart choices
4. **Workflow Automation**: Can monitor multiple patients simultaneously
5. **Extensible**: Easy to add more Nokia APIs or external services

### Hackathon Requirements Met

✅ **Agentic apps**: Gemini agent makes autonomous decisions
✅ **Workflow automations**: Automated patient monitoring workflows
✅ **Tools and data sources integrations**: Nokia APIs exposed as MCP tools
✅ **Model Context Protocol**: Standard MCP implementation
✅ **Google Gemini**: Using Gemini 2.5 Flash with function calling

## Running the Demo

### Quick Demo (30 seconds)

```bash
cd ~/carepulse/backend
source venv/bin/activate
python3 demo_mcp.py
```

### Custom Agent Query

```python
from gemini_agent import GeminiCarePulseAgent
import asyncio

async def main():
    agent = GeminiCarePulseAgent(GEMINI_API_KEY)
    result = await agent.run_agent(
        "Check if patient +34640030646 is safe and create a safe zone around their current location"
    )
    print(result)

asyncio.run(main())
```

## Technical Implementation

### MCP Server (`mcp_server.py`)
- Defines 6 tools as Python async functions
- Each tool wraps Nokia API calls
- Tools are described in MCP-compatible format
- Execution function routes tool calls to implementations

### Gemini Agent (`gemini_agent.py`)
- Uses Gemini Function Calling (equivalent to MCP)
- Maintains conversation history
- Iterates until task complete or max iterations
- Handles errors gracefully

### Demo Script (`demo_mcp.py`)
- Quick 30-second demo for pitches
- Shows autonomous agent behavior
- Demonstrates multi-tool workflows

## Key Differentiators

**vs. Traditional Automation:**
- ❌ Traditional: Hardcoded if-then-else rules
- ✅ CarePulse MCP: AI decides what to do based on context

**vs. Basic AI Integration:**
- ❌ Basic: AI generates text only
- ✅ CarePulse MCP: AI takes actions through Nokia APIs

**vs. Other Teams:**
- ❌ Others: Likely using 2-3 APIs with fixed workflows
- ✅ CarePulse: 5 APIs + Gemini + MCP = Autonomous agent

## Future Extensions

With MCP architecture, we can easily add:
- Multiple patient monitoring simultaneously
- Integration with hospital systems (HL7/FHIR)
- Predictive analytics (ML models as MCP tools)
- Voice interface (Gemini processes natural language)
- Integration with emergency services (112/911 APIs)

## Conclusion

CarePulse's MCP integration demonstrates:
1. ✅ Advanced AI capabilities (agentic behavior)
2. ✅ Innovative use of Nokia APIs (5 APIs orchestrated by AI)
3. ✅ Scalable architecture (add tools without changing agent)
4. ✅ Real-world value (autonomous patient safety monitoring)

**This is not just an API integration - it's an AI agent that thinks and acts autonomously to protect elderly patients.**
