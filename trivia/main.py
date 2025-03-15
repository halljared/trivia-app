import os
import psycopg2
import random
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)

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
    # Return the available difficulty levels
    return jsonify(['easy', 'medium', 'hard'])

if __name__ == "__main__":
    app.run(debug=True)