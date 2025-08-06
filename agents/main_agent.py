from agents.validator_agent import ValidatorAgent
from agents.sql_generator_agent import SQLGeneratorAgent

class MainAgent:
    def __init__(self):
        self.validator = ValidatorAgent()
        self.sql_generator = SQLGeneratorAgent()

    def is_xml(self, input_str):
        return input_str.strip().startswith("<") and input_str.strip().endswith(">")

    def handle_input(self, input_text):
        if self.is_xml(input_text):
            validation_result = self.validator.validate(input_text)
            if validation_result.get("status") == "valid":
                sql = self.sql_generator.generate_sql(validation_result["cleaned_xml"])
                return sql
            else:
                return "Invalid XML format. Please check the structure."
        else:
            return "Hello! I can answer your questions or help convert Alteryx XML to BigQuery SQL."