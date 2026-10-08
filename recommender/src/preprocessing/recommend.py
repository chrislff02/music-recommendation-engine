"""
Generates personalized song recommendations using onboarding preferences,
recency-weighted ratings, learned genre & artist preferences,
user-based collaborative filtering, popularity & diversity reranking.

The module can be imported by tests/executed directly from the
command line by the Node/Express backend.
"""
from pathlib import Path

import json
import os
import sys

import numpy as np
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Load the same database connection used by the Node backend.
load_dotenv(
    PROJECT_ROOT
    / "server"
    / ".env"
)


RETURN_COLUMNS = [
    "id",
    "title",
    "artist",
    "genre",
    "releaseYear",
    "popularity",
    "genre_score",
    "artist_score",
    "favorite_genre_score",
    "favorite_artist_score",
    "collaborative_score",
    "collaborative_support",
    "score",
    "explanation",
]


# --------------------------------------------------
# DATABASE LOADERS
# --------------------------------------------------


def load_songs(engine):
    """Load the full song catalog & related artist/genre metadata."""

    query = text(
        """
        SELECT
            s.id,
            s.title,
            s."externalId",
            s."musicBrainzId",
            s."releaseYear",
            s."listenCount",
            s."listenerCount",
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


def load_ratings(
    engine,
    user_id,
):
    """Load all ratings submitted by a specific user."""

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


def load_all_ratings(engine):
    """Load ratings from all users for collaborative filtering."""

    query = text(
        """
        SELECT
            "userId",
            "songId",
            value,
            "updatedAt"
        FROM "Rating"
        ORDER BY
            "userId",
            "songId"
        """
    )

    return pd.read_sql_query(
        query,
        engine,
    )


def load_favorite_genres(
    engine,
    user_id,
):
    """Load the genres selected in a user's taste profile."""

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


def load_favorite_artists(
    engine,
    user_id,
):
    """Load the artists selected in a user's taste profile."""

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
# ONBOARDING PREFERENCES
# --------------------------------------------------

def prepare_onboarding_preferences(
    songs,
    favorite_genres,
    favorite_artists,
):
    """
    Add favorite-genre & favorite-artist match scores to each song.

    Returns the updated song DataFrame, the selected genre & artist
    names & whether the user has any onboarding preferences.
    """

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

    songs = songs.copy()

    songs["favorite_genre_score"] = (
        songs["genre"]
        .apply(
            lambda genre: (
                1.0
                if (
                    pd.notna(genre)
                    and str(genre)
                    in favorite_genre_names
                )
                else 0.0
            )
        )
    )

    songs["favorite_artist_score"] = (
        songs["artist"]
        .apply(
            lambda artist: (
                1.0
                if (
                    pd.notna(artist)
                    and str(artist)
                    in favorite_artist_names
                )
                else 0.0
            )
        )
    )

    has_onboarding_preferences = (
        bool(favorite_genre_names)
        or bool(favorite_artist_names)
    )

    return (
        songs,
        favorite_genre_names,
        favorite_artist_names,
        has_onboarding_preferences,
    )


# --------------------------------------------------
# RATING RECENCY
# --------------------------------------------------

def add_recency_weights(rated):
    """
    Add an exponential recency weight to each rating.

    Ratings gradually lose influence over time using a 180 day
    half-life, while newer ratings receive greater weight.
    """

    rated = rated.copy()

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

    # A future timestamp should never increase
    # the importance of a rating.
    rated["age_days"] = (
        rated["age_days"]
        .clip(lower=0)
    )

    # A rating keeps roughly half of its influence
    # after six months.
    half_life_days = 180

    rated["recency_weight"] = np.exp(
        -np.log(2)
        * rated["age_days"]
        / half_life_days
    )

    return rated


# --------------------------------------------------
# LEARNED GENRE / ARTIST PREFERENCES
# --------------------------------------------------

def calculate_preference_scores(
    rated,
    column,
):
    """
    Calculate recency-weighted preference scores for genres/artists.

    The weighted 1-5 rating average is normalized to a 0-1 score,
    where higher values represent stronger user preference.
    """

    scores = {}

    usable = rated.dropna(
        subset=[column]
    ).copy()

    if usable.empty:
        return scores

    for value, group in usable.groupby(
        column
    ):
        rating_values = (
            group["value"]
            .astype(float)
            .to_numpy()
        )

        weights = (
            group["recency_weight"]
            .astype(float)
            .to_numpy()
        )

        if weights.sum() <= 0:
            continue

        weighted_average = np.average(
            rating_values,
            weights=weights,
        )

        # Convert the 1–5 rating scale
        # into a 0–1 preference score.
        scores[value] = float(
            np.clip(
                (weighted_average - 1) / 4,
                0,
                1,
            )
        )

    return scores


def apply_learned_preferences(
    songs,
    genre_scores,
    artist_scores,
):
    """
    Attach learned genre & artist preference scores to candidate songs.

    Unknown genres/artists receive a neutral score of 0.5.
    """

    songs = songs.copy()

    songs["genre_score"] = (
        songs["genre"]
        .apply(
            lambda genre: (
                0.5
                if pd.isna(genre)
                else genre_scores.get(
                    genre,
                    0.5,
                )
            )
        )
    )

    songs["artist_score"] = (
        songs["artist"]
        .apply(
            lambda artist: (
                0.5
                if pd.isna(artist)
                else artist_scores.get(
                    artist,
                    0.5,
                )
            )
        )
    )

    return songs


# --------------------------------------------------
# COLLABORATIVE FILTERING
# --------------------------------------------------

def calculate_collaborative_scores(
    user_id,
    ratings,
    all_ratings,
    candidate_song_ids,
):
    """
    Score candidate songs using user-based collaborative filtering.

    Users are compared using cosine similarity over overlapping
    non-neutral ratings. Similarities are reduced when based on only
    a small number of shared ratings & only positively similar users
    contribute to candidate song predictions.

    Returns a collaborative score from 0 to 1 & the number of similar
    users that contributed to each candidate song.
    """

    candidate_song_ids = list(
        candidate_song_ids
    )

    empty_result = pd.DataFrame(
        {
            "id": candidate_song_ids,
            "collaborative_score": 0.5,
            "collaborative_support": 0,
        }
    )

    if (
        user_id is None
        or ratings is None
        or ratings.empty
        or all_ratings is None
        or all_ratings.empty
    ):
        return empty_result

    required_columns = {
        "userId",
        "songId",
        "value",
    }

    if not required_columns.issubset(
        all_ratings.columns
    ):
        return empty_result

    # A neutral 3/5 rating does not strongly
    # describe whether the user likes the song.
    target_ratings = ratings[
        ratings["value"] != 3
    ].copy()

    if target_ratings.empty:
        return empty_result

    # Map:
    # 1 -> -1
    # 2 -> -0.5
    # 4 -> +0.5
    # 5 -> +1
    target_preferences = {
        row["songId"]: (
            row["value"] - 3
        ) / 2
        for _, row
        in target_ratings.iterrows()
    }

    candidate_song_ids = set(
        candidate_song_ids
    )

    numerators = {
        song_id: 0.0
        for song_id in candidate_song_ids
    }

    denominators = {
        song_id: 0.0
        for song_id in candidate_song_ids
    }

    support_counts = {
        song_id: 0
        for song_id in candidate_song_ids
    }

    other_users = all_ratings[
        all_ratings["userId"]
        != user_id
    ]

    for _, user_group in other_users.groupby(
        "userId"
    ):
        overlapping = user_group[
            user_group["songId"].isin(
                target_preferences.keys()
            )
        ].copy()

        # One matching song is too little evidence
        # to call two users similar.
        if len(overlapping) < 2:
            continue

        target_vector = []
        other_vector = []

        for _, row in overlapping.iterrows():
            song_id = row["songId"]

            target_vector.append(
                target_preferences[
                    song_id
                ]
            )

            other_vector.append(
                (
                    row["value"]
                    - 3
                )
                / 2
            )

        target_vector = np.array(
            target_vector,
            dtype=float,
        )

        other_vector = np.array(
            other_vector,
            dtype=float,
        )

        target_norm = np.linalg.norm(
            target_vector
        )

        other_norm = np.linalg.norm(
            other_vector
        )

        if (
            target_norm == 0
            or other_norm == 0
        ):
            continue

        similarity = float(
            np.dot(
                target_vector,
                other_vector,
            )
            / (
                target_norm
                * other_norm
            )
        )

        overlap_count = len(
            overlapping
        )

        # Shrink weak similarities that are based
        # on only a few overlapping ratings.
        shrinkage = (
            overlap_count
            / (
                overlap_count + 2
            )
        )

        similarity *= shrinkage

        # Recommendations only use users with
        # positively similar taste.
        if similarity <= 0:
            continue

        candidate_ratings = user_group[
            user_group[
                "songId"
            ].isin(
                candidate_song_ids
            )
        ]

        for _, row in candidate_ratings.iterrows():
            song_id = row["songId"]

            preference = (
                row["value"] - 3
            ) / 2

            numerators[
                song_id
            ] += (
                similarity
                * preference
            )

            denominators[
                song_id
            ] += abs(
                similarity
            )

            support_counts[
                song_id
            ] += 1

    rows = []

    for song_id in candidate_song_ids:
        denominator = denominators[
            song_id
        ]

        if denominator > 0:
            predicted_preference = (
                numerators[
                    song_id
                ]
                / denominator
            )

            collaborative_score = (
                predicted_preference
                + 1
            ) / 2

            collaborative_score = float(
                np.clip(
                    collaborative_score,
                    0,
                    1,
                )
            )

        else:
            collaborative_score = 0.5

        rows.append(
            {
                "id": song_id,
                "collaborative_score":
                    collaborative_score,
                "collaborative_support":
                    support_counts[
                        song_id
                    ],
            }
        )

    return pd.DataFrame(
        rows
    )


# --------------------------------------------------
# EXPLANATIONS
# --------------------------------------------------

def build_explanation(row):
    """
    Build a human-readable explanation for a recommendation.

    Explanations may reference favorite artists/genres/learned
    rating preferences/collaborative signals/popularity.
    """

    reasons = []

    if row[
        "favorite_artist_score"
    ] > 0:
        reasons.append(
            f"{row['artist']} is one of "
            f"your favorite artists."
        )

    if (
        row["favorite_genre_score"] > 0
        and pd.notna(row["genre"])
    ):
        reasons.append(
            f"You selected {row['genre']} "
            f"as a favorite genre."
        )

    if (
        row["artist_score"] >= 0.75
    ):
        reasons.append(
            f"You've rated {row['artist']} "
            f"highly."
        )

    elif (
        row["artist_score"] <= 0.25
    ):
        reasons.append(
            f"You've tended to rate "
            f"{row['artist']} lower."
        )

    if (
        pd.notna(row["genre"])
        and row["genre_score"] >= 0.75
    ):
        reasons.append(
            f"You've rated {row['genre']} "
            f"highly."
        )

    elif (
        pd.notna(row["genre"])
        and row["genre_score"] <= 0.25
    ):
        reasons.append(
            f"You've tended to rate "
            f"{row['genre']} lower."
        )

    if (
        row["collaborative_support"] > 0
        and row["collaborative_score"]
        >= 0.75
    ):
        reasons.append(
            "Users with similar taste also "
            "rated this song highly."
        )

    if (
        not reasons
        and row["popularity"] >= 0.75
    ):
        reasons.append(
            "This is a popular track that "
            "fits your current taste profile."
        )

    if not reasons:
        reasons.append(
            "This song adds some variety "
            "while MusicMatch learns your taste."
        )

    return " ".join(
        reasons
    )


# --------------------------------------------------
# DIVERSITY RERANKING
# --------------------------------------------------

def diversity_rerank(
    recommendations,
    limit,
):
    """
    Rerank high-scoring songs to improve artist & genre diversity.

    At most two songs from the same artist are selected & repeated
    genres receive a small score penalty during reranking.
    """

    if recommendations.empty:
        return recommendations

    candidate_pool_size = max(
        50,
        limit * 5,
    )

    candidate_pool = (
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
        .head(
            candidate_pool_size
        )
        .copy()
    )

    selected_ids = []

    artist_counts = {}
    genre_counts = {}

    # No more than two recommendations
    # from the same artist.
    max_per_artist = 2

    while (
        len(selected_ids) < limit
        and not candidate_pool.empty
    ):
        best_song_id = None
        best_rerank_score = float(
            "-inf"
        )

        for _, candidate in (
            candidate_pool.iterrows()
        ):
            artist = candidate[
                "artist"
            ]

            genre = candidate[
                "genre"
            ]

            if (
                artist_counts.get(
                    artist,
                    0,
                )
                >= max_per_artist
            ):
                continue

            # Small metadata based diversity penalty.
            # Repeated genres are allowed, but songs
            # from genres already selected lose a
            # little reranking score.
            genre_penalty = 0.0

            if pd.notna(genre):
                genre_penalty = (
                    genre_counts.get(
                        genre,
                        0,
                    )
                    * 0.02
                )

            rerank_score = (
                candidate["score"]
                - genre_penalty
            )

            if (
                rerank_score
                > best_rerank_score
            ):
                best_rerank_score = (
                    rerank_score
                )

                best_song_id = candidate[
                    "id"
                ]

        if best_song_id is None:
            break

        selected_song = candidate_pool[
            candidate_pool["id"]
            == best_song_id
        ].iloc[0]

        artist = selected_song[
            "artist"
        ]

        genre = selected_song[
            "genre"
        ]

        selected_ids.append(
            best_song_id
        )

        artist_counts[
            artist
        ] = (
            artist_counts.get(
                artist,
                0,
            )
            + 1
        )

        if pd.notna(genre):
            genre_counts[
                genre
            ] = (
                genre_counts.get(
                    genre,
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

    return (
        recommendations
        .set_index("id")
        .loc[selected_ids]
        .reset_index()
    )


# --------------------------------------------------
# COLD START
# --------------------------------------------------

def build_cold_start_recommendations(
    songs,
    rated_song_ids,
    limit,
):
    """
    Generate recommendations when the user lacks meaningful rating data.

    Favorite genres & artists provide the primary personalization
    signal, while popularity acts as a smaller tie-breaking signal.
    """

    recommendations = songs[
        ~songs["id"].isin(
            rated_song_ids
        )
    ].copy()

    if recommendations.empty:
        return pd.DataFrame()

    recommendations[
        "genre_score"
    ] = 0.5

    recommendations[
        "artist_score"
    ] = 0.5

    recommendations[
        "collaborative_score"
    ] = 0.5

    recommendations[
        "collaborative_support"
    ] = 0

    onboarding_score = (
        recommendations[
            "favorite_genre_score"
        ]
        * 0.60
        +
        recommendations[
            "favorite_artist_score"
        ]
        * 0.40
    )

    # Favorite genres/artists drive cold-start
    # recommendations. Popularity breaks ties.
    recommendations["score"] = (
        onboarding_score
        * 0.85
        +
        recommendations[
            "popularity"
        ]
        .fillna(0.5)
        * 0.15
    )

    recommendations["score"] = (
        recommendations["score"]
        .clip(
            0,
            1,
        )
    )

    recommendations[
        "explanation"
    ] = recommendations.apply(
        build_explanation,
        axis=1,
    )

    recommendations = diversity_rerank(
        recommendations,
        limit,
    )

    if recommendations.empty:
        return pd.DataFrame()

    return recommendations[
        RETURN_COLUMNS
    ]


# --------------------------------------------------
# MAIN RECOMMENDATION LOGIC
# --------------------------------------------------

def build_recommendations_from_data(
    songs,
    ratings,
    favorite_genres=None,
    favorite_artists=None,
    all_ratings=None,
    user_id=None,
    limit=10,
):
    """
    Generate personalized recommendations from catalog & user data.

    Combines onboarding preferences, recency-weighted rating history,
    learned genre/artist preferences, collaborative filtering &
    popularity before applying diversity reranking.
    """

    if songs is None or songs.empty:
        return pd.DataFrame()

    songs = songs.copy()

    # Some test fixtures/older song data may not
    # include releaseYear. Treat it as unknown.
    if "releaseYear" not in songs.columns:
        songs["releaseYear"] = pd.NA

    # Popularity should always have a usable
    # neutral/default value.
    songs["popularity"] = pd.to_numeric(
        songs["popularity"],
        errors="coerce",
    ).fillna(0.5)

    songs["popularity"] = (
        songs["popularity"]
        .clip(
            0,
            1,
        )
    )

    (
        songs,
        favorite_genre_names,
        favorite_artist_names,
        has_onboarding_preferences,
    ) = prepare_onboarding_preferences(
        songs=songs,
        favorite_genres=favorite_genres,
        favorite_artists=favorite_artists,
    )


    # ----------------------------------------------
    # NO RATINGS: COLD START
    # ----------------------------------------------

    if ratings is None or ratings.empty:
        if not has_onboarding_preferences:
            return pd.DataFrame()

        return build_cold_start_recommendations(
            songs=songs,
            rated_song_ids=set(),
            limit=limit,
        )


    # ----------------------------------------------
    # MATCH RATINGS TO SONGS
    # ----------------------------------------------

    rated = ratings.merge(
        songs,
        left_on="songId",
        right_on="id",
        how="inner",
    )

    if rated.empty:
        if has_onboarding_preferences:
            return build_cold_start_recommendations(
                songs=songs,
                rated_song_ids=set(
                    ratings["songId"]
                ),
                limit=limit,
            )

        return pd.DataFrame()

    rated = add_recency_weights(
        rated
    )

    meaningful_ratings = rated[
        rated["value"] != 3
    ].copy()

    meaningful_rating_count = len(
        meaningful_ratings
    )

    # Neutral only ratings do not create a taste
    # profile. Onboarding can still provide useful
    # recommendations.
    if meaningful_rating_count == 0:
        if has_onboarding_preferences:
            return build_cold_start_recommendations(
                songs=songs,
                rated_song_ids=set(
                    ratings["songId"]
                ),
                limit=limit,
            )

        return pd.DataFrame()


    # ----------------------------------------------
    # LEARN TASTE FROM RATINGS
    # ----------------------------------------------

    genre_scores = (
        calculate_preference_scores(
            meaningful_ratings,
            "genre",
        )
    )

    artist_scores = (
        calculate_preference_scores(
            meaningful_ratings,
            "artist",
        )
    )

    songs = apply_learned_preferences(
        songs=songs,
        genre_scores=genre_scores,
        artist_scores=artist_scores,
    )


    # ----------------------------------------------
    # REMOVE ALREADY-RATED SONGS
    # ----------------------------------------------

    rated_song_ids = set(
        ratings["songId"]
    )

    recommendations = songs[
        ~songs["id"].isin(
            rated_song_ids
        )
    ].copy()

    if recommendations.empty:
        return pd.DataFrame()


    # ----------------------------------------------
    # COLLABORATIVE FILTERING
    # ----------------------------------------------

    collaborative_scores = (
        calculate_collaborative_scores(
            user_id=user_id,
            ratings=ratings,
            all_ratings=all_ratings,
            candidate_song_ids=(
                recommendations[
                    "id"
                ].tolist()
            ),
        )
    )

    recommendations = (
        recommendations.merge(
            collaborative_scores,
            on="id",
            how="left",
        )
    )

    recommendations[
        "collaborative_score"
    ] = (
        recommendations[
            "collaborative_score"
        ]
        .fillna(0.5)
    )

    recommendations[
        "collaborative_support"
    ] = (
        recommendations[
            "collaborative_support"
        ]
        .fillna(0)
        .astype(int)
    )


    # ----------------------------------------------
    # PERSONALIZATION CONFIDENCE
    # ----------------------------------------------

    # Around ten meaningful ratings gives the
    # learned rating profile full confidence.
    confidence = min(
        meaningful_rating_count
        / 10,
        1.0,
    )


    # ----------------------------------------------
    # COMPONENT SCORES
    # ----------------------------------------------

    # Genre preference contributes slightly more than artist preference
    # so recommendations can generalize beyond artists the user already knows.
    rating_profile_score = (
        recommendations[
            "genre_score"
        ]
        * 0.60
        +
        recommendations[
            "artist_score"
        ]
        * 0.40
    )

    # Favorite genres receive slightly more weight than favorite artists
    # to encourage discovery beyond the user's selected artists.
    onboarding_score = (
        recommendations[
            "favorite_genre_score"
        ]
        * 0.60
        +
        recommendations[
            "favorite_artist_score"
        ]
        * 0.40
    )

    # Increase collaborative influence as more similar users support a song.
    # Three or more supporting users gives this signal full confidence.
    collaborative_confidence = (
        recommendations[
            "collaborative_support"
        ]
        .clip(
            lower=0,
            upper=3,
        )
        / 3
    )


    # ----------------------------------------------
    # FINAL SCORE
    # ----------------------------------------------

    # As the user provides more ratings, learned preferences gradually
    # replace onboarding preferences as the main personalization signal.
    # Collaborative filtering & popularity remain secondary signals.
    rating_weight = (
        0.55
        * confidence
    )

    onboarding_weight = (
        0.55
        * (
            1.0 - confidence
        )
        if has_onboarding_preferences
        else 0.0
    )

    collaborative_weight = (
        0.20
        * collaborative_confidence
    )

    popularity_weight = 0.15

    total_weight = (
        rating_weight
        + onboarding_weight
        + collaborative_weight
        + popularity_weight
    )

    weighted_score = (
        rating_profile_score
        * rating_weight
        +
        onboarding_score
        * onboarding_weight
        +
        recommendations[
            "collaborative_score"
        ]
        * collaborative_weight
        +
        recommendations[
            "popularity"
        ]
        * popularity_weight
    )

    recommendations["score"] = (
        weighted_score
        / total_weight
    )

    recommendations["score"] = (
        recommendations["score"]
        .clip(
            0,
            1,
        )
    )


    # ----------------------------------------------
    # EXPLANATIONS
    # ----------------------------------------------

    recommendations[
        "explanation"
    ] = recommendations.apply(
        build_explanation,
        axis=1,
    )


    # ----------------------------------------------
    # DIVERSITY
    # ----------------------------------------------

    recommendations = diversity_rerank(
        recommendations,
        limit,
    )

    if recommendations.empty:
        return pd.DataFrame()

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
    """
    Load recommendation data from PostgreSQL & generate results
    for the requested user.
    """

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

        all_ratings = load_all_ratings(
            engine
        )

        favorite_genres = (
            load_favorite_genres(
                engine,
                user_id,
            )
        )

        favorite_artists = (
            load_favorite_artists(
                engine,
                user_id,
            )
        )

    finally:
        engine.dispose()

    return build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        favorite_genres=favorite_genres,
        favorite_artists=favorite_artists,
        all_ratings=all_ratings,
        user_id=user_id,
        limit=limit,
    )


# --------------------------------------------------
# COMMAND-LINE ENTRY POINT
# --------------------------------------------------

def main():
    """Run the recommender from the command line and output JSON."""
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "error":
                        "user_id is required",
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
                    "error":
                        "user_id must be an integer",
                }
            )
        )

        sys.exit(1)

    recommendations = (
        build_recommendations(
            user_id=user_id,
            limit=10,
        )
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

    # Using pandas JSON conversion avoids problems
    # with NumPy integer/float scalar types.
    records = json.loads(
        recommendations.to_json(
            orient="records"
        )
    )

    print(
        json.dumps(
            {
                "recommendations":
                    records,
            }
        )
    )


if __name__ == "__main__":
    main()