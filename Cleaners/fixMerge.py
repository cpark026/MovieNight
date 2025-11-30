import pandas as pd

# Read each file
movies_df = pd.read_csv("Cleaned/movies_no_extra.csv", low_memory=False)
credits_df = pd.read_csv("Cleaned/credits_grouped.csv", low_memory=False)
ratings_df = pd.read_csv("Cleaned/ratings_cleaned.csv", low_memory=False)

# Convert types
movies_df["id"] = pd.to_numeric(movies_df["id"], errors="coerce")
credits_df["movieId"] = pd.to_numeric(credits_df["movieId"], errors="coerce")
ratings_df["movieId"] = pd.to_numeric(ratings_df["movieId"], errors="coerce")

print("Movies columns:", movies_df.columns.tolist())
print("Credits columns:", credits_df.columns.tolist())
print("Ratings columns:", ratings_df.columns.tolist())

# Merge step by step
print("\n1. Merging movies with credits...")
merged = movies_df.merge(credits_df, left_on="id", right_on="movieId", how="left")
print("Merged shape:", merged.shape)
print("Merged columns:", merged.columns.tolist())

# Aggregate ratings
print("\n2. Aggregating ratings...")
ratings_agg = ratings_df.groupby("movieId").agg({
    "rating": ["mean", "count", "min", "max"]
}).reset_index()
ratings_agg.columns = ["movieId", "avg_rating", "rating_count", "min_rating", "max_rating"]

# Final merge
print("\n3. Merging with ratings...")
final = merged.merge(ratings_agg, left_on="id", right_on="movieId", how="left")

# Remove duplicate movieId columns
if "movieId_x" in final.columns:
    final = final.drop(columns=["movieId_x"])
if "movieId_y" in final.columns:
    final = final.drop(columns=["movieId_y"])
if "movieId" in final.columns and "movieId_x" not in final.columns:
    final = final.drop(columns=["movieId"])

print("\nFinal shape:", final.shape)
print("Final columns:", final.columns.tolist())

# Save
final.to_csv("Cleaned/movies_combined.csv", index=False)
print("\n✓ Saved to Cleaned/movies_combined.csv")

# Show sample
print("\nSample data:")
print(final[["id", "title", "vote_average", "avg_rating"]].head())