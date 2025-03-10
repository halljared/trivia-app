-- Import multiple season files
DO $$
DECLARE
    season_number INTEGER;
BEGIN
    FOR season_number IN 1..1 LOOP  -- Adjust max number based on your seasons
        EXECUTE format('COPY import_table (round, clue_value, daily_double_value, category, comments, answer, question, air_date, notes)
                       FROM ''../data/seasons/season%s.tsv''
                       DELIMITER E''\t''
                       CSV HEADER', season_number);
    END LOOP;
END $$; 