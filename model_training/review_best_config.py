#!/usr/bin/env python3
"""Review and display best hyperparameter configuration"""

import sqlite3
import json

conn = sqlite3.connect('movies.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get best configuration
cursor.execute('''
    SELECT * FROM hp_experiments
    WHERE status = 'completed'
    ORDER BY improvement_from_baseline DESC, test_accuracy DESC
    LIMIT 1
''')

best = cursor.fetchone()

if best:
    print('='*80)
    print('BEST CONFIGURATION FOUND')
    print('='*80)
    print()
    print(f'Experiment ID: {best["experiment_id"]}')
    print(f'Test Accuracy: {best["test_accuracy"]:.2%}')
    print(f'Improvement: {best["improvement_from_baseline"]:+.2%}')
    print()
    print('Hyperparameters:')
    print(f'  Genre Weight: {best["genre_weight"]:.4f}')
    print(f'  Cast Weight: {best["cast_weight"]:.4f}')
    print(f'  Franchise Weight: {best["franchise_weight"]:.4f}')
    print(f'  Rating Weight: {best["rating_weight"]:.4f}')
    print(f'  Popularity Weight: {best["popularity_weight"]:.4f}')
    print()
    print('Additional Parameters:')
    if best["genre_boost_high"] is not None:
        print(f'  Genre Boost (High): {best["genre_boost_high"]:+.4f}')
    if best["genre_boost_medium"] is not None:
        print(f'  Genre Boost (Med): {best["genre_boost_medium"]:+.4f}')
    if best["genre_boost_low"] is not None:
        print(f'  Genre Boost (Low): {best["genre_boost_low"]:+.4f}')
    if best["cast_lead_weight"] is not None:
        print(f'  Cast Lead Weight: {best["cast_lead_weight"]:.4f}')
    if best["cast_supporting_weight"] is not None:
        print(f'  Cast Supporting Weight: {best["cast_supporting_weight"]:.4f}')
    if best["cast_background_weight"] is not None:
        print(f'  Cast Background Weight: {best["cast_background_weight"]:.4f}')
    if best["popularity_rating_weight"] is not None:
        print(f'  Popularity (Rating): {best["popularity_rating_weight"]:.4f}')
    if best["popularity_count_weight"] is not None:
        print(f'  Popularity (Count): {best["popularity_count_weight"]:.4f}')
    print()
    
    # Create JSON for applying
    config_json = json.dumps({
        'genre_weight': best['genre_weight'],
        'cast_weight': best['cast_weight'],
        'franchise_weight': best['franchise_weight'],
        'rating_weight': best['rating_weight'],
        'popularity_weight': best['popularity_weight'],
        'genre_boost_high': best['genre_boost_high'],
        'genre_boost_medium': best['genre_boost_medium'],
        'genre_boost_low': best['genre_boost_low'],
        'genre_threshold_high': best['genre_threshold_high'],
        'genre_threshold_medium': best['genre_threshold_medium'],
        'genre_threshold_low': best['genre_threshold_low'],
        'cast_lead_weight': best['cast_lead_weight'],
        'cast_supporting_weight': best['cast_supporting_weight'],
        'cast_background_weight': best['cast_background_weight'],
        'cast_lead_threshold': best['cast_lead_threshold'],
        'cast_supporting_threshold': best['cast_supporting_threshold'],
        'popularity_rating_weight': best['popularity_rating_weight'],
        'popularity_count_weight': best['popularity_count_weight'],
        'accuracy_threshold': best['accuracy_threshold']
    })
    
    print('JSON for applying:')
    print(config_json)
    print()
    print('='*80)
else:
    print('No experiments found in database')

conn.close()
