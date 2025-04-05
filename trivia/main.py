import os
import psycopg2
import random
import secrets
import bcrypt
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from flask_cors import CORS

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)
CORS(app)

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

def get_db_connection():
    db_config = {
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "host": DB_HOST
    }
    conn = psycopg2.connect(**db_config)
    return conn

@app.route('/api/question', methods=['GET'])
def get_question():
    """
    Get a random trivia question.
    
    Query Parameters:
        difficulty (optional): Filter by difficulty level ('easy', 'medium', 'hard')
        category_id (optional): Filter by category ID (integer)
    
    Returns:
        JSON object containing:
        - id: Question ID
        - question: The trivia question text
        - answer: The trivia answer text
        - category: Category name
        - difficulty: Question difficulty level
    """
    # Get difficulty parameter (if provided)
    difficulty = request.args.get('difficulty')
    category_id = request.args.get('category_id', type=int)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Build query based on provided parameters
            query = """SELECT q.id, q.question, q.answer, c.name as category, q.difficulty 
                      FROM trivia_questions q 
                      JOIN categories c ON q.category_id = c.id 
                      WHERE 1=1"""
            params = []
            
            if difficulty:
                query += " AND q.difficulty = %s"
                params.append(difficulty)
                
            if category_id:
                query += " AND q.category_id = %s"
                params.append(category_id)
            
            # Get count of matching questions
            count_query = f"SELECT COUNT(*) FROM ({query}) AS subquery"
            cursor.execute(count_query, params)
            total_questions = cursor.fetchone()[0]
            
            if total_questions == 0:
                return jsonify({"error": "No questions found with these criteria"}), 404
            
            # Get random question
            random_index = random.randint(0, total_questions - 1)
            query += " OFFSET %s LIMIT 1"
            params.append(random_index)
            
            cursor.execute(query, params)
            question_id, question, answer, category, difficulty = cursor.fetchone()
            
        return jsonify({
            'id': question_id,
            'question': question,
            'answer': answer,
            'category': category,
            'difficulty': difficulty
        })
    finally:
        conn.close()

