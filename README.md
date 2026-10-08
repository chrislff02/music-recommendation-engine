# MusicMatch

MusicMatch is a full-stack music recommendation application that learns a user's taste from ratings, favorite genres, favorite artists, popularity signals, and collaborative filtering.

The project is designed as a recommendation system rather than a Spotify clone. Users can browse a curated song catalog, rate tracks, build a taste profile, and receive personalized recommendations with explanations for why each song was suggested.

## Features

- User registration and login
- JWT-based authentication
- Browse and search songs
- Filter songs by genre
- Rate songs from 1 to 5 stars
- Build a taste profile with favorite genres and artists
- Personalized music recommendations
- Cold-start recommendations for new users
- Collaborative filtering using similar users
- Rating recency weighting
- Genre and artist preference learning
- Popularity-based ranking
- Recommendation diversity
- Human-readable recommendation explanations
- Recommendation detail breakdowns
- Responsive dark-themed frontend

## Recommendation System

MusicMatch combines several signals to generate personalized song recommendations.

### Rating Preferences

User ratings are used to learn which genres and artists a user tends to like or dislike.

Ratings are put into preference signals, and newer ratings receive more weight using recency decay. This allows a user's recommendation profile to adapt if their music taste changes over time.

### Favorite Genres and Artists

Users can build a taste profile by selecting favorite genres and artists.

These preferences are especially useful for new users who have not rated many songs yet.

As users add more meaningful ratings, their actual rating history becomes increasingly important in the recommendation score.

### Collaborative Filtering

MusicMatch also uses collaborative filtering.

The system compares a user's ratings with ratings from other users. If another user has a similar pattern of likes and dislikes, songs rated highly by that similar user can receive an additional recommendation boost.

The system requires overlapping meaningful ratings before considering two users similar.

### Popularity

Song popularity is included as a smaller ranking signal.

This helps recognizable and widely listened-to songs break ties between otherwise similar candidates without letting popularity completely control the recommendations.

### Diversity

After songs are scored, the final recommendation list is reranked to improve variety.

MusicMatch limits how many songs from the same artist can appear and applies a small penalty when the list becomes too concentrated in one genre.

## Recommendation Explanations

Each recommendation includes a short explanation describing why the song was suggested.

Examples include:

- You've rated this artist highly.
- You've rated this genre highly.
- This is one of your favorite artists.
- You selected this as a favorite genre.
- Users with similar taste also rated this song highly.

Users can also expand the **Why this recommendation** section to see individual recommendation signals such as:

- Genre preference
- Artist preference
- Popularity
- Favorite genre match
- Favorite artist match
- Similar-user signal
- Similar-user support

## Song Catalog

The current MusicMatch catalog contains approximately **2,140 songs** from recognizable artists across multiple decades and genres.

Catalog metadata is built using data from **MusicBrainz** and **ListenBrainz**.

The catalog includes information such as:

- Song title
- Artist
- Genre
- MusicBrainz ID
- Release year
- Listen count
- Listener count
- Popularity
- Duration

The current catalog includes the following main genres:

- Rock
- Pop
- Hip-Hop
- R&B
- Electronic
- Country
- Metal
- Jazz
- Latin
- Reggae

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- CSS

### Backend

- Node.js
- Express
- TypeScript
- JWT authentication
- PostgreSQL
- Prisma contract tooling

### Recommendation Engine

- Python
- pandas
- NumPy
- SQLAlchemy

### Testing

- pytest
- Vitest
- Supertest

## Project Structure

```text
music-recommendation-engine/
├── client/
│   ├── src/
│   └── React + TypeScript frontend
│
├── server/
│   ├── src/
│   ├── tests/
│   └── Express + TypeScript backend
│
├── recommender/
│   ├── src/
│   │   └── preprocessing/
│   │       ├── recommend.py
│   │       ├── import_to_db.py
│   │       └── catalog/
│   └── tests/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── README.md
└── .gitignore
```

## Catalog Pipeline

The catalog-building workflow is located in:

```text
recommender/src/preprocessing/catalog/
```

The catalog pipeline:

1. Starts with a curated list of recognizable artists.
2. Finds MusicBrainz artist IDs.
3. Retrieves popular recordings using ListenBrainz.
4. Enriches recordings with metadata such as release year and genre.
5. Cleans and normalizes the catalog.
6. Removes duplicate songs.
7. Fills missing genre information where possible.
8. Normalizes popularity values.
9. Produces a final database-ready catalog.
10. Imports the finished catalog into PostgreSQL.

Some of the main catalog scripts include:

```text
artists.py
build_catalog.py
clean_catalog.py
enrich_catalog.py
fill_missing_genres.py
fix_release_years.py
musicbrainz.py
listenbrainz.py
prepare_final_catalog.py
```

## Database

