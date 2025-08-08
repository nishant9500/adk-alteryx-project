import asyncio
import os
import sys
from dotenv import load_dotenv
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Attempt to import AgentWebApp with error handling ---
try:
    from google.adk.agent_web_app import AgentWebApp
    ADK_WEB_APP_AVAILABLE = True
    logger.info("Successfully imported AgentWebApp. ADK UI should be available.")
except ImportError as e:
    ADK_WEB_APP_AVAILABLE = False
    logger.error(f"Failed to import AgentWebApp: {e}")
    logger.error("This often means 'google-adk' is not fully installed or its components are missing.")
    logger.error("The ADK Web UI will not be available. Please verify your 'google-adk' installation.")

# Import other necessary ADK components and Gemini configuration
from google.adk.agents import LlmAgent
from google.adk.tools import tool # Changed: Import 'tool' from google.adk.tools
from google.generativeai import GenerativeModel, configure as configure_gemini

# Load environment variables from .env file
load_dotenv()

# --- Configure Gemini ---
# Prioritize Vertex AI configuration if specified in .env
if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").lower() == "true":
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    if not project_id or not location:
        logger.error("GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION not set in .env for Vertex AI.")
        sys.exit(1)
    configure_gemini(project=project_id, location=location)
    logger.info(f"Gemini configured for Vertex AI: Project={project_id}, Location={location}")
else:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not set in .env. Please provide your Gemini API key.")
        sys.exit(1)
    configure_gemini(api_key=api_key)
    logger.info("Gemini configured using API Key (not Vertex AI).")


# --- Define XMLConverterAgent ---
# This agent handles the core logic for XML to SQL conversion
class XMLConverterAgent(LlmAgent):
    def __init__(self, **kwargs):
        super().__init__(
            model=GenerativeModel("gemini-2.0-flash"), # Using gemini-2.0-flash as requested
            name="XMLConverterAgent",
            description="Specialized agent for validating, parsing Alteryx XML, and converting it to BigQuery SQL.",
            **kwargs
        )
        logger.info("XMLConverterAgent initialized.")

    async def process_alteryx_xml_to_sql(self, xml_code: str) -> str:
        """
        Validates, parses Alteryx XML, and converts it to BigQuery SQL.
        """
        logger.info("XMLConverterAgent: Starting XML processing...")
        
        # --- Step 1: XML Validation and Basic Parsing (using a dummy parser for this example) ---
        # In a real scenario, you'd use xml.etree.ElementTree or lxml for robust parsing
        # and add detailed Alteryx XML schema validation.
        try:
            # Simple check for XML structure
            if not xml_code.strip().startswith("<") or not xml_code.strip().endswith(">"):
                raise ValueError("Input does not appear to be valid XML.")
            
            # Simulate parsing - In a real app, you'd parse specific Alteryx nodes
            # For demonstration, we'll just acknowledge it's XML-like.
            logger.info("XMLConverterAgent: Input appears to be XML-like. Proceeding to LLM conversion.")
        except Exception as e:
            logger.error(f"XMLConverterAgent: Invalid XML format or parsing error: {e}")
            return f"Error: Invalid Alteryx XML format. Please check your XML syntax. Details: {e}"

        # --- Step 2: Convert to BigQuery SQL using Gemini-2.0-Flash ---
        # The LLM will perform the complex mapping from Alteryx concepts to SQL.
        prompt = f"""
        You are an expert Alteryx and BigQuery SQL developer.
        Your task is to convert the provided Alteryx XML backend code into a functional BigQuery Standard SQL query.
        Focus on the main data flow and transformations (e.g., Input Data, Select, Filter, Join, Union, Output Data).
        Infer table names, column names, and data types where necessary from the context of the Alteryx XML.
        Assume the source tables for Alteryx Input Data tools exist in BigQuery.
        
        Here is the Alteryx XML backend code:
        
        ```xml
        {xml_code}
        ```
        
        Based on this Alteryx XML, generate the corresponding BigQuery SQL.
        Do NOT include any explanations, preambles, or conversational text. Just provide the SQL code.
        If the XML is clearly not a valid Alteryx workflow or too complex/malformed to convert, 
        provide a concise error message starting with "Conversion Error:" instead of SQL.
        """
        
        try:
            logger.info("XMLConverterAgent: Calling Gemini model for SQL generation...")
            response = await self.model.generate_content_async(prompt)
            sql_result = response.text.strip()
            logger.info("XMLConverterAgent: Received response from Gemini model.")
            
            # Basic check to see if the LLM generated something that looks like SQL
            if not sql_result.upper().startswith(("SELECT", "CREATE", "INSERT", "MERGE", "CONVERSION ERROR:")):
                 logger.warning(f"XMLConverterAgent: LLM did not generate expected SQL format or error message. Raw response start: {sql_result[:100]}...")
                 return f"Conversion Error: The AI model could not generate valid BigQuery SQL from the provided Alteryx XML. Please review the XML. Raw AI response: {sql_result}"

            return sql_result
        except Exception as e:
            logger.error(f"XMLConverterAgent: Error during SQL generation with LLM: {e}")
            return f"Conversion Error: Failed to generate BigQuery SQL using the AI model. Details: {e}"