@app.route('/api/check-answer', methods=['POST'])
def check_answer():
    """
    Check if the provided answer matches the correct answer for a question.
    
    Request Body (JSON):
        question_id: ID of the question being answered
        answer: User's answer to check
    
    Returns:
        JSON object containing:
        - correct: Boolean indicating if answer is correct
        - score: Fuzzy matching score (0-100)
        - correct_answer: The actual correct answer
    """
    data = request.get_json()
    if not data or 'answer' not in data or 'question_id' not in data:
        return jsonify({'error': 'Missing answer or question_id'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT answer FROM trivia_questions WHERE id = %s", (data['question_id'],))
            result = cursor.fetchone()
            
            if not result:
                return jsonify({'error': 'Question not found'}), 404
                
            correct_answer = result[0]
            
        # Fuzzy matching
        score = fuzz.ratio(data['answer'].lower(), correct_answer.lower())
        is_correct = score >= 80

        return jsonify({
            'correct': is_correct,
            'score': score,
            'correct_answer': correct_answer
        })
    finally:
        conn.close()

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """
    Get all available trivia categories.
    
    Returns:
        JSON array of category objects, each containing:
        - id: Category ID
        - name: Category name
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM categories ORDER BY name")
            categories = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
            
        return jsonify(categories)
    finally:
        conn.close()

@app.route('/api/difficulties', methods=['GET'])
def get_difficulties():
    """
    Get all available difficulty levels.
    
    Returns:
        JSON array of difficulty levels: ['easy', 'medium', 'hard']
    """
    # Return the available difficulty levels
    return jsonify(['easy', 'medium', 'hard'])

@app.route('/api/categories/active', methods=['GET'])
def get_active_categories():
    """
    Get categories that have a minimum number of questions.
    
    Query Parameters:
        min_questions (optional): Minimum number of questions required (default: 80)
    
    Returns:
        JSON array of category objects, each containing:
        - id: Category ID
        - name: Category name
        - question_count: Number of questions in category
    """
    min_questions = request.args.get('min_questions', default=80, type=int)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT c.id, c.name, COUNT(q.id) as question_count
                FROM categories c
                LEFT JOIN trivia_questions q ON c.id = q.category_id
                GROUP BY c.id, c.name
                HAVING COUNT(q.id) >= %s
                ORDER BY c.name
            """
            cursor.execute(query, (min_questions,))
            categories = [
                {
                    "id": row[0],
                    "name": row[1],
                    "question_count": row[2]
                }
                for row in cursor.fetchall()
            ]
            
        return jsonify(categories)
    finally:
        conn.close()

@app.route('/api/category/<int:category_id>/questions', methods=['GET'])
def get_category_questions(category_id):
    """
    Get multiple random questions from a specific category.
    
    Path Parameters:
        category_id: ID of the category to get questions from
    
    Query Parameters:
        count (optional): Number of questions to return (default: 10, max: 50)
    
    Returns:
        JSON array of question objects, each containing:
        - id: Question ID
        - question: The trivia question text
        - answer: The trivia answer text
        - category: Category name
        - difficulty: Question difficulty level
    """
    count = min(request.args.get('count', default=10, type=int), 50)  # Cap at 50 questions
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # First verify the category exists
            cursor.execute("SELECT name FROM categories WHERE id = %s", (category_id,))
            category_result = cursor.fetchone()
            if not category_result:
                return jsonify({"error": "Category not found"}), 404
            
            # Get random questions from this category
            query = """
                SELECT q.id, q.question, q.answer, c.name as category, q.difficulty
                FROM trivia_questions q
                JOIN categories c ON q.category_id = c.id
                WHERE q.category_id = %s
                ORDER BY RANDOM()
                LIMIT %s
            """
            cursor.execute(query, (category_id, count))
            questions = [
                {
                    'id': row[0],
                    'question': row[1],
                    'answer': row[2],
                    'category': row[3],
                    'difficulty': row[4]
                }
                for row in cursor.fetchall()
            ]
            
            if not questions:
                return jsonify({"error": "No questions found in this category"}), 404
                
        return jsonify(questions)
    finally:
        conn.close()

@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Request Body (JSON):
        username: Username for the new account
        email: Email address
        password: Password (will be hashed)
    
    Returns:
        JSON object containing success message and user info
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['username', 'email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if username or email already exists
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", 
                         (data['username'], data['email']))
            if cursor.fetchone():
                return jsonify({'error': 'Username or email already exists'}), 409

            # Hash password
            password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
            
            # Insert new user
            cursor.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, username, email
            """, (data['username'], data['email'], password_hash.decode('utf-8')))
            
            user = cursor.fetchone()
            conn.commit()
            
            return jsonify({
                'message': 'User registered successfully',
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2]
                }
            })
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Login a user and create a session.
    
    Request Body (JSON):
        email: User's email
        password: User's password
    
    Returns:
        JSON object containing session token and user info
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get user by email
            cursor.execute("""
                SELECT id, username, email, password_hash 
                FROM users 
                WHERE email = %s
            """, (data['email'],))
            
            user = cursor.fetchone()
            if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), 
                                           user[3].encode('utf-8')):
                return jsonify({'error': 'Invalid credentials'}), 401

            # Generate session token
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(days=7)

            # Create session
            cursor.execute("""
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (%s, %s, %s)
            """, (user[0], session_token, expires_at))

            # Update last login
            cursor.execute("""
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (user[0],))
            
            conn.commit()

            return jsonify({
                'session_token': session_token,
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2]
                }
            })
    finally:
        conn.close()

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """
    Logout a user by invalidating their session.
    
    Headers:
        Authorization: Bearer <session_token>
    
    Returns:
        JSON object containing success message
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid authorization header'}), 401

    session_token = auth_header.split(' ')[1]
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM user_sessions WHERE session_token = %s", (session_token,))
            conn.commit()
            
            return jsonify({'message': 'Logged out successfully'})
    finally:
        conn.close()

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """
    Get the current user's information.
    
    Headers:
        Authorization: Bearer <session_token>
    
    Returns:
        JSON object containing user information
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid authorization header'}), 401

    session_token = auth_header.split(' ')[1]
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.email, u.created_at, u.last_login
                FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = %s AND s.expires_at > CURRENT_TIMESTAMP
            """, (session_token,))
            
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': 'Invalid or expired session'}), 401

            return jsonify({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'created_at': user[3].isoformat(),
                'last_login': user[4].isoformat() if user[4] else None
            })
    finally:
        conn.close()


@app.route('/api/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """
    Fetch an event and its associated rounds by event ID.
    
    Args:
        event_id (int): The ID of the event to retrieve
    
    Returns:
        JSON: Event details including its rounds
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # SQL query that joins events with rounds and aggregates round data as JSON
            query = """
                SELECT e.id, e.name, e.event_date, e.status, e.description,
                json_agg(json_build_object(
                    'id', r.id,
                    'round_number', r.round_number,
                    'name', r.name,
                    'created_at', r.created_at
                )) AS rounds
                FROM events e
                LEFT JOIN rounds r ON e.id = r.event_id
                WHERE e.id = %s
                GROUP BY e.id
            """
            cursor.execute(query, (event_id,))
            event = cursor.fetchone()

            # Convert database row to dictionary with proper type handling
            event_dict = {
                'id': event[0],
                'name': event[1],
                'event_date': event[2].isoformat() if event[2] else None,
                'status': event[3],
                'description': event[4],
                'rounds': event[5] if event[5] else []
            }

            return jsonify(event_dict)
    finally:
        conn.close()


