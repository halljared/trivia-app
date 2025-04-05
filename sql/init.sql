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

-- Create events table
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    created_by INTEGER REFERENCES users(id),
    event_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, completed, etc.
    description TEXT
);

-- Create rounds table
CREATE TABLE IF NOT EXISTS rounds (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id),
    round_number INTEGER NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, round_number)
);

-- Create user_generated_questions table
CREATE TABLE IF NOT EXISTS user_generated_questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    difficulty VARCHAR(10) NOT NULL,    -- 'easy', 'medium', or 'hard'
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active', -- active, flagged, deleted, etc.
    notes TEXT
);

-- Create round_questions table to link questions to rounds
CREATE TABLE IF NOT EXISTS round_questions (
    id SERIAL PRIMARY KEY,
    round_id INTEGER REFERENCES rounds(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    -- These next two columns are mutually exclusive (only one should have a value)
    preset_question_id INTEGER REFERENCES trivia_questions(id),
    user_question_id INTEGER REFERENCES user_generated_questions(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(round_id, question_number),
    -- Ensure only one question type is referenced
    CONSTRAINT question_type_check CHECK (
        (preset_question_id IS NULL AND user_question_id IS NOT NULL) OR
        (preset_question_id IS NOT NULL AND user_question_id IS NULL)
    )
);

-- Create helpful indexes
CREATE INDEX IF NOT EXISTS idx_trivia_questions_difficulty ON trivia_questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_trivia_questions_category_id ON trivia_questions(category_id);
CREATE INDEX IF NOT EXISTS idx_round_questions_preset_id ON round_questions(preset_question_id);
CREATE INDEX IF NOT EXISTS idx_round_questions_user_id ON round_questions(user_question_id);
CREATE INDEX IF NOT EXISTS idx_rounds_event_id ON rounds(event_id);
CREATE INDEX IF NOT EXISTS idx_user_generated_questions_category ON user_generated_questions(category_id);
