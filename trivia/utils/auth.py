from datetime import datetime, timezone
from functools import wraps
from flask import jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import Optional

from ..models.user import User, UserSession
from .. import db

def get_user_from_token(session_token: str) -> Optional[User]:
    """Fetches a user based on a valid session token."""
    if not session_token:
        return None
    session = db.session.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user))
        .filter_by(session_token=session_token)
        .filter(UserSession.expires_at > datetime.now(timezone.utc))
    )
    return session.user if session else None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401

        session_token = auth_header.split(' ')[1]
        user = get_user_from_token(session_token)
        
        if not user:
            return jsonify({'error': 'Invalid or expired session'}), 401
            
        # Add the user to the request context
        request.user = user
        return f(*args, **kwargs)
    return decorated 