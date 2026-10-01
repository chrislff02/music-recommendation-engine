from pathlib import Path

import numpy as np
import pandas as pd
import psycopg
import json
import sys
from dotenv import load_dotenv
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity


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
    import os

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not defined")

    with psycopg.connect(database_url) as connection:
        songs = load_songs(connection)
        ratings = load_ratings(connection, user_id)

    if ratings.empty:
        print("This user has not rated any songs yet.")
        return pd.DataFrame()

    # Keep songs that contain every audio feature we need.
    usable_songs = songs.dropna(subset=FEATURE_COLUMNS).copy()

    rated = ratings.merge(
        usable_songs,
        left_on="songId",
        right_on="id",
        how="inner",
    )

    if rated.empty:
        print("None of this user's rated songs have usable audio features.")
        return pd.DataFrame()

    # Standardize features so tempo does not overpower 0-1 features.
    scaler = StandardScaler()

    song_features = scaler.fit_transform(
        usable_songs[FEATURE_COLUMNS]
    )

    feature_frame = pd.DataFrame(
        song_features,
        index=usable_songs["id"],
        columns=FEATURE_COLUMNS,
    )

    # Convert ratings:
    #
    # 1 -> -1.0
    # 2 -> -0.5
    # 3 ->  0.0
    # 4 ->  0.5
    # 5 ->  1.0
    #
    # Positive ratings pull recommendations toward similar songs.
    # Negative ratings push recommendations away.
    rated["weight"] = (rated["value"] - 3) / 2

    weighted_profiles = []

    for _, rating in rated.iterrows():
        song_id = rating["songId"]
        weight = rating["weight"]

        feature_vector = feature_frame.loc[song_id].to_numpy()

        weighted_profiles.append(
            feature_vector * weight
        )

    user_profile = np.sum(weighted_profiles, axis=0)

    # If every rating is 3/5, the profile contains no preference signal.
    if np.allclose(user_profile, 0):
        print(
            "The user's ratings are neutral. "
            "Rate some songs above or below 3 stars first."
        )
        return pd.DataFrame()

    similarities = cosine_similarity(
        [user_profile],
        feature_frame.to_numpy(),
    )[0]

    usable_songs["similarity"] = similarities

    rated_song_ids = set(ratings["songId"])

    recommendations = usable_songs[
        ~usable_songs["id"].isin(rated_song_ids)
    ].copy()

    # Slightly use popularity as a tie-breaker rather than allowing
    # extremely obscure but nearly identical tracks to dominate.
    recommendations["score"] = (
        recommendations["similarity"] * 0.9
        + recommendations["popularity"].fillna(0) * 0.1
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