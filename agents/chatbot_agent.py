from google.adk.agents import Agent, tool, LlmAgent
from google.generativeai import GenerativeModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatbotAgent(LlmAgent):
    def __init__(self, **kwargs):
        super().__init__(
            model=GenerativeModel("gemini-2.0-flash"),
            name="ChatbotAgent",
            description="A friendly chatbot for general conversations and initiating Alteryx XML to BigQuery SQL conversions.",
            **kwargs
        )
        self.add_tool(self.convert_alteryx_to_sql) # Register the tool

    @tool
    async def convert_alteryx_to_sql(self, alteryx_xml_code: str) -> str:
        """
        Converts Alteryx XML backend code to BigQuery SQL.
        This tool should be called when the user provides Alteryx XML.
        Args:
            alteryx_xml_code: The Alteryx XML backend code string.
        Returns:
            The generated BigQuery SQL or an error message.
        """
        logger.info(f"ChatbotAgent received XML for conversion. Passing to XMLConverterAgent...")
        # Simulate calling the XMLConverterAgent via A2A or direct function call
        # For simplicity within the same process, we can directly call its method
        from .xml_converter_agent import XMLConverterAgent
        
        # In a real A2A setup across services, you'd use A2A client here:
        # from google.adk.a2a.clients import A2AClient
        # client = A2AClient()
        # task_request = TaskRequest(skill="convert_alteryx_xml", inputs={"xml_code": alteryx_xml_code})
        # task = await client.create_task(agent_url="http://localhost:8001/run", task_request=task_request) # Assuming XMLConverterAgent runs on 8001
        # result = await client.wait_for_task_result(task.id)
        # return result.outputs.get("bigquery_sql", "Conversion failed.")

        converter_agent = XMLConverterAgent() # Instantiate the converter agent
        try:
            # Directly call the conversion method (for in-process A2A simulation)
            result = await converter_agent.process_alteryx_xml_to_sql(alteryx_xml_code)
            return result
        except Exception as e:
            logger.error(f"Error during XML conversion: {e}")
            return f"Sorry, I encountered an error during XML to BigQuery SQL conversion: {e}"
