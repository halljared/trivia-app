#!/bin/bash

# Load credentials
source credentials.sh
export PGPASSWORD=$DB_PASSWORD

for season_number in {1..40}; do  # Adjust max number based on your seasons
    echo "Importing data from season${season_number}.tsv..."
    echo "  Processing season${season_number}.tsv..."
    input_file="../data/seasons/season${season_number}.tsv"
    fixed_file="./fixed.tsv"

    # The Ultimate Text Cleaner™ (TSV-friendly version)
    perl -CSD -pe '
        # Convert to UTF-8 and remove invalid UTF-8
        use utf8;
        # Remove control characters EXCEPT tabs and newlines
        s/[[:cntrl:]&&[^\t\n]]//g;
        # Normalize quotes and remove backslashes before quotes
        s/\\"/"/g;  # Remove backslash before quotes first
        s/[""″‟„]|&quot;/"/g;
        s/[''′‵`]|&apos;/'"'"'/g;
        # Remove zero-width and invisible characters
        s/[\x{200B}-\x{200F}\x{FEFF}]//g;
        # Remove emojis
        s/[\x{1F000}-\x{1F9FF}]//g;
        # Remove non-ASCII but keep punctuation
        s/[^\x00-\x7F!"#$%&'"'"'()*+,\-.\/0-9:;<=>?@A-Z\[\\\]^_`a-z{|}~\t\n]//g;
        # For each field in the TSV
        my @fields = split(/\t/);
        foreach (@fields) {
            # Remove any remaining backslashed quotes
            s/\\"/"/g;
            # Double any quotes in the content
            s/"/""/g;
            # Wrap field in quotes if it contains special characters
            if (/[",\n\r\t]/) {
                $_ = qq{"$_"};
            }
        }
        # Rejoin with tabs
        $_ = join("\t", @fields) . "\n";
    ' "$input_file" > "$fixed_file"

    # Check if preprocessing was successful
    if [ $? -ne 0 ]; then
        echo "Error preprocessing season${season_number}.tsv"
        continue
    fi
    
    # Run the \copy command for each season file
    psql -U $DB_USER -d $DB_NAME -c "\copy import_table (round, clue_value, daily_double_value, \
    category, comments, answer, question, air_date, notes) FROM '$fixed_file' \
    DELIMITER E'\t' CSV HEADER;"
    
    if [ $? -ne 0 ]; then
        echo "Error importing season${season_number}.tsv"
    else
        echo "Successfully imported season${season_number}.tsv"
    fi
done

echo "Database setup and data import completed."