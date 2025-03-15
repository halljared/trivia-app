-- Step 1: Create new normalized tables
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(256) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS trivia_questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,             -- This was "answer" in the Jeopardy format
    answer TEXT NOT NULL,               -- This was "question" in the Jeopardy format
    category_id INTEGER NOT NULL,
    difficulty VARCHAR(10) NOT NULL,    -- 'easy', 'medium', or 'hard'
    air_date DATE,
    original_value SMALLINT,            -- Original clue value for reference
    original_round SMALLINT,            -- Original round for reference
    notes TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Step 2: Populate categories table with unique values
INSERT INTO categories (name)
SELECT DISTINCT category
FROM import_table
ON CONFLICT (name) DO NOTHING;

-- Step 3: Populate trivia_questions with converted data
INSERT INTO trivia_questions (
    question, answer, category_id, difficulty, 
    air_date, original_value, original_round, notes
)
SELECT 
    it.answer AS question,              -- Swap answer to question (Jeopardy format conversion)
    it.question AS answer,              -- Swap question to answer
    c.id AS category_id,
    CASE
        -- Handle difficulty based on air_date, round, and clue_value
        WHEN (
            -- Older episodes format (pre-November 2001)
            TO_DATE(it.air_date, 'YYYY-MM-DD') < '2001-11-26'::DATE 
            OR
            -- Some special older format indicator if needed
            (it.round = 1 AND it.clue_value IN (100, 200, 300, 400, 500))
            OR 
            (it.round = 2 AND it.clue_value IN (200, 400, 600, 800, 1000))
        ) THEN
            -- For older episodes, use position-based approach
            CASE
                WHEN (
                    (it.round = 1 AND it.clue_value IN (100, 200)) OR
                    (it.round = 2 AND it.clue_value IN (200, 400))
                ) THEN 'easy'
                WHEN (
                    (it.round = 1 AND it.clue_value IN (300, 400)) OR
                    (it.round = 2 AND it.clue_value IN (600, 800))
                ) THEN 'medium'
                ELSE 'hard'
            END
        ELSE
            -- For newer episodes (post-November 2001)
            CASE
                WHEN (
                    (it.round = 1 AND it.clue_value IN (200, 400)) OR
                    (it.round = 2 AND it.clue_value IN (400, 800))
                ) THEN 'easy'
                WHEN (
                    (it.round = 1 AND it.clue_value IN (600, 800)) OR
                    (it.round = 2 AND it.clue_value IN (1200, 1600))
                ) THEN 'medium'
                ELSE 'hard'
            END
    END AS difficulty,
    CASE 
        WHEN it.air_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' 
        THEN TO_DATE(it.air_date, 'YYYY-MM-DD')
        ELSE NULL
    END AS air_date,
    it.clue_value AS original_value,
    it.round AS original_round,
    CONCAT(it.comments, ' ', it.notes) AS notes
FROM import_table it
JOIN categories c ON it.category = c.name
WHERE it.question IS NOT NULL AND it.answer IS NOT NULL;

-- Create indexes for better performance
CREATE INDEX idx_trivia_questions_difficulty ON trivia_questions(difficulty);
CREATE INDEX idx_trivia_questions_category_id ON trivia_questions(category_id);
