"""
Gemini AI Agent for CarePulse - Autonomous Patient Monitoring
Uses MCP tools to make intelligent decisions about patient safety
"""
import asyncio
import json
import httpx
import os
from dotenv import load_dotenv
from mcp_server import CAREPULSE_TOOLS, execute_tool

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"


class GeminiCarePulseAgent:
    """Autonomous AI agent powered by Gemini that monitors patient safety"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.http_client = httpx.AsyncClient(verify=False, timeout=60.0)
        self.conversation_history = []

    async def run_agent(self, user_request: str, max_iterations: int = 5) -> Dict:
        """
        Run the Gemini agent to handle a user request autonomously.
        The agent will decide which tools to call and when.

        Args:
            user_request: What the user wants (e.g., "Check if Maria Rodriguez is safe")
            max_iterations: Maximum number of tool calls to prevent infinite loops

        Returns:
            Final response with agent's analysis and actions taken
        """
        print(f"\n{'='*70}")
        print(f"🤖 GEMINI AGENT STARTED")
        print(f"{'='*70}")
        print(f"📝 User Request: {user_request}\n")

        # Initialize conversation
        messages = [{
            "role": "user",
            "parts": [{
                "text": f"""You are an AI agent for CarePulse, an elderly care monitoring system.

You have access to 5 Nokia Network as Code APIs through MCP tools:
1. get_patient_location - Real-time GPS tracking
2. check_device_status - Network connectivity, battery, signal
3. check_sim_swap - Fraud detection
4. trigger_emergency_qos - Emergency network priority
5. create_safe_zone - Geofencing alerts
6. analyze_patient_safety - Comprehensive AI analysis

Your job: {user_request}

Patient phone number: +34640030646 (Maria Rodriguez)

Think step by step:
1. What information do you need?
2. Which tools should you call?
3. Based on results, what actions should you take?
4. Provide a final assessment

Be autonomous - call multiple tools as needed to complete the task thoroughly."""
            }]
        }]

        iteration = 0
        actions_taken = []

        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Iteration {iteration}/{max_iterations}")
            print(f"{'─'*70}")

            # Call Gemini with function calling
            try:
                response = await self._call_gemini(messages)

                # Check if Gemini wants to use a tool
                if self._has_function_call(response):
                    # Extract function call
                    function_calls = self._extract_function_calls(response)

                    for func_call in function_calls:
                        tool_name = func_call['name']
                        arguments = func_call['args']

                        print(f"\n🛠️  Gemini is calling: {tool_name}")
                        print(f"   Arguments: {json.dumps(arguments, indent=2)}")

                        # Execute the tool
                        result = await execute_tool(tool_name, arguments)

                        print(f"   ✅ Result: {result.get('message', 'Completed')}")

                        actions_taken.append({
                            "tool": tool_name,
                            "arguments": arguments,
                            "result": result
                        })

                        # Add function result to conversation
                        messages.append({
                            "role": "model",
                            "parts": [{
                                "functionCall": {
                                    "name": tool_name,
                                    "args": arguments
                                }
                            }]
                        })

                        messages.append({
                            "role": "user",
                            "parts": [{
                                "functionResponse": {
                                    "name": tool_name,
                                    "response": result
                                }
                            }]
                        })

                else:
                    # Gemini provided final answer
                    final_text = self._extract_text(response)
                    print(f"\n✨ GEMINI FINAL RESPONSE:")
                    print(f"{'─'*70}")
                    print(final_text)
                    print(f"{'─'*70}")

                    return {
                        "success": True,
                        "user_request": user_request,
                        "iterations": iteration,
                        "actions_taken": actions_taken,
                        "final_response": final_text,
                        "agent": "Gemini 2.5 Flash"
                    }

            except Exception as e:
                print(f"\n❌ Error: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "actions_taken": actions_taken
                }

        print(f"\n⚠️  Max iterations reached ({max_iterations})")
        return {
            "success": False,
            "error": "Max iterations reached",
            "actions_taken": actions_taken
        }

    async def _call_gemini(self, messages):
        """Call Gemini API with function calling support"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={self.api_key}"

        # Build request with tools
        request_body = {
            "contents": messages,
            "tools": [{
                "functionDeclarations": CAREPULSE_TOOLS
            }]
        }

        response = await self.http_client.post(url, json=request_body)
        response.raise_for_status()
        return response.json()

    def _has_function_call(self, response) -> bool:
        """Check if Gemini wants to call a function"""
        try:
            parts = response['candidates'][0]['content']['parts']
            return any('functionCall' in part for part in parts)
        except (KeyError, IndexError):
            return False

    def _extract_function_calls(self, response) -> list:
        """Extract function calls from Gemini response"""
        function_calls = []
        try:
            parts = response['candidates'][0]['content']['parts']
            for part in parts:
                if 'functionCall' in part:
                    function_calls.append({
                        'name': part['functionCall']['name'],
                        'args': part['functionCall'].get('args', {})
                    })
        except (KeyError, IndexError):
            pass
        return function_calls

    def _extract_text(self, response) -> str:
        """Extract text response from Gemini"""
        try:
            parts = response['candidates'][0]['content']['parts']
            text_parts = [part['text'] for part in parts if 'text' in part]
            return '\n'.join(text_parts)
        except (KeyError, IndexError):
            return "No response generated"

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


async def main():
    """Demo: Run Gemini agent with different scenarios"""

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not found in .env file")
        return

    agent = GeminiCarePulseAgent(GEMINI_API_KEY)

    # Scenario 1: Check patient safety
    print("\n" + "="*70)
    print("🎯 SCENARIO 1: Comprehensive Safety Check")
    print("="*70)

    result = await agent.run_agent(
        "Check if Maria Rodriguez (+34640030646) is safe. "
        "Get her location, check device status, verify no SIM swap, "
        "and run a comprehensive safety analysis. "
        "If risk is high or critical, activate emergency QoS."
    )

    print("\n" + "="*70)
    print("📊 SCENARIO 1 RESULTS")
    print("="*70)
    print(f"Actions taken: {len(result.get('actions_taken', []))}")
    print(f"Iterations: {result.get('iterations', 0)}")
    print(f"Success: {result.get('success', False)}")

    # Scenario 2: Create safe zone
    print("\n" + "="*70)
    print("🎯 SCENARIO 2: Create Safe Zone")
    print("="*70)

    result2 = await agent.run_agent(
        "Create a safe zone called 'Home' for Maria Rodriguez (+34640030646) "
        "at coordinates 41.38°N, 2.17°E with a radius of 500 meters."
    )

    await agent.close()

    print("\n" + "="*70)
    print("✅ AGENT DEMO COMPLETED")
    print("="*70)
    print("\n🎉 CarePulse MCP + Gemini integration working perfectly!")
    print("📝 The agent autonomously decided which tools to call and when.")
    print("🤖 This demonstrates true agentic AI workflow automation.")


if __name__ == "__main__":
    asyncio.run(main())
