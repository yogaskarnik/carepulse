#!/usr/bin/env python3
"""
CarePulse MCP Demo Script
Quick demonstration of Gemini AI Agent autonomously monitoring patients
"""
import asyncio
from gemini_agent import GeminiCarePulseAgent
from dotenv import load_dotenv
import os

load_dotenv()


async def demo_quick():
    """Quick 30-second demo for pitch"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🤖  CAREPULSE MCP + GEMINI AI AGENT DEMO                          ║
║                                                                      ║
║   Demonstrating autonomous patient monitoring using:                ║
║   • Model Context Protocol (MCP)                                    ║
║   • Google Gemini 2.5 Flash AI                                      ║
║   • 5 Nokia Network as Code APIs                                    ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("❌ ERROR: GEMINI_API_KEY not found in .env")
        return

    agent = GeminiCarePulseAgent(GEMINI_API_KEY)

    print("\n🎯 DEMO: Ask Gemini to monitor Maria Rodriguez")
    print("─" * 70)
    print("The AI will autonomously decide which APIs to call...\n")

    try:
        result = await agent.run_agent(
            "Monitor Maria Rodriguez (phone: +34640030646). "
            "Check her location, device status, and run a safety analysis. "
            "If she's at risk, tell me what actions I should take.",
            max_iterations=8
        )

        print("\n" + "═" * 70)
        print("📊 DEMO SUMMARY")
        print("═" * 70)

        if result.get('success'):
            print(f"✅ Agent successfully completed the task")
            print(f"📍 Tools called: {len(result.get('actions_taken', []))}")
            print(f"🔄 Iterations: {result.get('iterations', 0)}")
            print(f"\n🎯 Actions taken by Gemini AI:")
            for i, action in enumerate(result.get('actions_taken', []), 1):
                print(f"   {i}. {action['tool']}")
                print(f"      → {action['result'].get('message', 'Completed')}")
        else:
            print(f"❌ Agent encountered an error: {result.get('error')}")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")

    finally:
        await agent.close()

    print("\n" + "═" * 70)
    print("🎉 MCP DEMO COMPLETED!")
    print("═" * 70)
    print("""
Key Takeaways:
• Gemini AI autonomously called Nokia APIs through MCP
• No hardcoded workflows - the AI decided which tools to use
• True agentic behavior with function calling
• Scalable to any number of patients and scenarios
    """)


async def demo_emergency():
    """Emergency scenario demo"""
    print("\n\n🚨 EMERGENCY SCENARIO DEMO")
    print("=" * 70)

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    agent = GeminiCarePulseAgent(GEMINI_API_KEY)

    try:
        result = await agent.run_agent(
            "EMERGENCY: Maria Rodriguez (+34640030646) has a critical risk alert! "
            "Immediately: 1) Get her exact location, 2) Check device status, "
            "3) Activate emergency QoS to ensure connectivity, "
            "4) Run safety analysis and provide action plan.",
            max_iterations=8
        )

        print("\n🚑 EMERGENCY RESPONSE SUMMARY:")
        print(f"   Tools activated: {len(result.get('actions_taken', []))}")
        print(f"   Emergency QoS: {'✅ Activated' if any(a['tool'] == 'trigger_emergency_qos' for a in result.get('actions_taken', [])) else '❌ Not activated'}")

    finally:
        await agent.close()


if __name__ == "__main__":
    print("\n🚀 Starting CarePulse MCP Demo...\n")

    # Run quick demo
    asyncio.run(demo_quick())

    # Optional: Run emergency scenario
    # asyncio.run(demo_emergency())

    print("\n✨ Demo complete! Press Ctrl+C to exit.\n")
