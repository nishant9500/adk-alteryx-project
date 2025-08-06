# ADK Alteryx XML to BigQuery SQL Chatbot

## Overview
This project deploys a Flask app using Google Cloud's Gemini 2.0 Flash models in an Agent-to-Agent architecture.
- Main agent handles user input and XML routing.
- Validator agent checks Alteryx XML.
- SQL Generator agent converts valid XML into BigQuery SQL.

## Setup

### 1. Build & Run (locally or on GCP VM)
```bash
docker-compose up --build
```

### 2. Access
Visit: `http://<your-vm-ip>:8080`

### 3. Chat Endpoint
POST to `/chat` with:
```json
{
  "message": "<AlteryxWorkflow></AlteryxWorkflow>"
}
```