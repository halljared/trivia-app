import json
import psycopg2
from typing import Dict
import os
from dotenv import load_dotenv

def create_category(cursor, category_name: str) -> int:
    """Look up a category by name or create it if it doesn't exist, and return its ID"""
    # First try to find existing category
    cursor.execute(
        "SELECT id FROM categories WHERE name = %s",
        (category_name,)
    )
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # If not found, create new category
    cursor.execute(
        "INSERT INTO categories (name) VALUES (%s) RETURNING id",
        (category_name,)
    )
    return cursor.fetchone()[0]

def get_or_create_category(cursor, category_name: str, category_dict: Dict[str, int]) -> int:
    """Get category ID from dictionary or create new category if it doesn't exist"""
    if category_name not in category_dict:
        category_dict[category_name] = create_category(cursor, category_name)
    return category_dict[category_name]

def process_mappings(cursor, json_file: str):
    # Dictionary to store category name -> new ID mapping
    category_dict = {}
    
    # Process JSONL file
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.loads(f.read())  # Parse each JSON object per line
        mappings = data["mappings"]

    for mapping in mappings:
        old_id = mapping["id"]
        new_category_name = mapping["category"]

        if old_id is not None and new_category_name is not None:
            # Get or create the new category ID
            new_category_id = get_or_create_category(cursor, new_category_name, category_dict)
            
            # Update all trivia questions with this old_category_id
            cursor.execute("""
                UPDATE trivia_questions 
                SET category_id = %s 
                WHERE old_category_id = %s
            """, (new_category_id, old_id))

def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost')
    )
    
    try:
        with conn:
            with conn.cursor() as cur:
                # process_mappings(cur, 'extras.json')
                process_mappings(cur, 'stragglers.csv')

                # Print summary of new categories
                cur.execute("SELECT id, name FROM categories ORDER BY id")
                print("\nNew Categories:")
                for id, name in cur.fetchall():
                    print(f"ID: {id}, Name: {name}")
                
                # Print count of unmapped questions
                cur.execute("SELECT COUNT(*) FROM trivia_questions WHERE category_id IS NULL")
                null_count = cur.fetchone()[0]
                print(f"\nQuestions still unmapped: {null_count}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()