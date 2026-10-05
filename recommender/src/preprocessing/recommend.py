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


RETURN_COLUMNS = [
    "id",
    "title",
    "artist",
    "genre",
    "positive_similarity",
    "negative_similarity",
    "genre_score",
    "favorite_genre_score",
    "favorite_artist_score",
    "popularity",
    "score",
    "explanation",
]


# --------------------------------------------------
# DATABASE LOADERS
# --------------------------------------------------


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


def load_favorite_genres(engine, user_id):
    query = text(
        """
        SELECT
            g.name AS genre
        FROM "UserFavoriteGenre" ufg
        JOIN "Genre" g
            ON ufg."genreId" = g.id
        WHERE ufg."userId" = :user_id
        """
    )

    return pd.read_sql_query(
        query,
        engine,
        params={
            "user_id": user_id,
        },
    )


def load_favorite_artists(engine, user_id):
    query = text(
        """
        SELECT
            a.name AS artist
        FROM "UserFavoriteArtist" ufa
        JOIN "Artist" a
            ON ufa."artistId" = a.id
        WHERE ufa."userId" = :user_id
        """
    )

    return pd.read_sql_query(
        query,
        engine,
        params={
            "user_id": user_id,
        },
    )


# --------------------------------------------------
# HELPERS
# --------------------------------------------------


def prepare_onboarding_preferences(
    usable_songs,
    favorite_genres,
    favorite_artists,
):
    if favorite_genres is None:
        favorite_genres = pd.DataFrame(
            columns=["genre"]
        )

    if favorite_artists is None:
        favorite_artists = pd.DataFrame(
            columns=["artist"]
        )

    favorite_genre_names = set(
        favorite_genres["genre"]
        .dropna()
        .astype(str)
    )

    favorite_artist_names = set(
        favorite_artists["artist"]
        .dropna()
        .astype(str)
    )

    usable_songs = usable_songs.copy()

    usable_songs["favorite_genre_score"] = (
        usable_songs["genre"]
        .apply(
            lambda value: (
                1.0
                if pd.notna(value)
                and str(value) in favorite_genre_names
                else 0.0
            )
        )
    )

    usable_songs["favorite_artist_score"] = (
        usable_songs["artist"]
        .apply(
            lambda value: (
                1.0
                if pd.notna(value)
                and str(value) in favorite_artist_names
                else 0.0
            )
        )
    )

    has_onboarding_preferences = (
        bool(favorite_genre_names)
        or bool(favorite_artist_names)
    )

    return (
        usable_songs,
        favorite_genre_names,
        favorite_artist_names,
        has_onboarding_preferences,
    )


