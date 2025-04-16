import os
import random
import secrets
import bcrypt
from datetime import datetime, timedelta, timezone # Use timezone-aware datetimes
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, UniqueConstraint, CheckConstraint, select # Import necessary SQLAlchemy functions/classes
from sqlalchemy.orm import joinedload, Mapped, mapped_column, relationship, selectinload # Use newer SQLAlchemy 2.0 style
from typing import List, Optional # For type hinting
from functools import wraps

# --- Load Environment Variables ---
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# --- App Configuration ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Database Configuration using environment variables
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432') # Default PostgreSQL port

# Configure SQLAlchemy - Use 'postgresql+psycopg2' driver
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable modification tracking overhead

# Initialize SQLAlchemy extension
db = SQLAlchemy(app)

# --- SQLAlchemy Models (Define based on your SQL schema) ---

class User(db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    sessions: Mapped[List["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    events_created: Mapped[List["Event"]] = relationship(back_populates="creator", foreign_keys="Event.user_id")
    user_questions: Mapped[List["UserGeneratedQuestion"]] = relationship(back_populates="creator")

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    session_token: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

class Category(db.Model):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(256), unique=True, nullable=False)

    # Relationships
    trivia_questions: Mapped[List["TriviaQuestion"]] = relationship(back_populates="category")
    rounds: Mapped[List["Round"]] = relationship(back_populates="category")
    user_questions: Mapped[List["UserGeneratedQuestion"]] = relationship(back_populates="category")

class TriviaQuestion(db.Model):
    __tablename__ = 'trivia_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(db.Text, nullable=False)
    answer: Mapped[str] = mapped_column(db.Text, nullable=False)
    category_id: Mapped[int] = mapped_column(db.ForeignKey('categories.id'), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(db.String(10), nullable=False, index=True) # 'easy', 'medium', or 'hard'
    air_date: Mapped[Optional[datetime]] = mapped_column(db.Date, nullable=True)
    original_value: Mapped[Optional[int]] = mapped_column(db.SmallInteger, nullable=True)
    original_round: Mapped[Optional[int]] = mapped_column(db.SmallInteger, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)

    # Relationships
    category: Mapped["Category"] = relationship(back_populates="trivia_questions")
    round_associations: Mapped[List["RoundQuestion"]] = relationship(back_populates="preset_question")

class Event(db.Model):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id'))
    event_date: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(db.String(50), default='draft', server_default='draft')
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(db.Boolean, default=False, server_default='false')

    # Relationships
    creator: Mapped["User"] = relationship(back_populates="events_created", foreign_keys=[user_id])
    rounds: Mapped[List["Round"]] = relationship(back_populates="event", cascade="all, delete-orphan", order_by="Round.round_number")

class NormalizedQuestion(db.Model):
    __tablename__ = 'normalized_questions_view'
    
    round_question_id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(db.ForeignKey('rounds.id'))
    question_number: Mapped[int] = mapped_column()
    question_id: Mapped[int] = mapped_column()
    question_type: Mapped[str] = mapped_column(db.String(10))
    question: Mapped[str] = mapped_column(db.Text)
    answer: Mapped[str] = mapped_column(db.Text)
    difficulty: Mapped[str] = mapped_column(db.String(10))
    category_id: Mapped[Optional[int]] = mapped_column()
    category_name: Mapped[str] = mapped_column(db.String(256))

    __table_args__ = (
        {'info': {'is_view': True}}  # Mark this as a view
    )

    # Make it effectively immutable
    __mapper_args__ = {
        'confirm_deleted_rows': False
    }

class Round(db.Model):
    __tablename__ = 'rounds'
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(db.ForeignKey('events.id', ondelete='CASCADE'), index=True)
    category_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('categories.id'), nullable=True)
    round_number: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint('event_id', 'round_number', name='uq_rounds_event_round'),)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="rounds")
    category: Mapped[Optional["Category"]] = relationship(back_populates="rounds")
    questions: Mapped[List["RoundQuestion"]] = relationship(back_populates="round", cascade="all, delete-orphan", order_by="RoundQuestion.question_number")
    normalized_questions: Mapped[List["NormalizedQuestion"]] = relationship(
        primaryjoin="Round.id == NormalizedQuestion.round_id",
        order_by="NormalizedQuestion.question_number",
        viewonly=True # Crucial: Indicates this relationship is read-only via the view
    )


