"""
Request context management for tracking requests across layers
"""
import uuid
from contextvars import ContextVar
from typing import Optional

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)

def generate_request_id() -> str:
    """Generate unique request ID"""
    return f"req_{uuid.uuid4().hex[:12]}"

def generate_session_id() -> str:
    """Generate unique session ID"""
    return f"sess_{uuid.uuid4().hex[:12]}"

def set_request_id(request_id: str):
    """Set request ID in context"""
    request_id_var.set(request_id)

def get_request_id() -> Optional[str]:
    """Get request ID from context"""
    return request_id_var.get()

def set_session_id(session_id: str):
    """Set session ID in context"""
    session_id_var.set(session_id)

def get_session_id() -> Optional[str]:
    """Get session ID from context"""
    return session_id_var.get()

def clear_context():
    """Clear all context variables"""
    request_id_var.set(None)
    session_id_var.set(None)
