import csv

input_file = "../Raw/ratings.csv"
output_file = "../Cleaned/ratings_cleaned.csv"

with open(input_file, "r", newline="", encoding="utf-8") as f_in:
    reader = csv.reader(f_in)
    header = next(reader)        # read header

    # Find the index of the timestamp column
    if "timestamp" in header:
        timestamp_idx = header.index("timestamp")
        # Remove timestamp from header
        header.pop(timestamp_idx)
    else:
        timestamp_idx = None

    # Load rows, dropping timestamp column
    rows = []
    for r in reader:
        if timestamp_idx is not None:
            r.pop(timestamp_idx)
        rows.append(r)

# Optional: sort by movieId (column index 1)
rows.sort(key=lambda r: int(r[1]))

# Write output
with open(output_file, "w", newline="", encoding="utf-8") as f_out:
    writer = csv.writer(f_out)
    writer.writerow(header)
    writer.writerows(rows)

print("Done. Cleaned file saved as:", output_file)
