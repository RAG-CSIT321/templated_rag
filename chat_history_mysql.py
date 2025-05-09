import mysql.connector
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class ChatHistoryMySQL:
    def __init__(self):
        self.connection = self._create_connection()
        self._initialize_database()

    def _create_connection(self):
        """Create and return a MySQL database connection."""
        return mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="12345678",
            database="movie"
        )

    def _initialize_database(self):
        """Initialize the database with required tables if they don't exist."""
        cursor = self.connection.cursor()
        
        # Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY,
            username VARCHAR(255),
            created_at DATETIME NOT NULL
        )
        """)
        
        # Create sessions table with user relationship
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            session_name VARCHAR(255),
            created_at DATETIME NOT NULL,
            last_updated DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        # Create messages table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            role ENUM('user', 'assistant') NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
        )
        """)
        
        self.connection.commit()
        cursor.close()

    def create_user_if_not_exists(self, user_id: str, username: str = None):
        """Create a user record if it doesn't exist."""
        cursor = self.connection.cursor()
        
        cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (user_id, username, created_at) VALUES (%s, %s, %s)",
                (user_id, username, datetime.now())
            )
            self.connection.commit()
        
        cursor.close()

    def save_chat_history(self, user_id: str, session_id: str, messages: List[Dict], session_name: str = None):
        """Save chat history for a specific user's session."""
        self.create_user_if_not_exists(user_id)
        
        cursor = self.connection.cursor()
        now = datetime.now()
        
        # Check if session exists
        cursor.execute(
            "SELECT 1 FROM chat_sessions WHERE session_id = %s AND user_id = %s",
            (session_id, user_id)
        )
        session_exists = cursor.fetchone()
        
        if not session_exists:
            # Create new session
            cursor.execute(
                """INSERT INTO chat_sessions 
                (session_id, user_id, session_name, created_at, last_updated) 
                VALUES (%s, %s, %s, %s, %s)""",
                (session_id, user_id, session_name or f"Session {now.strftime('%Y-%m-%d')}", now, now)
            )
        else:
            # Update session
            cursor.execute(
                """UPDATE chat_sessions 
                SET last_updated = %s, session_name = COALESCE(%s, session_name)
                WHERE session_id = %s AND user_id = %s""",
                (now, session_name, session_id, user_id)
            )
        
        # Clear existing messages for this session
        cursor.execute(
            "DELETE FROM chat_messages WHERE session_id = %s",
            (session_id,)
        )
        
        # Insert new messages
        for message in messages:
            cursor.execute(
                """INSERT INTO chat_messages 
                (session_id, role, content, timestamp) 
                VALUES (%s, %s, %s, %s)""",
                (session_id, message['role'], message['content'], now)
            )
        
        self.connection.commit()
        cursor.close()

    def save_chat_message(self, user_id: str, session_id: str, role: str, content: str):
        """Append a single message to an existing session"""
        cursor = self.connection.cursor()
        now = datetime.now()
        
        # Insert the message without clearing existing ones
        cursor.execute(
            """INSERT INTO chat_messages 
            (session_id, role, content, timestamp) 
            VALUES (%s, %s, %s, %s)""",
            (session_id, role, content, now)
        )
        
        # Update session's last_updated time
        cursor.execute(
            "UPDATE chat_sessions SET last_updated = %s WHERE session_id = %s",
            (now, session_id)
        )
        
        self.connection.commit()
        cursor.close()

    def create_new_session(self, user_id: str, session_name: str = None) -> str:
        """Create a new chat session for a user and return the session ID."""
        cursor = self.connection.cursor()
        now = datetime.now()
        
        # Generate a new session ID
        session_id = f"sess_{now.timestamp()}_{user_id[:4]}"
        
        # Create the new session with initial empty messages
        cursor.execute(
            """INSERT INTO chat_sessions 
            (session_id, user_id, session_name, created_at, last_updated) 
            VALUES (%s, %s, %s, %s, %s)""",
            (session_id, user_id, session_name or f"Chat {now.strftime('%m/%d %H:%M')}", now, now)
        )
        
        self.connection.commit()
        cursor.close()
        return session_id
    
    def load_chat_history(self, user_id: str, session_id: str):
        cursor = self.connection.cursor(dictionary=True)
        
        # Kiểm tra session thuộc về user
        cursor.execute(
            """SELECT * FROM chat_sessions 
            WHERE session_id = %s AND user_id = %s""",
            (session_id, user_id)
        )
        session = cursor.fetchone()
        
        if not session:
            cursor.close()
            return None
        
        # Lấy tin nhắn
        cursor.execute(
            """SELECT role, content FROM chat_messages 
            WHERE session_id = %s ORDER BY timestamp ASC""",
            (session_id,)
        )
        messages = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        
        return {
            "messages": messages,
            "session_name": session.get('session_name', ''),
            "last_updated": session['last_updated'].strftime("%Y-%m-%d %H:%M:%S")
        }

    def list_user_sessions(self, user_id: str) -> List[Tuple[str, str, str]]:
        """List all chat sessions for a specific user."""
        self.create_user_if_not_exists(user_id)
        
        cursor = self.connection.cursor()
        
        cursor.execute(
            """SELECT session_id, session_name, last_updated 
            FROM chat_sessions 
            WHERE user_id = %s 
            ORDER BY last_updated DESC""",
            (user_id,)
        )
        
        sessions = [
            (row[0], row[1], row[2].strftime("%Y-%m-%d %H:%M:%S")) 
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        return sessions

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a specific session for a user."""
        cursor = self.connection.cursor()
        
        # Verify the session belongs to the user before deleting
        cursor.execute(
            "SELECT 1 FROM chat_sessions WHERE session_id = %s AND user_id = %s",
            (session_id, user_id)
        )
        if not cursor.fetchone():
            cursor.close()
            return False
        
        # Delete messages first (due to foreign key constraint)
        cursor.execute(
            "DELETE FROM chat_messages WHERE session_id = %s",
            (session_id,)
        )
        
        # Then delete the session
        cursor.execute(
            "DELETE FROM chat_sessions WHERE session_id = %s",
            (session_id,)
        )
        
        self.connection.commit()
        cursor.close()
        return True

    def __del__(self):
        """Close the database connection when the object is destroyed."""
        if hasattr(self, 'connection') and self.connection.is_connected():
            self.connection.close()


