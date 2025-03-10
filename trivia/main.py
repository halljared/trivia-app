import os
import psycopg2
import random
from fuzzywuzzy import fuzz
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

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
    # Replace with your actual connection details
    conn = psycopg2.connect(**db_config)
    return conn

def fetch_question(conn):
    with conn.cursor() as cursor:
        # Get the total number of questions
        cursor.execute("SELECT COUNT(*) FROM import_table;")
        total_questions = cursor.fetchone()[0]

        # Pick a random question
        random_index = random.randint(0, total_questions - 1)
        cursor.execute(f"SELECT question, answer, category FROM import_table OFFSET {random_index} LIMIT 1;")
        # remember it's jeopardy wording so the answer is the question
        answer, question, category = cursor.fetchone()
        
    return question, answer, category

def main():
    conn = get_db_connection()
    def print_correct_answer(correct_answer):
        print(f"\nThe correct answer was: {correct_answer}\n")

    try:
      while True:
          question, correct_answer, category = fetch_question(conn)
          print(f"Category: {category}")
          print(f"Question: {question}")

          for attempt in range(2):
              user_input = input("Your answer (or type '?' if you don't know): ").strip()
              
              if user_input == '?':
                  print_correct_answer(correct_answer)
                  break
              
              # Fuzzy matching
              score = fuzz.ratio(user_input.lower(), correct_answer.lower())
              if score >= 80:  # You can adjust the threshold as needed
                  print("Correct! Well done.")
                  break
              else:
                  print("Incorrect. Try again.")
                  if attempt == 1:
                      print_correct_answer(correct_answer)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
1