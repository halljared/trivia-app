#!/bin/bash

# Check if the input file is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

# Assign input file variable
FILE="$1"

# Step 1: Trim the header rows and store in a temporary file
TEMP_FILE=$(mktemp)
tail -n +7 "$FILE" > "$TEMP_FILE"

# Step 2: Split into basic and cloze types, using temporary files
awk -F'\t' 'BEGIN {IGNORECASE=1} {
    if ($2 ~ /basic/) {
        print > "/tmp/basic_type.txt"
    } else if ($2 ~ /cloze/) {
        print > "/tmp/cloze_type.txt"
    }
}' "$TEMP_FILE"

# Step 3: Prune rows with > 1 cloze and store in another temporary file
FILTERED_FILE=$(mktemp)
awk -F'{{|}}' 'NF > 2 && (NF-1) % 2 == 0 && (NF-1) / 2 == 1' /tmp/cloze_type.txt > "$FILTERED_FILE"

# Step 4: Only keep 3rd and 4th columns and save to final output file
awk -F'\t' '{print $3 "\t" $4}' "$FILTERED_FILE" > columns_3_and_4.txt

# Clean up temporary files
rm "$TEMP_FILE" /tmp/basic_type.txt /tmp/cloze_type.txt "$FILTERED_FILE"

echo "Processing complete. Output saved to columns_3_and_4.txt"
