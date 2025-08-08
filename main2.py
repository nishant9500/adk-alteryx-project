import asyncio
import os
import sys
from dotenv import load_dotenv
import logging
import re # Added for simple XML detection

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

# Import only 'Agent' as requested
from google.adk.agents import Agent # Changed from LlmAgent
from google.generativeai import GenerativeModel, configure as configure_gemini

# Load environment variables from .env file
load_dotenv()

# --- Global Gemini Configuration Parameters ---
# These will be used when instantiating GenerativeModel
GEMINI_MODEL_NAME = "gemini-2.0-flash"
USE_VERTEX_AI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").lower() == "true"
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Configure Gemini (only for API Key, Vertex AI config handled in GenerativeModel constructor) ---
if not USE_VERTEX_AI:
    if not API_KEY:
        logger.error("GOOGLE_API_KEY not set in .env. Please provide your Gemini API key.")
        sys.exit(1)
    configure_gemini(api_key=API_KEY)
    logger.info("Gemini configured using API Key (not Vertex AI).")
else:
    if not PROJECT_ID or not LOCATION:
        logger.error("GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION not set in .env for Vertex AI.")
        sys.exit(1)
    logger.info(f"Gemini will be configured for Vertex AI in GenerativeModel constructors: Project={PROJECT_ID}, Location={LOCATION}")


# --- Define XMLConverterAgent ---
# This agent handles the core logic for XML to SQL conversion
class XMLConverterAgent(Agent): # Changed to inherit from Agent
    def __init__(self, **kwargs):
        super().__init__(
            name="XMLConverterAgent",
            description="Specialized agent for validating, parsing Alteryx XML, and converting it to BigQuery SQL.",
            **kwargs
        )
        # Conditionally pass project/location to GenerativeModel
        model_args = {}
        if USE_VERTEX_AI:
            model_args['project'] = PROJECT_ID
            model_args['location'] = LOCATION

        self.model = GenerativeModel(GEMINI_MODEL_NAME, **model_args)
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
class ChatbotAgent(Agent): # Changed to inherit from Agent
    def __init__(self, **kwargs):
        super().__init__(
            name="ChatbotAgent",
            description="A friendly chatbot for general conversations and initiating Alteryx XML to BigQuery SQL conversions.",
            **kwargs
        )
        # Conditionally pass project/location to GenerativeModel
        model_args = {}
        if USE_VERTEX_AI:
            model_args['project'] = PROJECT_ID
            model_args['location'] = LOCATION

        self.model = GenerativeModel(GEMINI_MODEL_NAME, **model_args)
        logger.info("ChatbotAgent initialized.")

        # Register the tool that calls the XMLConverterAgent
        # Note: With Agent (not LlmAgent), tool calling needs to be explicitly managed in the run method
        self.add_tool(self.convert_alteryx_to_sql_tool) 

    async def run(self, context): # Agent's run method
        user_message = context.get_message_text()
        logger.info(f"ChatbotAgent received message: {user_message}")

        # Manual detection of Alteryx XML to trigger the tool
        # In a real application, this regex might need to be more robust
        if re.search(r'<AlteryxWorkflow>', user_message, re.IGNORECASE):
            logger.info("ChatbotAgent detected Alteryx XML. Calling conversion tool.")
            try:
                # Explicitly call the tool method
                sql_result = await self.convert_alteryx_to_sql_tool(alteryx_xml_code=user_message)
                return f"XML conversion initiated. Result:\n```sql\n{sql_result}\n```"
            except Exception as e:
                logger.error(f"ChatbotAgent: Error during tool call: {e}")
                return f"Sorry, I had trouble processing the XML conversion: {e}"
        else:
            logger.info("ChatbotAgent handling general query with LLM.")
            # Use the LLM for general chat
            try:
                response = await self.model.generate_content_async(user_message)
                return response.text.strip()
            except Exception as e:
                logger.error(f"ChatbotAgent: Error generating general response: {e}")
                return f"Sorry, I'm having trouble responding right now."

    async def convert_alteryx_to_sql_tool(self, alteryx_xml_code: str) -> str:
        """
        Converts Alteryx XML backend code to BigQuery SQL.
        This tool is called by the ChatbotAgent when the user provides Alteryx XML.
        Args:
            alteryx_xml_code: The Alteryx XML backend code string.
        Returns:
            The generated BigQuery SQL or an error message.
        """
        logger.info(f"ChatbotAgent: User requested XML conversion. Passing to XMLConverterAgent...")
        
        # Instantiate the XMLConverterAgent and call its processing method directly.
        # In a distributed A2A setup, this would involve HTTP calls via A2AClient.
        converter_agent = XMLConverterAgent(
            project_id=PROJECT_ID,
            location=LOCATION,
            api_key=API_KEY # This will be None if USE_VERTEX_AI is True, which is fine
        ) 
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
