import asyncio
import os
from dotenv import load_dotenv
from google.adk.agent_web_app import AgentWebApp
from google.adk.agents import Agent
from google.adk.testing.agent_test_runner import AgentTestRunner
from google.generativeai import configure as configure_gemini

# Load environment variables from .env file
load_dotenv()

# Configure Gemini for Vertex AI (if GOOGLE_GENAI_USE_VERTEXAI=TRUE)
if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").lower() == "true":
    configure_gemini(
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION")
    )
else:
    # Configure Gemini with API Key if not using Vertex AI
    configure_gemini(api_key=os.getenv("GOOGLE_API_KEY"))

# Import your custom agents
from agents.chatbot_agent import ChatbotAgent
from agents.xml_converter_agent import XMLConverterAgent # Even if not directly exposed, it's part of the app

async def main():
    # Instantiate your agents
    chatbot_agent = ChatbotAgent()
    xml_converter_agent = XMLConverterAgent() # This agent is called internally by ChatbotAgent

    # Define the root agent that will be the primary one in the UI
    # You could make a more complex orchestrator if needed, but for simple routing,
    # the ChatbotAgent's tool use handles the handoff.
    root_agent = chatbot_agent 

    # Launch the ADK web app
    # You can specify the port if 8080 is already in use or you prefer another
    # adk_web_app = AgentWebApp(agents=[root_agent], host="0.0.0.0", port=8080)
    adk_web_app = AgentWebApp(agents=[root_agent], host="0.0.0.0", port=8080) # Host on 0.0.0.0 for external access
    
    print(f"ADK Web UI running at http://0.0.0.0:8080. Access via your VM's external IP.")
    print("Go to your VM's external IP address and port 8080 in your browser.")
    print("Example: http://<YOUR_VM_EXTERNAL_IP>:8080")

    await adk_web_app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nADK Web UI stopped.")
