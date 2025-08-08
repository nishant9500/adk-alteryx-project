from google.adk.agents import Agent, tool, LlmAgent
from google.generativeai import GenerativeModel
import xml.etree.ElementTree as ET
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class XMLConverterAgent(LlmAgent):
    def __init__(self, **kwargs):
        super().__init__(
            model=GenerativeModel("gemini-2.0-flash"),
            name="XMLConverterAgent",
            description="Specialized agent for validating, parsing Alteryx XML, and converting it to BigQuery SQL.",
            **kwargs
        )
        # No tools needed for this agent if it's primarily an internal processing unit
        # It exposes a method that the ChatbotAgent calls

    async def process_alteryx_xml_to_sql(self, xml_code: str) -> str:
        """
        Validates, parses Alteryx XML, and converts it to BigQuery SQL.
        """
        logger.info("XMLConverterAgent: Starting XML processing...")
        
        # --- Step 1: XML Validation and Basic Parsing ---
        try:
            root = ET.fromstring(xml_code)
            logger.info("XMLConverterAgent: XML is well-formed.")
            # Add more specific Alteryx XML validation here if needed
            # e.g., check for specific root tags, required attributes
        except ET.ParseError as e:
            logger.error(f"XMLConverterAgent: Invalid XML format: {e}")
            return f"Error: Invalid Alteryx XML format. Please check your XML syntax. Details: {e}"
        except Exception as e:
            logger.error(f"XMLConverterAgent: Error parsing XML: {e}")
            return f"Error: Could not parse Alteryx XML. Details: {e}"

        # --- Step 2: Convert to BigQuery SQL (This is where Gemini-2.0-Flash shines) ---
        sql_output = await self._generate_sql_from_xml(root, xml_code)
        logger.info("XMLConverterAgent: Finished SQL generation.")
        return sql_output

    async def _generate_sql_from_xml(self, xml_root: ET.Element, original_xml: str) -> str:
        """
        Uses Gemini-2.0-Flash to convert the parsed Alteryx XML to BigQuery SQL.
        This is a complex task and will rely heavily on the LLM's understanding.
        For a production system, you might build a more deterministic parser + LLM for tricky parts.
        """
        # Example: Extracting relevant parts of the XML for the LLM prompt
        # You'll need to tailor this based on common Alteryx XML structures.
        simplified_xml_elements = []
        for elem in xml_root.iter():
            # Only include elements with text or specific attributes
            if elem.text and elem.text.strip():
                simplified_xml_elements.append(f"<{elem.tag}> {elem.text.strip()}")
            elif elem.attrib:
                simplified_xml_elements.append(f"<{elem.tag} {elem.attrib}>")

        simplified_xml_representation = "\n".join(simplified_xml_elements[:50]) # Limit to avoid token issues

        prompt = f"""
        You are an expert Alteryx and BigQuery SQL developer.
        Your task is to convert the provided Alteryx XML backend code into a functional BigQuery Standard SQL query.
        Focus on the main data flow and transformations (e.g., Input Data, Select, Filter, Join, Union, Output Data).
        Infer table names, column names, and data types where necessary from the context of the Alteryx XML.
        Assume the source tables for Alteryx Input Data tools exist in BigQuery.
        
        Here is the Alteryx XML snippet (or its simplified representation):
        
        ```xml
        {original_xml}
        ```
        
        Based on this Alteryx XML, generate the corresponding BigQuery SQL.
        If the XML represents multiple distinct data flows, generate one comprehensive SQL query or multiple queries as appropriate.
        Prioritize clarity and correctness. Do NOT include any explanations, just the SQL code.
        If the XML is clearly not a valid Alteryx workflow or too complex to convert, provide a concise error message instead of SQL.
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            # Assuming the response is directly the SQL
            sql_result = response.text.strip()
            
            # Basic check if it looks like SQL
            if not sql_result.upper().startswith(("SELECT", "CREATE", "INSERT", "MERGE")):
                 logger.warning(f"XMLConverterAgent: LLM did not generate expected SQL format. Raw response: {sql_result[:200]}...")
                 return f"Could not generate valid BigQuery SQL from the provided Alteryx XML. Please ensure it's a convertible Alteryx workflow. LLM's response: {sql_result}"

            return sql_result
        except Exception as e:
            logger.error(f"XMLConverterAgent: Error during SQL generation with LLM: {e}")
            return f"Error: Failed to generate BigQuery SQL using the AI model. Details: {e}"