# --- Define ChatbotAgent ---
# This agent is the user-facing interface and orchestrates the call to XMLConverterAgent.
class ChatbotAgent(LlmAgent):
    def __init__(self, **kwargs):
        super().__init__(
            model=GenerativeModel("gemini-2.0-flash"), # Using gemini-2.0-flash as requested
            name="ChatbotAgent",
            description="A friendly chatbot for general conversations and initiating Alteryx XML to BigQuery SQL conversions.",
            **kwargs
        )
        # Register the tool that calls the XMLConverterAgent
        self.add_tool(self.convert_alteryx_to_sql_tool) 
        logger.info("ChatbotAgent initialized.")

    @tool
    async def convert_alteryx_to_sql_tool(self, alteryx_xml_code: str) -> str:
        """
        Converts Alteryx XML backend code to BigQuery SQL.
        This tool should be called by the ChatbotAgent when the user provides Alteryx XML.
        Args:
            alteryx_xml_code: The Alteryx XML backend code string.
        Returns:
            The generated BigQuery SQL or an error message.
        """
        logger.info(f"ChatbotAgent: User requested XML conversion. Passing to XMLConverterAgent...")
        
        # Instantiate the XMLConverterAgent and call its processing method directly.
        # In a distributed A2A setup, this would involve HTTP calls via A2AClient.
        converter_agent = XMLConverterAgent() 
        try:
            result = await converter_agent.process_alteryx_xml_to_sql(alteryx_xml_code)
            logger.info("ChatbotAgent: Received result from XMLConverterAgent.")
            return result
        except Exception as e:
            logger.error(f"ChatbotAgent: Error calling XMLConverterAgent: {e}")
            return f"Sorry, I encountered an internal error trying to convert your XML: {e}"

# --- Main execution function ---
async def main():
    chatbot_agent = ChatbotAgent()
    
    if ADK_WEB_APP_AVAILABLE:
        # Launch the ADK web app with the ChatbotAgent as the primary agent
        # The XMLConverterAgent is called internally as a tool by ChatbotAgent
        adk_web_app = AgentWebApp(agents=[chatbot_agent], host="0.0.0.0", port=8080)
        
        logger.info("ADK Web UI is attempting to start.")
        logger.info("Please access it via your VM's external IP address and port 8080.")
        logger.info("Example: http://<YOUR_VM_EXTERNAL_IP>:8080")

        await adk_web_app.run()
    else:
        logger.error("ADK Web UI cannot be started due to missing 'AgentWebApp'.")
        logger.error("Please resolve the 'ImportError' for 'google.adk.agent_web_app'.")
        logger.info("You can still interact with the ChatbotAgent via CLI if you implement a CLI runner.")
        # Example of a simple CLI runner if UI is not available (for debugging only)
        # from google.adk.runners import Runner
        # runner = Runner(agent=chatbot_agent, app_name="alteryx-converter-app")
        # while True:
        #     user_input = input("You: ")
        #     if user_input.lower() == 'exit':
        #         break
        #     response = await runner.run_async(user_input)
        #     print(f"Agent: {response.text}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nADK Web UI stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception(f"An unhandled error occurred: {e}")