@app.route('/api/rounds/<int:round_id>/questions', methods=['GET'])
def get_round_questions(round_id):
    """
    Fetch all questions for a specific round.
    
    Args:
        round_id (int): The ID of the round to retrieve questions for
    
    Returns:
        JSON: List of questions in the round with their details
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # SQL query that joins round_questions with both preset and user-generated questions
            query = """
                SELECT 
                    rq.question_number,
                    COALESCE(q.question, uq.question) as question,
                    COALESCE(q.answer, uq.answer) as answer,
                    COALESCE(q.difficulty, uq.difficulty) as difficulty,
                    c.name as category
                FROM round_questions rq
                LEFT JOIN trivia_questions q ON rq.preset_question_id = q.id
                LEFT JOIN user_generated_questions uq ON rq.user_question_id = uq.id
                LEFT JOIN categories c ON COALESCE(q.category_id, uq.category_id) = c.id
                WHERE rq.round_id = %s
                ORDER BY rq.question_number
            """
            cursor.execute(query, (round_id,))
            questions = cursor.fetchall()

            # Convert database rows to a list of dictionaries
            questions_list = [{
                'question_number': q[0],
                'question': q[1],
                'answer': q[2],
                'difficulty': q[3],
                'category': q[4]
            } for q in questions]

            return jsonify(questions_list)
    finally:
        conn.close()


@app.route('/api/questions/user-generated', methods=['POST'])
def add_user_generated_question():
    """
    Add a new user-generated question to the database.
    
    Expected JSON payload:
    {
        "question": "Question text",
        "answer": "Answer text",
        "category_id": 1,
        "difficulty": "easy|medium|hard",
        "created_by": "user_id"
    }
    
    Returns:
        JSON: ID of the new question and success message (201)
        or error message (400/500)
    """
    data = request.get_json()
    question = data.get('question')
    answer = data.get('answer')
    category_id = data.get('category_id')
    difficulty = data.get('difficulty')
    created_by = data.get('created_by')

    # Validate required fields
    if not question or not answer or not category_id or not difficulty:
        return jsonify({'error': 'Missing required fields. Question, answer, category_id, and difficulty are required.'}), 400
    
    # Validate difficulty is one of the allowed values
    if difficulty not in ['easy', 'medium', 'hard']:
        return jsonify({'error': 'Invalid difficulty. Must be one of: easy, medium, hard'}), 400
    
    # If created_by is required but not provided
    if not created_by:
        return jsonify({'error': 'User ID (created_by) is required'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Insert the new question and return its ID
            query = """
                INSERT INTO user_generated_questions (question, answer, category_id, difficulty, created_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """
            cursor.execute(query, (question, answer, category_id, difficulty, created_by))
            new_question_id = cursor.fetchone()[0]
            conn.commit()

            return jsonify({'id': new_question_id, 'message': 'Question added successfully'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)