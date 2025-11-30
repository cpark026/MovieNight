#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('movies.db')
cursor = conn.cursor()

# Get hp_experiments schema
cursor.execute("PRAGMA table_info(hp_experiments)")
columns = cursor.fetchall()

print("HP_EXPERIMENTS TABLE COLUMNS:")
for col in columns:
    print(f"  {col[1]}: {col[2]}")

conn.close()
