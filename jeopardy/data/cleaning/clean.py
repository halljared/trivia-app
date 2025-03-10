import pandas as pd
import unicodedata

# Load the TSV file
input_file = '../seasons/season1.tsv'
output_file = './cleaned.tsv'
# Read the TSV file
try:
    df = pd.read_csv(input_file, sep='\t', encoding='latin-1', on_bad_lines='skip')
    # Alternative approach if latin-1 doesn't work:
    # df = pd.read_csv(input_file, sep='\t', encoding='utf-8', encoding_errors='replace', on_bad_lines='skip')
except Exception as e:
    print(f"Error reading the file: {e}")

# More thorough cleaning of problematic characters
def clean_text(text):
    if not isinstance(text, str):
        return text
    # Remove control characters and non-printable characters
    text = ''.join(char for char in text if ord(char) >= 32)
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    # Remove any remaining non-ASCII characters
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text

# Apply the cleaning function to all string columns
df = df.applymap(clean_text)

# Write the cleaned DataFrame back to a new TSV file
df.to_csv(output_file, sep='\t', index=False, encoding='utf-8')

print(f"Cleaned data written to {output_file}")