from pathlib import Path
import json
import os
import sys

import numpy as np
import pandas as pd
import psycopg
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Load the same database connection used by the Node backend.
load_dotenv(PROJECT_ROOT / "server" / ".env")


FEATURE_COLUMNS = [
    "tempo",
    "energy",
    "danceability",
    "valence",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "liveness",
]


RATING_WEIGHTS = {
    1: -0.75,
    2: -0.25,
    3: 0.0,
    4: 0.75,
    5: 1.0,
}


def load_songs(connection):
    query = """
        SELECT
            s.id,
            s.title,
            s."externalId",
            s.tempo,
            s.energy,
            s.danceability,
            s.valence,
            s.acousticness,
            s.instrumentalness,
            s.speechiness,
            s.liveness,
            s.popularity,
            s.duration,
            a.name AS artist,
            g.name AS genre
        FROM "Song" s
        JOIN "Artist" a
            ON s."artistId" = a.id
        LEFT JOIN "Genre" g
            ON s."genreId" = g.id
        ORDER BY s.id
    """

    return pd.read_sql_query(query, connection)


def load_ratings(connection, user_id):
    query = """
        SELECT
            "songId",
            value
        FROM "Rating"
        WHERE "userId" = %s
        ORDER BY "songId"
    """

    return pd.read_sql_query(
        query,
        connection,
        params=(user_id,),
    )


