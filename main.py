from flask import Flask, request, jsonify, render_template
from file_processor import FileProcessor
from query_engine import QueryEngine
from chat_history import ChatHistory
import os
from flask_cors import CORS
import datetime


app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})  

# Initialize components
query_engine = QueryEngine()
file_processor = FileProcessor(data_dir="data")
chat_history = ChatHistory(history_file="chat_history.json")

@app.route('/')
def home():
    return render_template('chat_ui.html')

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/api/interact_with_agent', methods=['POST'])
def interact_with_agent(self, prompt, session_id="default"):
        """Interact with chatbot and save history."""
        try:
            use_context = file_processor.retriever is not None
            response = query_engine.query(self.file_processor.retriever,prompt, use_context=use_context)

            response_text = response if isinstance(response, str) else str(response)

            if not response_text.strip():
                response_text = "I don't know. Please upload relevant files to provide more context."

            history = chat_history.load_chat_history(session_id) or {"messages": []}
            history["messages"].append({"role": "user", "content": prompt})
            history["messages"].append({"role": "assistant", "content": response_text})

            self.chat_history.save_chat_history(session_id, history["messages"])

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "messages": [{"role": "assistant", "content": response_text}],
            }

        except Exception as e:
            return {"status": "error", "message": f"Error interacting with the agent: {str(e)}"}


@app.route('/api/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"})
    if file:
        file_path = os.path.join("data", file.filename)
        file.save(file_path)
        result = file_processor.process_file(file_path)
        return jsonify({"message": result})
    return jsonify({"error": "File save failed"})

@app.route('/api/list_chat_sessions', methods=['GET'])
def list_chat_sessions():
    sessions = chat_history.list_chat_sessions()
    return jsonify(sessions)

@app.route('/api/load_chat_history/<session_id>', methods=['GET'])
def load_chat_history(session_id):
    history = chat_history.load_chat_history(session_id)
    if history:
        return jsonify(history)
    else:
        return jsonify({"error": "No history found"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


