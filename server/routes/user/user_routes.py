import secrets
from ... import app
from ...database import db
from ...models import User, UserSession
from ...utils.auth import require_auth
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from flask import request, jsonify, Blueprint

user_bp = Blueprint('user', __name__)

@user_bp.route('/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    if not data or not all(k in data for k in ['username', 'email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400

    username = data['username']
    email = data['email']
    password = data['password']

    # Check if user already exists
    existing_user = db.session.scalar(
        select(User).filter((User.username == username) | (User.email == email))
    )
    if existing_user:
        return jsonify({'error': 'Username or email already exists'}), 409

    # Create new user
    new_user = User(username=username, email=email)
    new_user.set_password(password) # Hash password

    try:
        db.session.add(new_user)
        db.session.commit()
        # Generate session token after user creation
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        new_session = UserSession(user_id=new_user.id, session_token=session_token, expires_at=expires_at)
        new_user.last_login = datetime.now(timezone.utc)
        db.session.add(new_session)
        db.session.commit()
        user_data = {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email,
            'createdAt': new_user.created_at.isoformat() if hasattr(new_user, 'created_at') and new_user.created_at else None,
            'lastLogin': new_user.last_login.isoformat() if new_user.last_login else None
        }
        return jsonify({
            'message': 'User registered successfully',
            'user': user_data,
            'sessionToken': session_token
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error during registration: {e}")
        return jsonify({'error': 'Could not register user'}), 500


@user_bp.route('/auth/login', methods=['POST'])
def login():
    """Login a user and create a session."""
    data = request.get_json()
    if not data or not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400

    email = data['email']
    password = data['password']

    user = db.session.scalar(select(User).filter_by(email=email))

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Generate session token
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7) # Use timezone-aware

    # Create session
    new_session = UserSession(user_id=user.id, session_token=session_token, expires_at=expires_at)

    # Update last login
    user.last_login = datetime.now(timezone.utc) # Use timezone-aware

    try:
        db.session.add(new_session)
        db.session.commit()
        # Construct user data with camelCase keys
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'createdAt': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
            'lastLogin': user.last_login.isoformat() if user.last_login else None
        }
        return jsonify({
            'sessionToken': session_token,
            'user': user_data
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error during login: {e}")
        return jsonify({'error': 'Could not process login'}), 500


@user_bp.route('/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout a user by invalidating their session."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid authorization header'}), 401

    session_token = auth_header.split(' ')[1]

    session_to_delete = db.session.scalar(select(UserSession).filter_by(session_token=session_token))

    if session_to_delete:
        try:
            db.session.delete(session_to_delete)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error during logout: {e}")
            return jsonify({'error': 'Could not process logout'}), 500

    return jsonify({'message': 'Logged out successfully'}) # Return success even if token was invalid/expired


@user_bp.route('/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get the current authenticated user's information."""
    # Get the user from the request context
    user = request.user

    if not user:
        return jsonify({'error': 'Invalid or expired session'}), 401

    # Construct response with camelCase keys
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'createdAt': user.created_at.isoformat() if user.created_at else None,
        'lastLogin': user.last_login.isoformat() if user.last_login else None
    })