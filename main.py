from flask import Flask, request, jsonify
from file_processor import FileProcessor
from query_engine import QueryEngine
from chat_history import ChatHistory
from config import Config
import os
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})  

# Initialize components
Config.setup_environment()
query_engine = QueryEngine()
file_processor = FileProcessor(data_dir="data", query_engine=query_engine)
chat_history = ChatHistory(history_file="chat_history.json")

@app.route('/')
def home():
    return 'Hello, World!'

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/api/interact_with_agent', methods=['POST'])
def interact_with_agent():
    data = request.json
    prompt = data.get('prompt', '')
    session_id = data.get('session_id', 'default')

    try:
        used_context =query_engine.query_engine is not None
        response = query_engine.query(prompt, use_context=used_context)
    except Exception as e:
        logging.error(f"Error in QueryEngine: {e}")
        return jsonify({"error": f"Query Engine Error: {str(e)}"}), 500  # Trả về mã lỗi 500
    response_content = response if isinstance(response, dict) else str(response)
    if not response_content.strip():
        response_content = "I don't know. Please upload relevant files to provide more context."
    chat_history.save_chat_history(session_id, [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response_content}
    ])
    return jsonify({"messages": [{"role": "assistant", "content": response_content}]})


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


