import csv
import json
import ast

input_file = "../Raw/credits.csv"
output_file = "../Cleaned/credits_grouped.csv"

movie_data = {}

with open(input_file, "r", newline="", encoding="utf-8") as f_in:
    reader = csv.DictReader(f_in)
    for row in reader:
        movie_id = row["id"]  # the column is called 'id'

        entries = []

        # Safely evaluate the Python-style list/dict
        try:
            cast_list = ast.literal_eval(row["cast"])
        except Exception:
            cast_list = []

        for c in cast_list:
            entries.append({"name": c.get("name", ""), "character": c.get("character", "")})

        try:
            crew_list = ast.literal_eval(row["crew"])
        except Exception:
            crew_list = []

        for c in crew_list:
            entries.append({"name": c.get("name", ""), "job": c.get("job", "")})

        movie_data[movie_id] = entries

# Write grouped JSON arrays to CSV
with open(output_file, "w", newline="", encoding="utf-8") as f_out:
    writer = csv.writer(f_out)
    writer.writerow(["cast_and_crew", "movieId"])
    for movie_id, entries in movie_data.items():
        writer.writerow([json.dumps(entries, ensure_ascii=False), movie_id])

print("Done. Saved as:", output_file)
