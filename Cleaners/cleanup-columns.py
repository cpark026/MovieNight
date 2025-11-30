import csv
import ast

input_file = ".movies_combined.csv"
output_file = "../output.csv"

# Columns to remove
drop_columns = [
    "cast_flat",
    "belongs_to_collection",
    "original_language",
    "original_title",
    "release_date",
    "runtime",
    "spoken_languages",
    "status",
    "tagline",
    "video",
    "vote_average",
    "vote_count",
    "min_rating",
    "max_rating",
    "popularity",
    "poster_path",
    "adult"
]

# Words that will filter out movies if found in title or overview
BLOCKED_WORDS = [
    "porno",
    "cuckold"
]

def contains_blocked_word(text):
    if not text:
        return False
    text_lower = text.lower()
    return any(blocked.lower() in text_lower for blocked in BLOCKED_WORDS)

def format_genres(genres_str):
    try:
        genres_list = ast.literal_eval(genres_str)
        return "|".join([g['name'] for g in genres_list])
    except:
        return genres_str

def format_cast(cast_str):
    try:
        cast_list = ast.literal_eval(cast_str)
        formatted = []
        for member in cast_list:
            if "character" in member:
                name = member.get("name", "")
                parts = name.split()
                first = parts[0] if len(parts) > 0 else ""
                last = parts[-1] if len(parts) > 1 else ""
                formatted.append(f"{first}|{last}")
        return ",".join(formatted)
    except:
        return cast_str

def format_companies(companies_str):
    try:
        companies_list = ast.literal_eval(companies_str)
        return "|".join([comp.get("name","") for comp in companies_list])
    except:
        return companies_str


# ============ NEW: Track IDs to prevent duplicates ============
seen_ids = set()


with open(input_file, "r", encoding="utf-8") as infile, \
     open(output_file, "w", newline="", encoding="utf-8") as outfile:

    reader = csv.DictReader(infile)

    # Keep only columns that aren't dropped
    fieldnames = [f for f in reader.fieldnames if f not in drop_columns]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:

        movie_id = row.get("id", "").strip()

        # Skip rows with duplicate IDs
        if movie_id in seen_ids:
            continue
        seen_ids.add(movie_id)

        is_banana = row.get("title", "").strip() == "Banana"

        # Skip Adult=True
        if row.get("adult", "").strip().lower() == "true":
            continue

        title = row.get("title", "").strip()
        overview = row.get("overview", "").strip()

        if contains_blocked_word(title) or contains_blocked_word(overview):
            continue

        # Skip rows with ANY empty fields BEFORE formatting (except rating fields)
        rating_fields = {"avg_rating", "rating_count"}
        empty_fields = [
            f for f in fieldnames
            if row.get(f, "").strip() == "" and f not in rating_fields
        ]
        if empty_fields:
            continue

        # Formatting
        if "genres" in row:
            row["genres"] = format_genres(row["genres"])

        if "cast_and_crew" in row:
            row["cast_and_crew"] = format_cast(row["cast_and_crew"])

        if "production_companies" in row:
            row["production_companies"] = format_companies(row["production_companies"])

        # Skip after formatting if required fields are empty
        if row.get("production_companies", "").strip() == "" or \
           row.get("cast_and_crew", "").strip() == "":
            continue

        # Remove dropped columns
        for col in drop_columns:
            row.pop(col, None)

        writer.writerow(row)

print(f"Reformatted CSV saved as {output_file}")
print(f"Unique IDs kept: {len(seen_ids)}")