def build_recommendations(user_id, limit=10):
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not defined")

    with psycopg.connect(database_url) as connection:
        songs = load_songs(connection)
        ratings = load_ratings(connection, user_id)

    if ratings.empty:
        return pd.DataFrame()

    # Keep only songs with every audio feature required by the model.
    usable_songs = songs.dropna(
        subset=FEATURE_COLUMNS
    ).copy()

    rated = ratings.merge(
        usable_songs,
        left_on="songId",
        right_on="id",
        how="inner",
    )

    if rated.empty:
        return pd.DataFrame()

    # Convert 1-5 ratings into preference weights.
    rated["weight"] = rated["value"].map(
        RATING_WEIGHTS
    )

    # --------------------------------------------------
    # AUDIO PREFERENCE PROFILE
    # --------------------------------------------------

    scaler = StandardScaler()

    song_features = scaler.fit_transform(
        usable_songs[FEATURE_COLUMNS]
    )

    feature_frame = pd.DataFrame(
        song_features,
        index=usable_songs["id"],
        columns=FEATURE_COLUMNS,
    )

    weighted_profiles = []

    for _, rating in rated.iterrows():
        song_id = rating["songId"]
        weight = rating["weight"]

        feature_vector = feature_frame.loc[
            song_id
        ].to_numpy()

        weighted_profiles.append(
            feature_vector * weight
        )

    user_profile = np.sum(
        weighted_profiles,
        axis=0,
    )

    if np.allclose(user_profile, 0):
        return pd.DataFrame()

    similarities = cosine_similarity(
        [user_profile],
        feature_frame.to_numpy(),
    )[0]

    usable_songs["similarity"] = similarities

    # --------------------------------------------------
    # GENRE PREFERENCE PROFILE
    # --------------------------------------------------

    genre_preferences = (
        rated.dropna(subset=["genre"])
        .groupby("genre")["weight"]
        .mean()
        .to_dict()
    )

    # Songs in genres the user likes receive a positive boost.
    # Songs in disliked genres receive a negative adjustment.
    usable_songs["genre_preference"] = (
        usable_songs["genre"]
        .map(genre_preferences)
        .fillna(0.0)
    )

    # Normalize genre preference from the rating-weight range
    # into approximately 0-1 for easier score combination.
    usable_songs["genre_score"] = (
        usable_songs["genre_preference"] + 1
    ) / 2

    # --------------------------------------------------
    # REMOVE SONGS ALREADY RATED
    # --------------------------------------------------

    rated_song_ids = set(
        ratings["songId"]
    )

    recommendations = usable_songs[
        ~usable_songs["id"].isin(rated_song_ids)
    ].copy()

    # --------------------------------------------------
    # FINAL RECOMMENDATION SCORE
    # --------------------------------------------------

    recommendations["score"] = (
        recommendations["similarity"] * 0.85
        + recommendations["genre_score"] * 0.10
        + recommendations["popularity"].fillna(0) * 0.05
    )

    recommendations = recommendations.sort_values(
        by="score",
        ascending=False,
    ).head(limit)

    return recommendations[
        [
            "id",
            "title",
            "artist",
            "genre",
            "similarity",
            "genre_preference",
            "popularity",
            "score",
        ]
    ]
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not defined")

    with psycopg.connect(database_url) as connection:
        songs = load_songs(connection)
        ratings = load_ratings(connection, user_id)

    if ratings.empty:
        return pd.DataFrame()

    # Keep only songs with every audio feature required by the model.
    usable_songs = songs.dropna(
        subset=FEATURE_COLUMNS
    ).copy()

    rated = ratings.merge(
        usable_songs,
        left_on="songId",
        right_on="id",
        how="inner",
    )

    if rated.empty:
        return pd.DataFrame()

    # Standardize the audio features so a large-scale feature such as
    # tempo does not overpower features whose values range from 0 to 1.
    scaler = StandardScaler()

    song_features = scaler.fit_transform(
        usable_songs[FEATURE_COLUMNS]
    )

    feature_frame = pd.DataFrame(
        song_features,
        index=usable_songs["id"],
        columns=FEATURE_COLUMNS,
    )

    # Rating weights:
    #
    # 1 -> -0.75 = strong dislike
    # 2 -> -0.25 = dislike
    # 3 ->  0.00 = neutral
    # 4 ->  0.75 = like
    # 5 ->  1.00 = strong like
    #
    # Positive ratings pull the user profile toward similar songs.
    # Negative ratings push the profile away from similar songs.
    rated["weight"] = rated["value"].map(
        RATING_WEIGHTS
    )

    weighted_profiles = []

    for _, rating in rated.iterrows():
        song_id = rating["songId"]
        weight = rating["weight"]

        feature_vector = feature_frame.loc[
            song_id
        ].to_numpy()

        weighted_profiles.append(
            feature_vector * weight
        )

    user_profile = np.sum(
        weighted_profiles,
        axis=0,
    )

    # If all ratings are neutral, there is no preference signal.
    if np.allclose(user_profile, 0):
        return pd.DataFrame()

    similarities = cosine_similarity(
        [user_profile],
        feature_frame.to_numpy(),
    )[0]

    usable_songs["similarity"] = similarities

    rated_song_ids = set(
        ratings["songId"]
    )

    # Never recommend a song the user has already rated.
    recommendations = usable_songs[
        ~usable_songs["id"].isin(rated_song_ids)
    ].copy()

    # Musical similarity drives 95% of the final score.
    # Popularity acts only as a small tie-breaker.
    recommendations["score"] = (
        recommendations["similarity"] * 0.95
        + recommendations["popularity"].fillna(0) * 0.05
    )

    recommendations = recommendations.sort_values(
        by="score",
        ascending=False,
    ).head(limit)

    return recommendations[
        [
            "id",
            "title",
            "artist",
            "genre",
            "similarity",
            "popularity",
            "score",
        ]
    ]


def main():
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "error": "user_id is required",
                }
            )
        )
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print(
            json.dumps(
                {
                    "error": "user_id must be an integer",
                }
            )
        )
        sys.exit(1)

    recommendations = build_recommendations(
        user_id=user_id,
        limit=10,
    )

    if recommendations.empty:
        print(
            json.dumps(
                {
                    "recommendations": [],
                }
            )
        )
        return

    records = recommendations.to_dict(
        orient="records"
    )

    print(
        json.dumps(
            {
                "recommendations": records,
            }
        )
    )


if __name__ == "__main__":
    main()