import os
import json
from datetime import datetime

class ChatHistory:
    def __init__(self, history_file="chat_history.json"):
        self.history_file = history_file
        self.history = self._load_all_histories()

    def _load_all_histories(self):
        """Load all chat histories from the file."""
        if not os.path.exists(self.history_file):
            # Create an empty history file if it doesn't exist
            print("Chat history file not found. Creating a new one.")
            with open(self.history_file, "w") as file:
                json.dump({}, file)
            return {}

        with open(self.history_file, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                print("Error: chat_history.json is corrupted. Recreating the file.")
                with open(self.history_file, "w") as file:
                    json.dump({}, file)
                return {}

    def save_chat_history(self, session_id, messages):
        """Save chat history for a specific session."""
        self.history[session_id] = {
            "messages": messages,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.history_file, "w") as file:
            json.dump(self.history, file, indent=4)

    def load_chat_history(self, session_id):
        """Load specific chat history."""
        return self.history.get(session_id)

    def list_chat_sessions(self):
        """
        List all chat sessions with metadata.
        """
        try:
            # Access the `self.history` attribute directly
            sessions = [(session_id, details["last_updated"]) for session_id, details in self.history.items()]
            print("Sessions from ChatHistory:", sessions)  # Debug print
            return sessions
        except Exception as e:
            print(f"Error in list_chat_sessions: {e}")  # Debug error
            return []



