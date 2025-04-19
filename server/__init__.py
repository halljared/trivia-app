from flask import Flask
from flask_cors import CORS
from .database import init_db, db

# Create the Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize the database
init_db(app)

# Import and initialize routes
from .routes import init_routes
init_routes(app)

