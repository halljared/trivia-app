import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def init_db(app):
    # --- Load Environment Variables ---
    env_file = os.getenv('ENV_FILE', '.env.local')
    load_dotenv(os.path.join(os.path.dirname(__file__), env_file))

    # Database Configuration using environment variables
    DB_NAME = os.getenv('POSTGRES_DB')
    DB_USER = os.getenv('POSTGRES_USER')
    DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    DB_HOST = os.getenv('POSTGRES_DB_HOST')
    DB_PORT = os.getenv('POSTGRES_DB_PORT', '5432')  # Default PostgreSQL port

    # Configure SQLAlchemy - Use 'postgresql+psycopg2' driver
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking overhead

    # Initialize the app with the database
    db.init_app(app) 