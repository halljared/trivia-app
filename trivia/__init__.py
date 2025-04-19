import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv

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

# Import routes after db initialization to avoid circular imports
from . import main  # This will import all your routes