class UserGeneratedQuestion(db.Model):
    __tablename__ = 'user_generated_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(db.Text, nullable=False)
    answer: Mapped[str] = mapped_column(db.Text, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('categories.id'), index=True)
    difficulty: Mapped[str] = mapped_column(db.String(10), nullable=False) # 'easy', 'medium', or 'hard'
    created_by: Mapped[Optional[int]] = mapped_column(db.ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(db.String(50), default='active', server_default='active') # active, flagged, deleted, etc.
    notes: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)

    # Relationships
    category: Mapped[Optional["Category"]] = relationship(back_populates="user_questions")
    creator: Mapped[Optional["User"]] = relationship(back_populates="user_questions")
    round_associations: Mapped[List["RoundQuestion"]] = relationship(back_populates="user_question")


class RoundQuestion(db.Model):
    __tablename__ = 'round_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(db.ForeignKey('rounds.id', ondelete='CASCADE'))
    question_number: Mapped[int] = mapped_column(nullable=False)
    preset_question_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('trivia_questions.id'), index=True, nullable=True)
    user_question_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('user_generated_questions.id'), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('round_id', 'question_number', name='uq_round_questions_round_number'),
        CheckConstraint(
            '(preset_question_id IS NULL AND user_question_id IS NOT NULL) OR (preset_question_id IS NOT NULL AND user_question_id IS NULL)',
            name='ck_round_questions_question_type'
        )
    )

    # Relationships
    round: Mapped["Round"] = relationship(back_populates="questions")
    preset_question: Mapped[Optional["TriviaQuestion"]] = relationship(back_populates="round_associations")
    user_question: Mapped[Optional["UserGeneratedQuestion"]] = relationship(back_populates="round_associations")

    # Property to get the actual question object regardless of type
    @property
    def question_object(self):
       return self.preset_question or self.user_question

# --- Helper Function for Auth ---

def get_user_from_token(session_token: str) -> Optional[User]:
    """Fetches a user based on a valid session token."""
    if not session_token:
        return None
    session = db.session.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user)) # Eager load user data
        .filter_by(session_token=session_token)
        .filter(UserSession.expires_at > datetime.now(timezone.utc)) # Use timezone-aware comparison
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

# --- API Routes ---

@app.route('/api/question', methods=['GET'])
def get_question():
    """Get a random trivia question, optionally filtered."""
    difficulty = request.args.get('difficulty')
    category_id = request.args.get('category_id', type=int)

    # Base query
    stmt = select(TriviaQuestion).options(joinedload(TriviaQuestion.category)) # Eager load category

    # Apply filters
    if difficulty:
        stmt = stmt.filter(TriviaQuestion.difficulty == difficulty)
    if category_id:
        stmt = stmt.filter(TriviaQuestion.category_id == category_id)

    # Order randomly and fetch one
    stmt = stmt.order_by(func.random()).limit(1)
    q = db.session.scalar(stmt)

    if not q:
        return jsonify({"error": "No questions found with these criteria"}), 404

    # Construct response with camelCase keys
    return jsonify({
        'id': q.id,
        'question': q.question,
        'answer': q.answer,
        'category': q.category.name if q.category else None,
        'difficulty': q.difficulty
        # No snake_case keys here, so no change needed from previous state, but good practice to verify.
    })

