import os
import json
import uuid
from datetime import datetime

class SessionManager:
    def __init__(self, storage_dir="data/sessions"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_session_path(self, session_id):
        return os.path.join(self.storage_dir, f"{session_id}.json")

    def save_session(self, session_id, messages, session_name=None, agent_type=None):
        """Saves the session messages and metadata to a JSON file."""
        path = self._get_session_path(session_id)
        
        # Load existing data to preserve name/type if not provided
        existing_data = {}
        if os.path.exists(path):
            with open(path, "r") as f:
                existing_data = json.load(f)
        
        data = {
            "session_id": session_id,
            "name": session_name or existing_data.get("name", "New Session"),
            "agent_type": agent_type or existing_data.get("agent_type", "General"),
            "created_at": existing_data.get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "messages": messages
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    def load_session(self, session_id):
        """Loads a session by ID."""
        path = self._get_session_path(session_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return None

    def list_sessions(self, agent_type=None):
        """Lists all available sessions sorted by updated_at desc, optionally filtered by agent_type."""
        sessions = []
        if not os.path.exists(self.storage_dir):
            return []
            
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                        
                        # Filter by agent_type if provided
                        if agent_type and data.get("agent_type") != agent_type:
                            continue
                            
                        sessions.append({
                            "id": data.get("session_id", filename.replace(".json", "")),
                            "name": data.get("name", "Untitled Session"),
                            "agent_type": data.get("agent_type", "General"),
                            "updated_at": data.get("updated_at", "")
                        })
                except:
                    continue
        
        # Sort by updated_at descending
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions

    def create_new_session(self):
        """Creates a new session ID."""
        return str(uuid.uuid4())

    def update_session_name(self, session_id, new_name):
        """Updates the name of a session."""
        session = self.load_session(session_id)
        if session:
            self.save_session(session_id, session["messages"], new_name)
