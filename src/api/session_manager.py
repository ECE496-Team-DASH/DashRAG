"""
Session Manager
Handles user sessions, state persistence, and conversation history
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid


class Session:
    """Represents a user session"""

    def __init__(self, session_id: str):
        """
        Initialize a new session

        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.conversation_history: List[Dict[str, str]] = []
        self.metadata: Dict[str, Any] = {}

    def add_message(self, role: str, content: str):
        """
        Add a message to conversation history

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_accessed = datetime.now()

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get conversation history

        Args:
            limit: Optional limit on number of messages to return

        Returns:
            List of conversation messages
        """
        if limit:
            return self.conversation_history[-limit:]
        return self.conversation_history

    def is_expired(self, expiry_hours: int = 24) -> bool:
        """
        Check if session has expired

        Args:
            expiry_hours: Hours until session expires

        Returns:
            True if session is expired
        """
        expiry_time = self.last_accessed + timedelta(hours=expiry_hours)
        return datetime.now() > expiry_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "message_count": len(self.conversation_history),
            "metadata": self.metadata
        }


class SessionManager:
    """
    Manages user sessions and conversation state
    Handles session creation, retrieval, and cleanup
    """

    def __init__(self, expiry_hours: int = 24):
        """
        Initialize session manager

        Args:
            expiry_hours: Hours until sessions expire
        """
        self.sessions: Dict[str, Session] = {}
        self.expiry_hours = expiry_hours

    def create_session(self) -> str:
        """
        Create a new session

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = Session(session_id)
        print(f"Created session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID

        Args:
            session_id: Session identifier

        Returns:
            Session object or None if not found
        """
        session = self.sessions.get(session_id)

        if session and session.is_expired(self.expiry_hours):
            self.delete_session(session_id)
            return None

        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"Deleted session: {session_id}")
            return True
        return False

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        Add a message to a session's conversation history

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content

        Returns:
            True if message was added, False if session not found
        """
        session = self.get_session(session_id)
        if session:
            session.add_message(role, content)
            return True
        return False

    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> Optional[List[Dict[str, str]]]:
        """
        Get conversation history for a session

        Args:
            session_id: Session identifier
            limit: Optional limit on messages

        Returns:
            List of messages or None if session not found
        """
        session = self.get_session(session_id)
        if session:
            return session.get_history(limit)
        return None

    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions

        Returns:
            Number of sessions cleaned up
        """
        expired = [
            sid for sid, session in self.sessions.items()
            if session.is_expired(self.expiry_hours)
        ]

        for session_id in expired:
            self.delete_session(session_id)

        print(f"Cleaned up {len(expired)} expired sessions")
        return len(expired)

    def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        return len(self.sessions)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions

        Returns:
            List of session information dictionaries
        """
        return [session.to_dict() for session in self.sessions.values()]