@app.route('/api/check-answer', methods=['POST'])
def check_answer():
    """Check if the provided answer matches the correct answer."""
    data = request.get_json()
    if not data or 'answer' not in data or 'question_id' not in data:
        return jsonify({'error': 'Missing answer or question_id'}), 400

    question_id = data['question_id']
    user_answer = data['answer']

    # Fetch the question (only checks preset questions currently)
    q = db.session.get(TriviaQuestion, question_id) # Efficient lookup by primary key

    if not q:
        # TODO: Potentially check UserGeneratedQuestion as well if needed
        return jsonify({'error': 'Question not found'}), 404

    correct_answer = q.answer

    # Fuzzy matching
    score = fuzz.ratio(user_answer.lower(), correct_answer.lower())
    is_correct = score >= 80 # Threshold for correctness

    return jsonify({
        'correct': is_correct,
        'score': score,
        'correct_answer': correct_answer
    })

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all available trivia categories."""
    categories = db.session.scalars(
        select(Category).order_by(Category.name)
    ).all()

    # Construct response with camelCase keys (no change needed as keys were simple)
    return jsonify([{"id": c.id, "name": c.name} for c in categories])

@app.route('/api/difficulties', methods=['GET'])
def get_difficulties():
    """Get all available difficulty levels."""
    return jsonify(['easy', 'medium', 'hard']) # Keep as is, not DB dependent

@app.route('/api/categories/active', methods=['GET'])
def get_active_categories():
    """Get categories that have a minimum number of questions."""
    min_questions = request.args.get('min_questions', default=80, type=int)

    stmt = (
        select(Category.id, Category.name, func.count(TriviaQuestion.id).label('question_count'))
        .outerjoin(TriviaQuestion, Category.id == TriviaQuestion.category_id) # Use outerjoin
        .group_by(Category.id, Category.name)
        .having(func.count(TriviaQuestion.id) >= min_questions)
        .order_by(Category.name)
    )
    results = db.session.execute(stmt).all() # Returns Row objects

    # Manually create dicts with camelCase keys
    categories_data = [
        {"id": row.id, "name": row.name, "questionCount": row.question_count} # Renamed question_count
        for row in results
    ]
    return jsonify(categories_data) # Return the transformed data

@app.route('/api/category/<int:category_id>/questions', methods=['GET'])
def get_category_questions(category_id):
    """Get multiple random questions from a specific category."""
    count = min(request.args.get('count', default=10, type=int), 50) # Cap at 50

    # Verify category exists first
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    # Fetch random questions
    stmt = (
        select(TriviaQuestion)
        .filter_by(category_id=category_id)
        .order_by(func.random())
        .limit(count)
    )
    questions = db.session.scalars(stmt).all()

    if not questions:
        return jsonify({"error": "No questions found in this category"}), 404

    # Construct response with camelCase keys (no change needed as keys were simple)
    questions_data = [
        {
            'id': q.id,
            'question': q.question,
            'answer': q.answer,
            'category': category.name, # Use the fetched category name
            'difficulty': q.difficulty
        } for q in questions
    ]
    return jsonify(questions_data)

# --- Auth Routes ---

@app.route('/api/auth/register', methods=['POST'])
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
        # Construct user data with camelCase keys
        user_data = {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email
            # 'createdAt': new_user.created_at.isoformat() if new_user.created_at else None # Example if needed later
        }
        return jsonify({
            'message': 'User registered successfully',
            'user': user_data
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error during registration: {e}")
        return jsonify({'error': 'Could not register user'}), 500


@app.route('/api/auth/login', methods=['POST'])
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
            'email': user.email
            # 'lastLogin': user.last_login.isoformat() if user.last_login else None # Example if needed later
        }
        return jsonify({
            'session_token': session_token, # Key is already fine
            'user': user_data
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error during login: {e}")
        return jsonify({'error': 'Could not process login'}), 500


@app.route('/api/auth/logout', methods=['POST'])
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


@app.route('/api/auth/me', methods=['GET'])
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
        'createdAt': user.created_at.isoformat() if user.created_at else None, # Renamed created_at
        'lastLogin': user.last_login.isoformat() if user.last_login else None # Renamed last_login
    })

# --- Event/Round/Question Routes ---

@app.route('/api/events/<int:event_id>', methods=['GET'])
@require_auth
def get_event(event_id):
    """Fetch an event and its associated rounds by event ID."""
    # Eager load rounds
    stmt = (
        select(Event)
        .options(selectinload(Event.rounds)) # Use selectinload for potentially better performance on lists
        .filter_by(id=event_id)
    )
    event = db.session.scalar(stmt)


    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    # Check permission AFTER fetching, to give correct 404 vs 403
    if event.user_id != request.user.id:
        return jsonify({'error': 'Permission denied'}), 403


    # Structure the response with camelCase keys
    rounds_data = [
        {
            'id': r.id,
            'roundNumber': r.round_number, # Renamed round_number
            'name': r.name,
            'createdAt': r.created_at.isoformat() if r.created_at else None, # Renamed created_at
            'categoryId': r.category_id, # Added categoryId
            # 'categoryName': r.category.name if r.category else None # Example if needed later
        } for r in event.rounds
    ]
    
    event_data = {
        'id': event.id,
        'name': event.name,
        'eventDate': event.event_date.isoformat() if event.event_date else None, # Renamed event_date
        'status': event.status,
        'description': event.description,
        'rounds': rounds_data,
        'createdAt': event.created_at.isoformat() if event.created_at else None, # Renamed created_at
        'userId': event.user_id, # Added userId
        # 'updatedAt': event.updated_at.isoformat() if event.updated_at else None # Assuming you add an updated_at field later
    }
    return jsonify(event_data)

@app.route('/api/rounds/<int:round_id>/questions', methods=['GET'])
@require_auth
def get_round_questions(round_id):
    """Fetch all questions for a specific round using the normalized view."""

    # Optional but recommended: Check if the round itself exists first
    round_exists = db.session.get(Round, round_id)
    if not round_exists:
         return jsonify({'error': f'Round with id {round_id} not found'}), 404

    # Verify the user has access to the event this round belongs to
    event_owner_id = db.session.scalar(select(Event.user_id).join(Round).filter(Round.id == round_id))
    if event_owner_id is None: # Should not happen if round exists, but safety check
        return jsonify({'error': 'Round data inconsistent'}), 500
    if event_owner_id != request.user.id:
        return jsonify({'error': 'Permission denied to access this round\'s questions'}), 403

    try:
        # Select the Round and eager load the normalized questions from the view
        stmt = (
            select(Round)
            .where(Round.id == round_id)
            .options(
                selectinload(Round.normalized_questions) # Eager load the view relationship
            )
        )
        round_obj = db.session.scalars(stmt).first()

        # Double check if round_obj was actually found
        if not round_obj:
            # This case should ideally be caught by the initial get, but good safety check
            return jsonify({'error': f'Round with id {round_id} not found after loading relationships'}), 404

        # Construct response with camelCase keys from the normalized view data
        questions_list = [{
            'roundQuestionId': q.round_question_id, # Renamed round_question_id
            'roundId': q.round_id,                 # Renamed round_id
            'questionNumber': q.question_number,   # Renamed question_number
            'questionId': q.question_id,           # Renamed question_id
            'questionType': q.question_type,       # Renamed question_type
            'question': q.question,
            'answer': q.answer,
            'difficulty': q.difficulty,
            'categoryId': q.category_id,           # Renamed category_id
            'categoryName': q.category_name        # Renamed category_name
        } for q in round_obj.normalized_questions] # Iterate over the loaded view relationship

        return jsonify(questions_list)
    except Exception as e:
        # Log the error for debugging
        app.logger.error(f"Database error fetching questions for round {round_id}: {e}")
        return jsonify({'error': 'Failed to retrieve questions due to a database error'}), 500

@app.route('/api/rounds', methods=['POST'])
@require_auth
def create_round():
    """Create a new round for a specific event."""
    data = request.get_json()
    if not data or 'event_id' not in data:
        return jsonify({'error': 'Missing event_id'}), 400

    event_id = data['event_id']

    # Verify the event exists and belongs to the current user
    event = db.session.scalar(
        select(Event).filter_by(id=event_id, user_id=request.user.id)
    )
    if not event:
        # Check if the event exists at all to give a more specific error
        event_exists = db.session.get(Event, event_id)
        if not event_exists:
             return jsonify({'error': f'Event with id {event_id} not found'}), 404
        else:
             return jsonify({'error': 'Permission denied to add rounds to this event'}), 403

    try:
        # Find the highest current round number for this event
        max_round_number = db.session.scalar(
            select(func.max(Round.round_number))
            .filter_by(event_id=event_id)
        )
        new_round_number = (max_round_number or 0) + 1

        # Create the new round
        new_round = Round(
            event_id=event_id,
            round_number=new_round_number,
            name=f"Round {new_round_number}" # Default name
            # category_id will be null by default
        )

        db.session.add(new_round)
        db.session.commit()

        # Construct response with camelCase keys
        return jsonify({
            'id': new_round.id,
            'name': new_round.name,
            'roundNumber': new_round.round_number, # Renamed round_number
            'eventId': new_round.event_id,       # Renamed event_id
            'categoryId': new_round.category_id,  # Add categoryId (will be null initially)
            'createdAt': new_round.created_at.isoformat() if new_round.created_at else None # Add createdAt
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating round for event {event_id}: {e}")
        return jsonify({'error': 'Could not create round'}), 500

@app.route('/api/questions/user-generated', methods=['POST'])
@require_auth
def add_user_generated_question():
    """Add a new user-generated question."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    question = data.get('question')
    answer = data.get('answer')
    category_id = data.get('category_id') # Optional category
    difficulty = data.get('difficulty')
    created_by = data.get('created_by') # Assuming you pass the user ID
    notes = data.get('notes')

    # Basic Validation
    if not all([question, answer, difficulty]):
        return jsonify({'error': 'Missing required fields: question, answer, difficulty'}), 400
    if difficulty not in ['easy', 'medium', 'hard']:
        return jsonify({'error': 'Invalid difficulty. Must be one of: easy, medium, hard'}), 400

    # Optional: Validate category_id exists if provided
    if category_id and not db.session.get(Category, category_id):
         return jsonify({'error': f'Category with id {category_id} not found'}), 400

    # Optional: Validate created_by exists if provided (or get from session)
    # If using auth, you'd likely get this from the token instead of the payload
    if created_by and not db.session.get(User, created_by):
         return jsonify({'error': f'User with id {created_by} not found'}), 400

    new_q = UserGeneratedQuestion(
        question=question,
        answer=answer,
        category_id=category_id,
        difficulty=difficulty,
        created_by=created_by,
        notes=notes
        # status defaults to 'active'
    )

    try:
        db.session.add(new_q)
        db.session.commit()
        return jsonify({'id': new_q.id, 'message': 'Question added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding user question: {e}")
        # Provide a more specific error if possible (e.g., FK violation)
        return jsonify({'error': f'Could not add question: {e}'}), 500

@app.route('/api/events', methods=['POST'])
@require_auth
def create_or_update_event():
    """Create a new event or update an existing one for the authenticated user."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    event_id = data.get('id')
    name = data.get('name')

    # Name is always required for creation, and usually present for updates
    if not event_id and not name:
         return jsonify({'error': 'Event name is required for creation'}), 400
    # If updating, name is optional, but if provided, it must be non-empty
    if event_id and 'name' in data and not name:
         return jsonify({'error': 'Event name cannot be empty if provided'}), 400


    try:
        # Prepare dictionary ONLY with fields present in the request
        event_data = {}
        if 'name' in data:
             event_data['name'] = name
        if 'description' in data:
            event_data['description'] = data.get('description')
        if 'status' in data:
            event_data['status'] = data.get('status')

        # Handle event_date separately due to conversion
        if 'event_date' in data:
            event_date_str = data.get('event_date')
            if event_date_str is None:
                 # Explicitly setting date to null
                 event_data['event_date'] = None
            else:
                try:
                    parsed_date = datetime.fromisoformat(event_date_str)
                    if parsed_date.tzinfo is None:
                        # Assume UTC if no timezone is provided
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    event_data['event_date'] = parsed_date
                except (ValueError, TypeError): # Catch TypeError for None
                    return jsonify({'error': 'Invalid event_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS[+-]HH:MM) or null'}), 400

        # Get or create pattern
        if event_id:
            event = db.session.get(Event, event_id)
            if not event:
                 return jsonify({'error': 'Event not found'}), 404
            # Check permissions only when updating an existing event
            if event.user_id != request.user.id:
                return jsonify({'error': 'Permission denied'}), 403
            # Apply updates from the filtered dictionary
            for key, value in event_data.items():
                setattr(event, key, value)
        else:
            # Create new event
            # Ensure required fields are present
            if 'name' not in event_data:
                 return jsonify({'error': 'Event name is required for creation'}), 400

            # Set creation defaults if not provided
            if 'status' not in event_data:
                 event_data['status'] = 'draft'
            
            # Add user_id explicitly for creation
            event_data['user_id'] = request.user.id

            event = Event(**event_data) # Create using the prepared dict
            db.session.add(event)


        db.session.commit()
        db.session.refresh(event) # Ensure computed fields like created_at are loaded

        # Construct response with camelCase keys
        return jsonify({
            'id': event.id,
            'name': event.name,
            'eventDate': event.event_date.isoformat() if event.event_date else None, # Renamed event_date
            'createdAt': event.created_at.isoformat(), # Renamed created_at
            'status': event.status,
            'description': event.description,
            'userId': event.user_id # Add userId
             # 'updatedAt': event.updated_at.isoformat() if event.updated_at else None # If you add an updated_at field later
        }), 200 if event_id else 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error {'updating' if event_id else 'creating'} event (ID: {event_id}): {e}")
        return jsonify({'error': f'Could not {"update" if event_id else "create"} event'}), 500

@app.route('/api/events/my', methods=['GET'])
@require_auth
def get_my_events():
    """Fetch all non-deleted events created by the authenticated user."""
    try:
        # Build the query with optional filters
        stmt = (
            select(Event)
            .filter_by(user_id=request.user.id)
            .filter_by(is_deleted=False)  # Only return non-deleted events
            .order_by(Event.created_at.desc())  # Most recent first
        )
        
        # Add status filter if provided
        status = request.args.get('status')
        if status:
            stmt = stmt.filter_by(status=status)
            
        events = db.session.scalars(stmt).all()
        
        # Manually create dicts with camelCase keys
        events_data = [{
            'id': event.id,
            'name': event.name,
            'eventDate': event.event_date.isoformat() if event.event_date else None, # Renamed event_date
            'createdAt': event.created_at.isoformat(), # Renamed created_at
            'status': event.status,
            # We might need roundsCount here if ListEvent expects it based on the TS type
            # 'roundsCount': len(event.rounds) # Example if needed - requires loading rounds
        } for event in events]
        return jsonify(events_data) # Return the transformed data
        
    except Exception as e:
        app.logger.error(f"Error fetching user events: {e}")
        return jsonify({'error': 'Failed to retrieve events'}), 500

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@require_auth
def delete_event(event_id):
    """Soft delete an event by setting is_deleted to true."""
    try:
        event = db.session.get(Event, event_id)
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
            
        if event.user_id != request.user.id:
            return jsonify({'error': 'Permission denied'}), 403
            
        event.is_deleted = True
        db.session.commit()
        
        return jsonify({'message': 'Event deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting event {event_id}: {e}")
        return jsonify({'error': 'Failed to delete event'}), 500

# --- Main Execution ---
if __name__ == "__main__":
    # Optional: Create tables if they don't exist (useful for development)
    # In production, you'd typically use migrations (e.g., Flask-Migrate + Alembic)
    with app.app_context():
        print("Creating database tables if they don't exist...")
        db.create_all()
        print("Tables should be ready.")

    app.run(debug=True) # Runs on port 5000 by default