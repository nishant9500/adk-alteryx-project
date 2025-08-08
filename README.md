# ADK Alteryx XML to BigQuery SQL Chatbot

## Overview
This project deploys a Flask app using Google Cloud's Gemini 2.0 Flash models in an Agent-to-Agent architecture.
- Main agent handles user input and XML routing.
- Validator agent checks Alteryx XML.
- SQL Generator agent converts valid XML into BigQuery SQL.

your-adk-project/
├── main.py
├── requirements.txt
├── .env
└── agents/
    ├── __init__.py
    ├── chatbot_agent.py
    └── xml_converter_agent.py


#how to use requirements
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
