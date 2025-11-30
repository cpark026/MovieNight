import pandas as pd
import re
import unicodedata

def clean_unicode_and_spacing(text):
    """Remove ambiguous unicode chars and non-windows spacing."""
    if not isinstance(text, str):
        return text
    
    # Normalize to NFD (decomposed form) to separate base chars from accents
    text = unicodedata.normalize('NFD', text)
    
    # Remove combining marks (accents, diacritics)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Replace non-breaking spaces, em-spaces, en-spaces with regular spaces
    text = re.sub(r'[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]', ' ', text)
    
    # Remove other problematic unicode characters
    text = ''.join(char if ord(char) < 128 or char in ' \n\t' else '' for char in text)
    
    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text).strip()
    
    return text

def clean_csv(input_file, output_file):
    """Clean CSV by removing specified columns and fixing unicode/spacing."""
    
    columns_to_remove = ["imdb_id", "revenue", "production_countries", "homepage", "budget"]
    
    # Read CSV
    df = pd.read_csv(input_file, low_memory=False)
    
    # Drop specified columns (if they exist)
    df = df.drop(columns=[col for col in columns_to_remove if col in df.columns])
    
    # Apply cleaning to all string columns
    for col in df.columns:
        if df[col].dtype == 'object':  # String columns
            df[col] = df[col].apply(clean_unicode_and_spacing)
    
    # Save cleaned CSV
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Cleaned CSV saved to {output_file}")

# Usage
if __name__ == "__main__":
    input_file = "../Raw/movies_metadata.csv"
    output_file = "../Cleaned/movies_no_extra.csv"
    clean_csv(input_file, output_file)