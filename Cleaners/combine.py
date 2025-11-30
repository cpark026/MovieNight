import pandas as pd

def merge_datasets():
    """Merge movies, credits, and ratings data by movieId."""
    
    # Read the CSV files
    movies_df = pd.read_csv("../Cleaned/movies_no_extra.csv", low_memory=False)
    credits_df = pd.read_csv("../Cleaned/credits_grouped.csv", low_memory=False)
    ratings_df = pd.read_csv("../Cleaned/ratings_cleaned.csv", low_memory=False)
    
    # Convert id columns to same type (int64)
    movies_df["id"] = pd.to_numeric(movies_df["id"], errors="coerce")
    credits_df["movieId"] = pd.to_numeric(credits_df["movieId"], errors="coerce")
    ratings_df["movieId"] = pd.to_numeric(ratings_df["movieId"], errors="coerce")
    
    # Merge movies with credits on id/movieId
    merged_df = movies_df.merge(
        credits_df,
        left_on="id",
        right_on="movieId",
        how="left"
    )
    
    # Drop the duplicate movieId column from credits
    merged_df = merged_df.drop(columns=["movieId"])
    
    # Merge with ratings (aggregate ratings by movieId)
    ratings_agg = ratings_df.groupby("movieId").agg({
        "rating": ["mean", "count", "min", "max"]
    }).reset_index()
    
    # Flatten column names for aggregated ratings
    ratings_agg.columns = ["movieId", "avg_rating", "rating_count", "min_rating", "max_rating"]
    
    # Merge final dataset
    final_df = merged_df.merge(
        ratings_agg,
        left_on="id",
        right_on="movieId",
        how="left"
    )
    
    # Drop duplicate movieId column from ratings merge
    final_df = final_df.drop(columns=["movieId"], errors="ignore")
    
    # Save to output
    final_df.to_csv("../Cleaned/movies_combined.csv", index=False)
    print(f"Combined dataset saved to Cleaned/movies_combined.csv")
    print(f"Total rows: {len(final_df)}")
    print(f"\nColumns: {list(final_df.columns)}")

if __name__ == "__main__":
    merge_datasets()