The main database entities are:

- User
- Artist
- Genre
- Song
- Rating
- UserFavoriteArtist
- UserFavoriteGenre

Each user can rate a song only once because ratings use a unique constraint on:

```text
(userId, songId)
```

Updating a rating changes the existing rating rather than creating a duplicate.

## Getting Started

### Requirements

Make sure the following are installed:

- Node.js
- npm
- Python 3
- PostgreSQL

## 1. Clone the Repository

```bash
git clone https://github.com/chrislff02/music-recommendation-engine.git
cd music-recommendation-engine
```

## 2. Backend Setup

Move into the server directory:

```bash
cd server
```

Install dependencies:

```bash
npm install
```

Create a `.env` file inside the `server` directory.

Example:

```env
DATABASE_URL=postgresql://your_user@localhost:5432/music_recommendation_engine
JWT_SECRET=your_secret_here
```

Start the backend:

```bash
npm run dev
```

The backend runs on:

```text
http://localhost:5001
```

## 3. Frontend Setup

Open another terminal and move into the client directory:

```bash
cd client
```

Install dependencies:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

The frontend runs on:

```text
http://localhost:5173
```

## 4. Python Recommender Setup

Open another terminal and move into the recommender directory:

```bash
cd recommender
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Running the Recommender Directly

Recommendations can be generated directly from the command line.

From the `recommender` directory:

```bash
python src/preprocessing/recommend.py 1
```

Replace `1` with the ID of the user you want to generate recommendations for.

The recommender returns recommendation data as JSON.

## Testing

### Recommendation Engine Tests

From the `recommender` directory:

```bash
pytest -q
```

Current result:

```text
14 passed
```

### Backend Tests

From the `server` directory:

```bash
npm test
```

Current result:

```text
3 test files passed
6 tests passed
```

The backend test suite includes authentication protection and integration tests for preferences and ratings.

### Frontend Production Build

From the `client` directory:

```bash
npm run build
```

This runs the TypeScript compiler and creates a production Vite build.

## Current Recommendation Flow

```text
Favorite genres / artists
        +
User ratings
        +
Rating recency
        +
Learned genre preference
        +
Learned artist preference
        +
Collaborative filtering
        +
Popularity
        ↓
Combined recommendation score
        ↓
Diversity reranking
        ↓
Personalized recommendations
        ↓
Human-readable explanations
```

## Rating Behavior

MusicMatch treats ratings differently depending on how strongly they represent a user's preference.

- 5 stars = strong positive preference
- 4 stars = positive preference
- 3 stars = neutral
- 2 stars = negative preference
- 1 star = strong negative preference

Neutral 3-star ratings are stored but do not strongly influence the user's recommendation profile.

## Cold Start

New users often have too little rating history for a recommendation system to understand their taste.

MusicMatch handles this by allowing users to select favorite genres and artists when building their taste profile.

These preferences can be used to generate useful early recommendations while the system waits for more rating data.

As the user rates more songs, the recommendation engine gradually relies more heavily on learned preferences.

## Collaborative Filtering

Collaborative filtering compares users based on overlapping ratings.

The system:

1. Finds users who have rated some of the same songs.
2. Converts meaningful ratings into positive or negative preference values.
3. Calculates similarity between users.
4. Applies shrinkage when there are only a small number of overlapping ratings.
5. Uses positively similar users to score unseen songs.
6. Tracks how many similar users contributed to a recommendation.

Collaborative filtering is only one component of the final recommendation score, so it complements rather than replaces the user's own taste profile.

## Recommendation Diversity

High-scoring recommendations can sometimes become repetitive.

For example, a user who strongly likes one artist could otherwise receive many songs from that same artist.

MusicMatch performs a final diversity reranking step that:

- limits the number of songs from the same artist
- reduces excessive genre repetition
- keeps high-scoring songs near the top of the list

## Future Improvements

Possible future improvements include:

- Expand the catalog beyond 2,140 songs
- Add more users to strengthen collaborative filtering
- Explore matrix factorization or other collaborative approaches
- Improve genre hierarchy and subgenre handling
- Add automated catalog refreshes
- Add recommendation analytics
- Improve discovery and exploration controls
- Deploy the frontend, backend, database, and recommender
- Add additional automated frontend testing

## About the Project

MusicMatch was built as a project to combine several areas of software development into one application:

- Full-stack web development
- Recommendation systems
- Python data processing
- PostgreSQL database design
- Authentication
- REST APIs
- React and TypeScript
- Automated testing
- External music metadata APIs
- Data cleaning and catalog construction

The recommendation algorithm is implemented directly in Python rather than relying on an external recommendation service.

The goal of the project is to demonstrate how user behavior, onboarding preferences, collaborative signals, and catalog metadata can be combined into an explainable personalized music discovery system.
