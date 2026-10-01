from pathlib import Path
import json
import os
import sys

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
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


def load_songs(engine):
    query = text(
        """
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
    )

    return pd.read_sql_query(
        query,
        engine,
    )


def load_ratings(engine, user_id):
    query = text(
        """
        SELECT
            "songId",
            value,
            "updatedAt"
        FROM "Rating"
        WHERE "userId" = :user_id
        ORDER BY "songId"
        """
    )

    return pd.read_sql_query(
        query,
        engine,
        params={
            "user_id": user_id,
        },
    )


def build_recommendations(user_id, limit=10):
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not defined")

    engine = create_engine(
        database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )
    )

    try:
        songs = load_songs(engine)

        ratings = load_ratings(
            engine,
            user_id,
        )
    finally:
        engine.dispose()

    if ratings.empty:
        return pd.DataFrame()

    # --------------------------------------------------
    # PREPARE SONG DATA
    # --------------------------------------------------

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

    # --------------------------------------------------
    # RATING RECENCY
    # --------------------------------------------------

    rated["updatedAt"] = pd.to_datetime(
        rated["updatedAt"],
        utc=True,
    )

    now = pd.Timestamp.now(
        tz="UTC"
    )

    rated["age_days"] = (
        now - rated["updatedAt"]
    ).dt.total_seconds() / 86400

    # Ratings lose half of their recency influence
    # after about 180 days.
    half_life_days = 180

    rated["recency_weight"] = np.exp(
        -np.log(2)
        * rated["age_days"]
        / half_life_days
    )

    # --------------------------------------------------
    # STANDARDIZE AUDIO FEATURES
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

    # --------------------------------------------------
    # SEPARATE LIKES AND DISLIKES
    # --------------------------------------------------

    liked = rated[
        rated["value"] >= 4
    ].copy()

    disliked = rated[
        rated["value"] <= 2
    ].copy()

    if liked.empty and disliked.empty:
        return pd.DataFrame()

    # --------------------------------------------------
    # POSITIVE PROFILE
    # --------------------------------------------------

    positive_profile = None

    if not liked.empty:
        liked_vectors = []
        liked_weights = []

        for _, rating in liked.iterrows():
            song_id = rating["songId"]

            base_weight = (
                1.0
                if rating["value"] == 5
                else 0.75
            )

            weight = (
                base_weight
                * rating["recency_weight"]
            )

            liked_vectors.append(
                feature_frame.loc[
                    song_id
                ].to_numpy()
            )

            liked_weights.append(
                weight
            )

        positive_profile = np.average(
            liked_vectors,
            axis=0,
            weights=liked_weights,
        )

    # --------------------------------------------------
    # NEGATIVE PROFILE
    # --------------------------------------------------

    negative_profile = None

    if not disliked.empty:
        disliked_vectors = []
        disliked_weights = []

        for _, rating in disliked.iterrows():
            song_id = rating["songId"]

            base_weight = (
                1.0
                if rating["value"] == 1
                else 0.5
            )

            weight = (
                base_weight
                * rating["recency_weight"]
            )

            disliked_vectors.append(
                feature_frame.loc[
                    song_id
                ].to_numpy()
            )

            disliked_weights.append(
                weight
            )

        negative_profile = np.average(
            disliked_vectors,
            axis=0,
            weights=disliked_weights,
        )

    # --------------------------------------------------
    # AUDIO SIMILARITY
    # --------------------------------------------------

    candidate_features = feature_frame.to_numpy()

    if positive_profile is not None:
        positive_similarity = cosine_similarity(
            [positive_profile],
            candidate_features,
        )[0]

        usable_songs["positive_similarity"] = (
            positive_similarity + 1
        ) / 2
    else:
        usable_songs["positive_similarity"] = 0.5

    if negative_profile is not None:
        negative_similarity = cosine_similarity(
            [negative_profile],
            candidate_features,
        )[0]

        usable_songs["negative_similarity"] = (
            negative_similarity + 1
        ) / 2
    else:
        usable_songs["negative_similarity"] = 0.0

    # --------------------------------------------------
    # GENRE PREFERENCE
    # --------------------------------------------------

    genre_ratings = (
        rated.dropna(subset=["genre"])
        .groupby("genre")["value"]
        .mean()
        .to_dict()
    )

    def get_genre_score(genre):
        if pd.isna(genre):
            return 0.5

        average_rating = genre_ratings.get(
            genre
        )

        if average_rating is None:
            return 0.5

        return (
            average_rating - 1
        ) / 4

    usable_songs["genre_score"] = (
        usable_songs["genre"]
        .apply(get_genre_score)
    )

    # --------------------------------------------------
    # REMOVE ALREADY-RATED SONGS
    # --------------------------------------------------

    rated_song_ids = set(
        ratings["songId"]
    )

    recommendations = usable_songs[
        ~usable_songs["id"].isin(
            rated_song_ids
        )
    ].copy()

    if recommendations.empty:
        return pd.DataFrame()

    # --------------------------------------------------
    # PERSONALIZATION CONFIDENCE
    # --------------------------------------------------

    rating_count = len(
        ratings
    )

    confidence = min(
        rating_count / 10,
        1.0,
    )

    # --------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------

    personalized_score = (
        recommendations["positive_similarity"] * 0.70
        - recommendations["negative_similarity"] * 0.15
        + recommendations["genre_score"] * 0.20
    )

    recommendations["score"] = (
        personalized_score
        * confidence
        + recommendations["popularity"].fillna(0)
        * (1 - confidence)
    )

    recommendations["score"] = (
        recommendations["score"]
        .clip(0, 1)
    )

    # --------------------------------------------------
    # EXPLANATIONS
    # --------------------------------------------------

    positive_profile_series = None

    if positive_profile is not None:
        positive_profile_series = pd.Series(
            positive_profile,
            index=FEATURE_COLUMNS,
        )

    def build_explanation(row):
        reasons = []

        genre = row["genre"]
        genre_score = row["genre_score"]

        if pd.notna(genre):
            if genre_score >= 0.75:
                reasons.append(
                    f"You've rated {genre} highly."
                )

            elif genre_score <= 0.25:
                reasons.append(
                    f"You've tended to rate {genre} lower."
                )

        if positive_profile_series is not None:
            feature_distances = (
                feature_frame.loc[
                    row["id"]
                ]
                - positive_profile_series
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
                    feature.replace(
                        "_",
                        " ",
                    )
                    for feature in closest_features
                )

                reasons.append(
                    f"Strong audio match on "
                    f"{readable_features}."
                )

        if (
            negative_profile is not None
            and row["negative_similarity"]
            >= row["positive_similarity"] - 0.10
        ):
            reasons.append(
                "Some audio traits are also similar to songs "
                "you rated lower."
            )

        if not reasons:
            reasons.append(
                "This song matches your overall listening profile."
            )

        return " ".join(
            reasons
        )

    recommendations["explanation"] = (
        recommendations.apply(
            build_explanation,
            axis=1,
        )
    )

    # --------------------------------------------------
    # DIVERSITY RERANKING
    # --------------------------------------------------

    candidate_pool_size = max(
        50,
        limit * 5,
    )

    candidate_pool = (
        recommendations
        .sort_values(
            by="score",
            ascending=False,
        )
        .head(
            candidate_pool_size
        )
        .copy()
    )

    selected_ids = []
    artist_counts = {}

    diversity_penalty = 0.10
    max_per_artist = 2

    while (
        len(selected_ids) < limit
        and not candidate_pool.empty
    ):
        best_song_id = None
        best_rerank_score = float(
            "-inf"
        )

        for _, candidate in candidate_pool.iterrows():
            song_id = candidate["id"]
            artist = candidate["artist"]

            if (
                artist_counts.get(
                    artist,
                    0,
                )
                >= max_per_artist
            ):
                continue

            redundancy = 0.0

            if selected_ids:
                candidate_vector = (
                    feature_frame.loc[
                        song_id
                    ]
                    .to_numpy()
                    .reshape(
                        1,
                        -1,
                    )
                )

                selected_vectors = (
                    feature_frame.loc[
                        selected_ids
                    ]
                    .to_numpy()
                )

                similarities_to_selected = (
                    cosine_similarity(
                        candidate_vector,
                        selected_vectors,
                    )[0]
                )

                redundancy = max(
                    0.0,
                    float(
                        similarities_to_selected.max()
                    ),
                )

            rerank_score = (
                candidate["score"]
                - diversity_penalty
                * redundancy
            )

            if (
                rerank_score
                > best_rerank_score
            ):
                best_rerank_score = (
                    rerank_score
                )

                best_song_id = (
                    song_id
                )

        if best_song_id is None:
            break

        selected_song = candidate_pool[
            candidate_pool["id"]
            == best_song_id
        ].iloc[0]

        selected_artist = (
            selected_song[
                "artist"
            ]
        )

        selected_ids.append(
            best_song_id
        )

        artist_counts[
            selected_artist
        ] = (
            artist_counts.get(
                selected_artist,
                0,
            )
            + 1
        )

        candidate_pool = (
            candidate_pool[
                candidate_pool["id"]
                != best_song_id
            ]
        )

    if not selected_ids:
        return pd.DataFrame()

    recommendations = (
        recommendations
        .set_index("id")
        .loc[selected_ids]
        .reset_index()
    )

    # --------------------------------------------------
    # RETURN RESULTS
    # --------------------------------------------------

    return recommendations[
        [
            "id",
            "title",
            "artist",
            "genre",
            "positive_similarity",
            "negative_similarity",
            "genre_score",
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
        user_id = int(
            sys.argv[1]
        )

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