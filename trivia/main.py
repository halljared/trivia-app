import os
import psycopg2
import random
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
from flask import Flask, jsonify, request
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
            query = "SELECT q.id, q.question, c.name as category, q.difficulty FROM trivia_questions q JOIN categories c ON q.category_id = c.id WHERE 1=1"
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
            question_id, question, category, difficulty = cursor.fetchone()
            
        return jsonify({
            'id': question_id,
            'question': question,
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
                SELECT q.id, q.question, c.name as category, q.difficulty
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
                    'category': row[2],
                    'difficulty': row[3]
                }
                for row in cursor.fetchall()
            ]
            
            if not questions:
                return jsonify({"error": "No questions found in this category"}), 404
                
        return jsonify(questions)
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)