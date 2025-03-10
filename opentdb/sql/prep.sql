CREATE TABLE opentdb_categories (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE opentdb_import (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    difficulty VARCHAR(50) NOT NULL,
    category_id INTEGER REFERENCES opentdb_categories(id),
    question_text TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    incorrect_answers TEXT[] NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);