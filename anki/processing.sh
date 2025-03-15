# trim the header rows
tail -n +7 $FILE > $OUT_FILE

# split into basic and cloze
awk -F'\t' 'BEGIN {IGNORECASE=1} {
    if ($2 ~ /basic/) {
        print > "basic_type.txt"
    } else if ($2 ~ /cloze/) {
        print > "cloze_type.txt"
    }
}' "$OUT_FILE"

# prune rows with > 1 cloze
awk -F'{{|}}' '((NF-2)/2) == 1' cloze_type.txt > filtered_output.txt

# only keep 3rd and 4th column
FILE=filtered_output.txt
awk -F'\t' '{print $3 "\t" $4}' "$FILE" > columns_3_and_4.txt

