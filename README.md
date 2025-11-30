# MovieNight - Movie Recommendation Engine

A sophisticated movie recommendation system built with Flask and PySpark that provides personalized movie suggestions based on genre preferences, cast members, and franchise history.

## Features

- **User Authentication**: Secure login and registration system
- **Multi-Dimensional Recommendations**: 
  - Personalized recommendations based on user history
  - Last-added movie-based recommendations
  - Genre-focused recommendations
- **Smart Similarity Metrics**:
  - Genre similarity (Jaccard coefficient)
  - Cast member overlap detection
  - Franchise recognition
  - Average rating normalization
- **Distributed Computing**: Powered by Apache Spark for efficient processing
- **Per-User Data Isolation**: Each user's watchlist is privately managed

## Tech Stack

- **Backend**: Flask (Python)
- **Data Processing**: Apache Spark (PySpark)
- **Database**: SQLite
- **Frontend**: HTML/CSS/JavaScript
- **Authentication**: SHA-256 password hashing with session management

## Project Structure

```
.
├── app.py                 # Flask application and API endpoints
├── model2.py             # PySpark recommendation engine
├── model.py              # Alternative model implementation
├── output.csv            # Processed movie dataset
├── movies.db             # SQLite database (user/watchlist data)
├── .env                  # Environment variables (API keys)
├── Templates/
│   ├── index.html        # Main recommendations page
│   ├── results.html      # Search results page
│   └── login.html        # Authentication page
├── static/
│   ├── css/              # Stylesheets
│   │   ├── home.css
│   │   ├── index.css
│   │   ├── login.css
│   │   ├── main.css
│   │   └── results.css
│   ├── js/               # Client-side logic
│   │   ├── index.js
│   │   └── results.js
│   └── images/           # Media assets
├── Cleaned/              # Pre-processed movie data
├── Cleaners/             # Data cleaning utilities
└── Raw/                  # Raw movie datasets
```

## Installation

### Prerequisites
- Python 3.8+
- Java 8+ (for Spark)
- Git

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/MovieNight.git
cd MovieNight
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your TMDb API key
```

5. Run the Flask application:
```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## API Endpoints

### Authentication
- `POST /api/login` - User login
- `POST /api/register` - User registration
- `GET /api/check-auth` - Check authentication status
- `POST /api/logout` - User logout

### Recommendations
- `GET /getRecommendations` - Get personalized recommendations
- `GET /getLastWatchedRecommendations` - Recommendations based on last movie
- `GET /getMostCommonGenreRecommendations` - Genre-focused recommendations
- `GET /getMostCommonGenre` - Get user's most watched genre

### Watchlist Management
- `POST /addShow` - Add movie to watchlist
- `GET /getWatchlistIDs` - Get all user's movies
- `GET /getLastAddedMovie` - Get most recently added movie
- `GET /getResults` - Search movies from TMDb

## Performance Metrics

- **First request (with Spark warmup)**: ~20 seconds
- **Subsequent requests (warm cache)**: ~7 seconds
- **Concurrent users**: Scales with Spark partitions

### Recommendation Scoring

Hybrid scoring combines four factors:
- **Genre Similarity**: 45% weight - Jaccard coefficient of genre sets
- **Cast Overlap**: 15% weight - Proportion of shared actors
- **Franchise Match**: 5% weight - Boolean franchise detection
- **User Rating Norm**: 35% weight - Average rating normalization

## Development

### Data Pipeline

1. **Raw Data**: Movies and ratings from TMDb API
2. **Cleaning**: Genre/cast parsing and normalization (`Cleaners/`)
3. **Processing**: Spark DataFrame creation with array pre-processing
4. **Caching**: Distributed cache for fast lookups

### Adding New Recommendation Types

Extend `model2.py` with new functions following the pattern:
```python
def get_recommendations_by_X(user_id, top_n=10):
    # Load user profile from database
    # Calculate similarity scores in Spark
    # Return sorted results
```

## License

MIT License - See LICENSE file for details

## Contributors

- Christian (Development)
- Lauren (Development)

## Support

For issues or suggestions, please open an issue on GitHub.
