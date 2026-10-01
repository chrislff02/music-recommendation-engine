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

    return pd.read_sql_query(
        query,
        connection,
    )


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

    # Keep only songs with all audio features required by the model.
    usable_songs = songs.dropna(
        subset=FEATURE_COLUMNS
    ).copy()

    # Combine this user's ratings with the matching song information.
    rated = ratings.merge(
        usable_songs,
        left_on="songId",
        right_on="id",
        how="inner",
    )

    if rated.empty:
        return pd.DataFrame()

    # Convert 1-5 ratings into preference weights.
    #
    # 1 -> -0.75 = strong dislike
    # 2 -> -0.25 = dislike
    # 3 ->  0.00 = neutral
    # 4 ->  0.75 = like
    # 5 ->  1.00 = strong like
    rated["weight"] = rated["value"].map(
        RATING_WEIGHTS
    )

    # --------------------------------------------------
    # AUDIO PREFERENCE PROFILE
    # --------------------------------------------------

    # Standardize features so tempo does not overpower
    # features whose values normally range from 0 to 1.
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

    # If every useful rating is neutral, there is no
    # preference signal to build recommendations from.
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

    # Average the user's rating weight for each genre.
    genre_preferences = (
        rated.dropna(subset=["genre"])
        .groupby("genre")["weight"]
        .mean()
        .to_dict()
    )

    usable_songs["genre_preference"] = (
        usable_songs["genre"]
        .map(genre_preferences)
        .fillna(0.0)
    )

    # Convert the genre preference into a roughly 0-1 range
    # so it can be combined with similarity and popularity.
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

    # Audio similarity is the strongest signal.
    # Genre preference gives the user's favorite genres a boost.
    # Popularity is only a small tie-breaker.
    recommendations["score"] = (
        recommendations["similarity"] * 0.85
        + recommendations["genre_score"] * 0.10
        + recommendations["popularity"].fillna(0) * 0.05
    )

    # --------------------------------------------------
    # EXPLANATIONS
    # --------------------------------------------------

    profile_series = pd.Series(
        user_profile,
        index=FEATURE_COLUMNS,
    )

    def build_explanation(row):
        reasons = []

        genre = row["genre"]
        genre_preference = row["genre_preference"]

        if pd.notna(genre):
            if genre_preference >= 0.75:
                reasons.append(
                    f"You strongly prefer {genre}."
                )
            elif genre_preference >= 0.25:
                reasons.append(
                    f"You tend to like {genre}."
                )

        song_vector = feature_frame.loc[
            row["id"]
        ]

        # Find the two audio characteristics that are closest
        # to the user's learned audio preference profile.
        feature_distances = (
            song_vector - profile_series
        ).abs()

        closest_features = (
            feature_distances
            .sort_values()
            .head(2)
            .index
            .tolist()
        )

        if closest_features:
            readable_features = " and ".join(
                feature.replace("_", " ")
                for feature in closest_features
            )

            reasons.append(
                f"Strong audio match on {readable_features}."
            )

        if not reasons:
            reasons.append(
                "This song has audio characteristics "
                "similar to your preferences."
            )

        return " ".join(reasons)

    recommendations["explanation"] = recommendations.apply(
        build_explanation,
        axis=1,
    )

    # --------------------------------------------------
    # RANK RESULTS
    # --------------------------------------------------

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
            "explanation",
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