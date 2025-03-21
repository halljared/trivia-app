import csv
import psycopg2
from psycopg2.extras import execute_values
import re
from dotenv import load_dotenv
import os

# Add this at the module level, before the functions
_category_cache = {}

def clean_text(text):
    # Remove quotes if they wrap the entire text
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    
    # Convert double quotes to single quotes for PostgreSQL
    text = text.replace('""', "'")
    return text

def get_or_create_category(cursor, category_name):
    # Check cache first (case insensitive)
    cache_key = category_name.lower()
    if cache_key in _category_cache:
        return _category_cache[cache_key]
    
    # Look up category (case insensitive)
    cursor.execute(
        "SELECT id FROM categories WHERE LOWER(name) = LOWER(%s)",
        (category_name,)
    )
    result = cursor.fetchone()
    
    if result:
        # Cache the result before returning
        _category_cache[cache_key] = result[0]
        return result[0]
    
    # Create new category if it doesn't exist
    cursor.execute(
        "INSERT INTO categories (name) VALUES (%s) RETURNING id",
        (category_name,)
    )
    category_id = cursor.fetchone()[0]
    
    # Cache the new category
    _category_cache[cache_key] = category_id
    return category_id

def import_anki_data(tsv_file, db_params):
    # Database connection
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    
    questions_to_insert = []
    
    with open(tsv_file, 'r', encoding='utf-8') as f:
        # Skip metadata lines that start with #
        for line in f:
            if not line.startswith('#'):
                break
        
        # Create CSV reader with tab delimiter
        reader = csv.reader(f, delimiter='\t')
        
        for row in reader:
            if len(row) < 7:  # Ensure we have all needed columns
                continue
                
            _, _, _, question, answer, category, _ = row
            
            # Clean the text fields
            question = clean_text(question)
            answer = clean_text(answer)
            
            # Get or create category
            category_id = get_or_create_category(cursor, category)
            
            # Prepare question data
            # Using 'medium' as default difficulty since Anki format doesn't specify difficulty
            question_data = (
                question,
                answer,
                category_id,
                'medium',  # default difficulty
                None,      # air_date
                None,      # original_value
                None,      # original_round
                None      # notes
            )
            
            questions_to_insert.append(question_data)
    
    # Bulk insert questions
    execute_values(
        cursor,
        """
        INSERT INTO trivia_questions 
        (question, answer, category_id, difficulty, air_date, original_value, original_round, notes)
        VALUES %s
        """,
        questions_to_insert
    )
    
    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    db_params = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"), 
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT")
    }
    
    import_anki_data("./data/misc.txt", db_params)