def build_cold_start_recommendations(
    usable_songs,
    rated_song_ids,
    limit,
):
    recommendations = usable_songs[
        ~usable_songs["id"].isin(
            rated_song_ids
        )
    ].copy()

    if recommendations.empty:
        return pd.DataFrame()

    recommendations["positive_similarity"] = 0.5
    recommendations["negative_similarity"] = 0.0
    recommendations["genre_score"] = 0.5

    onboarding_score = (
        recommendations["favorite_genre_score"] * 0.60
        + recommendations["favorite_artist_score"] * 0.40
    )

    # Onboarding drives most of a new user's score.
    # Popularity gives reasonable ordering among otherwise
    # similar cold-start candidates.
    recommendations["score"] = (
        onboarding_score * 0.80
        + recommendations["popularity"].fillna(0) * 0.20
    )

    recommendations["score"] = (
        recommendations["score"]
        .clip(0, 1)
    )

    def build_explanation(row):
        reasons = []

        if row["favorite_artist_score"] > 0:
            reasons.append(
                f"{row['artist']} is one of your favorite artists."
            )

        if row["favorite_genre_score"] > 0:
            reasons.append(
                f"You selected {row['genre']} as a favorite genre."
            )

        if not reasons:
            reasons.append(
                "This song is being suggested while "
                "MusicMatch learns your taste."
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

    recommendations = (
        recommendations
        .sort_values(
            by=[
                "score",
                "popularity",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .head(limit)
        .copy()
    )

    return recommendations[
        RETURN_COLUMNS
    ]


# --------------------------------------------------
# RECOMMENDATION ENGINE
# --------------------------------------------------


def build_recommendations_from_data(
    songs,
    ratings,
    favorite_genres=None,
    favorite_artists=None,
    limit=10,
):
    # --------------------------------------------------
    # PREPARE SONG DATA
    # --------------------------------------------------

    usable_songs = songs.dropna(
        subset=FEATURE_COLUMNS
    ).copy()

    if usable_songs.empty:
        return pd.DataFrame()

    (
        usable_songs,
        favorite_genre_names,
        favorite_artist_names,
        has_onboarding_preferences,
    ) = prepare_onboarding_preferences(
        usable_songs=usable_songs,
        favorite_genres=favorite_genres,
        favorite_artists=favorite_artists,
    )

    # --------------------------------------------------
    # NO RATINGS: PURE COLD START
    # --------------------------------------------------

    if ratings.empty:
        if not has_onboarding_preferences:
            return pd.DataFrame()

        return build_cold_start_recommendations(
            usable_songs=usable_songs,
            rated_song_ids=set(),
            limit=limit,
        )

    # --------------------------------------------------
    # MATCH RATINGS TO SONG DATA
    # --------------------------------------------------

    rated = ratings.merge(
        usable_songs,
        left_on="songId",
        right_on="id",
        how="inner",
    )

    if rated.empty:
        if has_onboarding_preferences:
            return build_cold_start_recommendations(
                usable_songs=usable_songs,
                rated_song_ids=set(
                    ratings["songId"]
                ),
                limit=limit,
            )

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

    # Future timestamps should never increase weight.
    rated["age_days"] = (
        rated["age_days"]
        .clip(lower=0)
    )

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
    # SEPARATE LIKES / DISLIKES / NEUTRAL
    # --------------------------------------------------

    liked = rated[
        rated["value"] >= 4
    ].copy()

    disliked = rated[
        rated["value"] <= 2
    ].copy()

    meaningful_rating_count = (
        len(liked)
        + len(disliked)
    )

    # If every rating is neutral, onboarding can still
    # provide cold-start recommendations.
    if meaningful_rating_count == 0:
        if has_onboarding_preferences:
            return build_cold_start_recommendations(
                usable_songs=usable_songs,
                rated_song_ids=set(
                    ratings["songId"]
                ),
                limit=limit,
            )

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

    candidate_features = (
        feature_frame.to_numpy()
    )

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
    # GENRE PREFERENCE LEARNED FROM RATINGS
    # --------------------------------------------------

    genre_data = rated.dropna(
        subset=["genre"]
    ).copy()

    genre_scores = {}

    for genre_name, group in genre_data.groupby("genre"):
        ratings_array = (
            group["value"]
            .to_numpy()
        )

        recency_weights = (
            group["recency_weight"]
            .to_numpy()
        )

        weighted_average = np.average(
            ratings_array,
            weights=recency_weights,
        )

        genre_scores[genre_name] = (
            weighted_average - 1
        ) / 4

    def get_genre_score(genre_name):
        if pd.isna(genre_name):
            return 0.5

        return genre_scores.get(
            genre_name,
            0.5,
        )

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

    # Ratings gradually replace onboarding preferences.
    confidence = min(
        meaningful_rating_count / 10,
        1.0,
    )

    onboarding_weight = (
        1.0 - confidence
    )

    # --------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------

    rating_based_score = (
        recommendations["positive_similarity"] * 0.60
        - recommendations["negative_similarity"] * 0.15
        + recommendations["genre_score"] * 0.20
    )

    onboarding_score = (
        recommendations["favorite_genre_score"] * 0.60
        + recommendations["favorite_artist_score"] * 0.40
    )

    recommendations["score"] = (
        rating_based_score * confidence
        + onboarding_score * onboarding_weight * 0.80
        + recommendations["popularity"].fillna(0) * 0.05
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

        if row["favorite_artist_score"] > 0:
            reasons.append(
                f"{row['artist']} is one of your favorite artists."
            )

        if row["favorite_genre_score"] > 0:
            reasons.append(
                f"You selected {row['genre']} as a favorite genre."
            )

        genre_name = row["genre"]
        genre_score = row["genre_score"]

        if pd.notna(genre_name):
            if genre_score >= 0.75:
                reasons.append(
                    f"You've rated {genre_name} highly."
                )

            elif genre_score <= 0.25:
                reasons.append(
                    f"You've tended to rate {genre_name} lower."
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
                - diversity_penalty * redundancy
            )

            if rerank_score > best_rerank_score:
                best_rerank_score = rerank_score
                best_song_id = song_id

        if best_song_id is None:
            break

        selected_song = candidate_pool[
            candidate_pool["id"]
            == best_song_id
        ].iloc[0]

        selected_artist = (
            selected_song["artist"]
        )

        selected_ids.append(
            best_song_id
        )

        artist_counts[selected_artist] = (
            artist_counts.get(
                selected_artist,
                0,
            )
            + 1
        )

        candidate_pool = candidate_pool[
            candidate_pool["id"]
            != best_song_id
        ]

    if not selected_ids:
        return pd.DataFrame()

    recommendations = (
        recommendations
        .set_index("id")
        .loc[selected_ids]
        .reset_index()
    )

    return recommendations[
        RETURN_COLUMNS
    ]


# --------------------------------------------------
# DATABASE ENTRY POINT
# --------------------------------------------------


def build_recommendations(
    user_id,
    limit=10,
):
    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not defined"
        )

    engine = create_engine(
        database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )
    )

    try:
        songs = load_songs(
            engine
        )

        ratings = load_ratings(
            engine,
            user_id,
        )

        favorite_genres = load_favorite_genres(
            engine,
            user_id,
        )

        favorite_artists = load_favorite_artists(
            engine,
            user_id,
        )

    finally:
        engine.dispose()

    return build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        favorite_genres=favorite_genres,
        favorite_artists=favorite_artists,
        limit=limit,
    )


# --------------------------------------------------
# COMMAND-LINE ENTRY POINT
# --------------------------------------------------


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