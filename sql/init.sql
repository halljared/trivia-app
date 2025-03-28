-- Initialize the trivia database schema

-- Create users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Create user_sessions table for managing active sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create index for faster session lookups
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);

-- Create categories table for organizing questions
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(256) UNIQUE NOT NULL
);

-- Create main trivia_questions table
CREATE TABLE IF NOT EXISTS trivia_questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    difficulty VARCHAR(10) NOT NULL,    -- 'easy', 'medium', or 'hard'
    air_date DATE,
    original_value SMALLINT,            -- Original clue value for reference
    original_round SMALLINT,            -- Original round for reference
    notes TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_trivia_questions_difficulty ON trivia_questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_trivia_questions_category_id ON trivia_questions(category_id);
