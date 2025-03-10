import json
import html
import psycopg2
from typing import List, Dict

def clean_string(text: str) -> str:
    """
    Clean a string by unescaping HTML entities and removing backslashes
    """
    return html.unescape(text).replace('\\', '')

def clean_trivia_data(json_file: str) -> List[Dict]:
    """
    Clean and process trivia JSON data
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cleaned_questions = []
    
    for question in data:
        # Decode HTML entities and normalize strings
        cleaned_question = {
            'type': question['type'],
            'difficulty': question['difficulty'],
            'category': clean_string(question['category']),
            'question': clean_string(question['question']),
            'correct_answer': clean_string(question['correct_answer']),
            'incorrect_answers': [clean_string(ans) for ans in question['incorrect_answers']]
        }
        cleaned_questions.append(cleaned_question)
    
    return cleaned_questions

def insert_into_postgres(questions: List[Dict], db_config: Dict):
    """
    Insert processed questions into PostgreSQL
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    for q in questions:
        # Insert category if not exists
        cur.execute("""
            INSERT INTO opentdb_categories (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id;
        """, (q['category'],))
        
        # Get category_id
        cur.execute("SELECT id FROM opentdb_categories WHERE name = %s", (q['category'],))
        category_id = cur.fetchone()[0]
        
        # Insert question
        cur.execute("""
            INSERT INTO opentdb_import (
                type, difficulty, category_id, question_text,
                correct_answer, incorrect_answers
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            q['type'],
            q['difficulty'],
            category_id,
            q['question'],
            q['correct_answer'],
            q['incorrect_answers']
        ))
    
    conn.commit()
    cur.close()
    conn.close()

# Example usage:
if __name__ == "__main__":
    from credentials import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST
    
    db_config = {
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "host": DB_HOST
    }
    
    # Assuming your JSON is in a file called 'trivia.json'
    cleaned_data = clean_trivia_data('../data/db.json')
    insert_into_postgres(cleaned_data, db_config)