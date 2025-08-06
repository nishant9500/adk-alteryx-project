from flask import Flask, request, jsonify
from agents.main_agent import MainAgent

app = Flask(__name__)
agent = MainAgent()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get("message", "")
    response = agent.handle_input(user_input)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)