-- First, drop the existing index that references the category_id column
DROP INDEX IF EXISTS idx_trivia_questions_category_id;

-- Drop the foreign key constraint
ALTER TABLE trivia_questions
DROP CONSTRAINT trivia_questions_category_id_fkey;

-- Rename the categories table
ALTER TABLE categories 
RENAME TO old_categories;

-- Rename the category_id column in trivia_questions
ALTER TABLE trivia_questions 
RENAME COLUMN category_id TO old_category_id;

-- Recreate the foreign key constraint with the new names
ALTER TABLE trivia_questions
ADD CONSTRAINT trivia_questions_old_category_id_fkey
FOREIGN KEY (old_category_id) REFERENCES old_categories(id);

-- Recreate the index with the new column name
CREATE INDEX idx_trivia_questions_old_category_id ON trivia_questions(old_category_id);

-- Create the new categories table
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(256) UNIQUE NOT NULL
);

-- Add new category_id column to trivia_questions (nullable initially)
ALTER TABLE trivia_questions
ADD COLUMN category_id INTEGER;

-- Add foreign key constraint for the new column
ALTER TABLE trivia_questions
ADD CONSTRAINT trivia_questions_category_id_fkey
FOREIGN KEY (category_id) REFERENCES categories(id);

-- Create index for the new category_id column
CREATE INDEX idx_trivia_questions_category_id ON trivia_questions(category_id); 