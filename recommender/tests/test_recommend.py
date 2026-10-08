"""
Tests for the MusicMatch recommendation engine.

These tests cover:
- Excluding already-rated songs
- Neutral and empty-rating behavior
- Genre and artist preference learning
- Rating recency
- Onboarding preferences
- Recommendation diversity
- Collaborative filtering
- Cold-start behavior
"""

import sys
from pathlib import Path

import pandas as pd


# Allow tests to import the recommender package when pytest is run
# from the recommender project directory.
sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
    )
)

from src.preprocessing.recommend import (
    build_recommendations_from_data,
    calculate_collaborative_scores,
)


def make_song(
    song_id,
    title,
    artist,
    genre,
    popularity,
):
    """
    Build a lightweight song dictionary for recommendation tests.

    Only fields used by the current metadata-based recommender are
    included so tests stay focused on active recommendation behavior.
    """
    return {
        "id": song_id,
        "title": title,
        "externalId": str(song_id),
        "artist": artist,
        "genre": genre,
        "popularity": popularity,
        "duration": 200,
    }


# --------------------------------------------------
# BASIC RECOMMENDATION BEHAVIOR
# --------------------------------------------------

def test_rated_songs_are_excluded():
    """Songs the user has already rated should not be recommended again."""
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Song",
                "Artist A",
                "Rock",
                0.8,
            ),
            make_song(
                2,
                "Candidate Song",
                "Artist B",
                "Rock",
                0.7,
            ),
            make_song(
                3,
                "Another Candidate",
                "Artist C",
                "Pop",
                0.6,
            ),
        ]
    )

    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            }
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        limit=10,
    )

    recommended_ids = set(
        recommendations["id"]
    )

    assert 1 not in recommended_ids


def test_neutral_ratings_return_no_recommendations():
    """
    A three-star rating is neutral & should not create a learned
    positive/negative taste profile by itself.
    """
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Neutral Song",
                "Artist A",
                "Rock",
                0.8,
            ),
            make_song(
                2,
                "Candidate Song",
                "Artist B",
                "Rock",
                0.7,
            ),
        ]
    )

    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 3,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            }
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        limit=10,
    )

    assert recommendations.empty


def test_artist_diversity_limit():
    """
    Diversity reranking should prevent one artist from dominating
    the recommendation list.
    """
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Song",
                "Artist A",
                "Rock",
                0.9,
            ),
            make_song(
                2,
                "Artist B Song 1",
                "Artist B",
                "Rock",
                0.9,
            ),
            make_song(
                3,
                "Artist B Song 2",
                "Artist B",
                "Rock",
                0.85,
            ),
            make_song(
                4,
                "Artist B Song 3",
                "Artist B",
                "Rock",
                0.8,
            ),
            make_song(
                5,
                "Artist C Song",
                "Artist C",
                "Rock",
                0.75,
            ),
        ]
    )

    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            }
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        limit=10,
    )

    artist_counts = (
        recommendations["artist"]
        .value_counts()
    )

    assert artist_counts.max() <= 2


# --------------------------------------------------
# LEARNED RATING PREFERENCES
# --------------------------------------------------

def test_high_rated_genre_gets_higher_genre_score():
    """
    A genre associated with a positive rating should receive a higher
    learned preference score than a genre associated with a low rating.
    """
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Rock Song",
                "Artist A",
                "Rock",
                0.8,
            ),
            make_song(
                2,
                "Disliked Pop Song",
                "Artist B",
                "Pop",
                0.7,
            ),
            make_song(
                3,
                "Rock Candidate",
                "Artist C",
                "Rock",
                0.75,
            ),
            make_song(
                4,
                "Pop Candidate",
                "Artist D",
                "Pop",
                0.65,
            ),
        ]
    )

    now = pd.Timestamp.now(tz="UTC")

    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 5,
                "updatedAt": now,
            },
            {
                "songId": 2,
                "value": 1,
                "updatedAt": now,
            },
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        limit=10,
    )

    rock_score = recommendations.loc[
        recommendations["id"] == 3,
        "genre_score",
    ].iloc[0]

    pop_score = recommendations.loc[
        recommendations["id"] == 4,
        "genre_score",
    ].iloc[0]

    assert rock_score > pop_score


def test_recent_ratings_have_more_influence_than_old_ratings():
    """
    Recency weighting should give recent feedback more influence than
    an older rating for the same genre.
    """
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Old Rock Rating",
                "Artist A",
                "Rock",
                0.8,
            ),
            make_song(
                2,
                "Recent Rock Rating",
                "Artist B",
                "Rock",
                0.8,
            ),
            make_song(
                3,
                "Rock Candidate",
                "Artist C",
                "Rock",
                0.7,
            ),
        ]
    )

    now = pd.Timestamp.now(tz="UTC")

    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 1,
                "updatedAt": now - pd.Timedelta(days=365),
            },
            {
                "songId": 2,
                "value": 5,
                "updatedAt": now,
            },
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        limit=10,
    )

    rock_candidate = recommendations.loc[
        recommendations["id"] == 3
    ].iloc[0]

    assert rock_candidate["genre_score"] > 0.5


def test_empty_ratings_return_no_recommendations():
    """No ratings alone should not create a learned recommendation profile."""
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Song A",
                "Artist A",
                "Rock",
                0.8,
            ),
        ]
    )

    ratings = pd.DataFrame(
        columns=[
            "songId",
            "value",
            "updatedAt",
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        limit=10,
    )

    assert recommendations.empty


# --------------------------------------------------
# ONBOARDING PREFERENCES
# --------------------------------------------------

def test_favorite_genre_boosts_recommendation():
    """
    A song matching one of the user's onboarding genres should receive
    both an onboarding score & a higher final recommendation score.
    """
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Song",
                "Rated Artist",
                "Rock",
                0.5,
            ),
            make_song(
                2,
                "Favorite Genre Candidate",
                "Artist A",
                "Jazz",
                0.5,
            ),
            make_song(
                3,
                "Other Genre Candidate",
                "Artist B",
                "Pop",
                0.5,
            ),
        ]
    )

    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            }
        ]
    )

    favorite_genres = pd.DataFrame(
        [
            {
                "genre": "Jazz",
            }
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        favorite_genres=favorite_genres,
        favorite_artists=pd.DataFrame(
            columns=["artist"]
        ),
        limit=10,
    )

    jazz_candidate = recommendations[
        recommendations["id"] == 2
    ].iloc[0]

    pop_candidate = recommendations[
        recommendations["id"] == 3
    ].iloc[0]

    assert jazz_candidate["favorite_genre_score"] == 1.0
    assert pop_candidate["favorite_genre_score"] == 0.0

    assert (
        jazz_candidate["score"]
        > pop_candidate["score"]
    )

    assert (
        "favorite genre"
        in jazz_candidate["explanation"].lower()
    )


def test_favorite_artist_boosts_recommendation():
    """
    A song by one of the user's onboarding artists should receive an
    artist preference boost & mention it in the explanation.
    """
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Song",
                "Rated Artist",
                "Rock",
                0.5,
            ),
            make_song(
                2,
                "Favorite Artist Candidate",
                "Favorite Artist",
                "Rock",
                0.5,
            ),
            make_song(
                3,
                "Other Artist Candidate",
                "Other Artist",
                "Rock",
                0.5,
            ),
        ]
    )

    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            }
        ]
    )

    favorite_artists = pd.DataFrame(
        [
            {
                "artist": "Favorite Artist",
            }
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        favorite_genres=pd.DataFrame(
            columns=["genre"]
        ),
        favorite_artists=favorite_artists,
        limit=10,
    )

    favorite_candidate = recommendations[
        recommendations["id"] == 2
    ].iloc[0]

    other_candidate = recommendations[
        recommendations["id"] == 3
    ].iloc[0]

    assert (
        favorite_candidate["favorite_artist_score"]
        == 1.0
    )

    assert (
        other_candidate["favorite_artist_score"]
        == 0.0
    )

    assert (
        favorite_candidate["score"]
        > other_candidate["score"]
    )

    assert (
        "favorite artists"
        in favorite_candidate["explanation"].lower()
    )


def test_onboarding_influence_decreases_with_more_ratings():
    """
    Onboarding preferences should matter most for new users & fade
    as enough meaningful ratings are collected.
    """
    songs_list = []

    # Ten rated songs provide enough feedback to eventually reach
    # full rating-profile confidence.
    for song_id in range(1, 11):
        songs_list.append(
            make_song(
                song_id,
                f"Rated Song {song_id}",
                f"Rated Artist {song_id}",
                "Rock",
                0.5,
            )
        )

    # These candidates are otherwise identical. The only meaningful
    # difference is whether the artist matches the onboarding preference.
    songs_list.extend(
        [
            make_song(
                11,
                "Favorite Artist Candidate",
                "Favorite Artist",
                "Rock",
                0.5,
            ),
            make_song(
                12,
                "Other Artist Candidate",
                "Other Artist",
                "Rock",
                0.5,
            ),
        ]
    )

    songs = pd.DataFrame(
        songs_list
    )

    favorite_artists = pd.DataFrame(
        [
            {
                "artist": "Favorite Artist",
            }
        ]
    )

    # Sparse user: one meaningful rating means onboarding should
    # still contribute strongly to recommendation scoring.
    sparse_ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            }
        ]
    )

    sparse_recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=sparse_ratings,
        favorite_genres=pd.DataFrame(
            columns=["genre"]
        ),
        favorite_artists=favorite_artists,
        limit=20,
    )

    sparse_favorite_score = sparse_recommendations.loc[
        sparse_recommendations["id"] == 11,
        "score",
    ].iloc[0]

    sparse_other_score = sparse_recommendations.loc[
        sparse_recommendations["id"] == 12,
        "score",
    ].iloc[0]

    sparse_boost = (
        sparse_favorite_score
        - sparse_other_score
    )

    # Experienced user: ten meaningful ratings produce full confidence
    # in the learned rating profile.
    dense_ratings = pd.DataFrame(
        [
            {
                "songId": song_id,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            }
            for song_id in range(1, 11)
        ]
    )

    dense_recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=dense_ratings,
        favorite_genres=pd.DataFrame(
            columns=["genre"]
        ),
        favorite_artists=favorite_artists,
        limit=20,
    )

    dense_favorite_score = dense_recommendations.loc[
        dense_recommendations["id"] == 11,
        "score",
    ].iloc[0]

    dense_other_score = dense_recommendations.loc[
        dense_recommendations["id"] == 12,
        "score",
    ].iloc[0]

    dense_boost = (
        dense_favorite_score
        - dense_other_score
    )

    # Sparse users should still receive a visible onboarding boost.
    assert sparse_boost > 0

    # At full rating confidence, onboarding no longer changes the score.
    assert abs(dense_boost) < 1e-9

    # Therefore onboarding matters more for a new user.
    assert sparse_boost > dense_boost


def test_onboarding_only_can_generate_recommendations():
    """
    A new user with no ratings should still receive recommendations
    when onboarding preferences are available.
    """
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Rock Song",
                "Artist A",
                "Rock",
                0.5,
            ),
            make_song(
                2,
                "Pop Song",
                "Artist B",
                "Pop",
                0.5,
            ),
        ]
    )

    ratings = pd.DataFrame(
        columns=[
            "songId",
            "value",
            "updatedAt",
        ]
    )

    favorite_genres = pd.DataFrame(
        [{"genre": "Rock"}]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        favorite_genres=favorite_genres,
        favorite_artists=pd.DataFrame(
            columns=["artist"]
        ),
        limit=10,
    )

    assert not recommendations.empty
    assert recommendations.iloc[0]["id"] == 1
    assert recommendations.iloc[0]["favorite_genre_score"] == 1.0


def test_no_ratings_and_no_preferences_returns_empty():
    """
    A user with neither ratings nor onboarding preferences does not
    provide enough information for personalized recommendations.
    """
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Song A",
                "Artist A",
                "Rock",
                0.5,
            ),
        ]
    )

    ratings = pd.DataFrame(
        columns=[
            "songId",
            "value",
            "updatedAt",
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        favorite_genres=pd.DataFrame(
            columns=["genre"]
        ),
        favorite_artists=pd.DataFrame(
            columns=["artist"]
        ),
        limit=10,
    )

    assert recommendations.empty


# --------------------------------------------------
# COLLABORATIVE FILTERING
# --------------------------------------------------

def test_collaborative_score_rewards_song_liked_by_similar_user():
    """
    A candidate liked by a sufficiently similar user should receive
    a collaborative score above the neutral baseline of 0.5.
    """
    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "songId": 2,
                "value": 4,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
        ]
    )

    all_ratings = pd.DataFrame(
        [
            # Target user
            {
                "userId": 1,
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "userId": 1,
                "songId": 2,
                "value": 4,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },

            # Similar user with matching ratings on the two shared songs.
            {
                "userId": 2,
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "userId": 2,
                "songId": 2,
                "value": 4,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "userId": 2,
                "songId": 3,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
        ]
    )

    collaborative = calculate_collaborative_scores(
        user_id=1,
        ratings=ratings,
        all_ratings=all_ratings,
        candidate_song_ids=[3],
    )

    row = collaborative.iloc[0]

    assert row["id"] == 3
    assert row["collaborative_support"] == 1
    assert row["collaborative_score"] > 0.5


def test_collaborative_score_ignores_user_with_too_little_overlap():
    """
    Collaborative filtering should ignore another user when the two
    users have fewer than the required number of shared rated songs.
    """
    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "songId": 2,
                "value": 4,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
        ]
    )

    all_ratings = pd.DataFrame(
        [
            # Target user
            {
                "userId": 1,
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "userId": 1,
                "songId": 2,
                "value": 4,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },

            # This user overlaps on only one rated song, which is not
            # enough evidence to influence collaborative recommendations.
            {
                "userId": 2,
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "userId": 2,
                "songId": 3,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
        ]
    )

    collaborative = calculate_collaborative_scores(
        user_id=1,
        ratings=ratings,
        all_ratings=all_ratings,
        candidate_song_ids=[3],
    )

    row = collaborative.iloc[0]

    assert row["id"] == 3
    assert row["collaborative_support"] == 0
    assert row["collaborative_score"] == 0.5


def test_collaborative_filtering_boosts_final_recommendation_score():
    """
    A candidate supported by a similar user's ratings should rank above
    an otherwise equivalent candidate with no collaborative evidence.
    """
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Song 1",
                "Artist A",
                "Rock",
                0.5,
            ),
            make_song(
                2,
                "Liked Song 2",
                "Artist B",
                "Rock",
                0.5,
            ),
            make_song(
                3,
                "Collaborative Candidate",
                "Artist C",
                "Rock",
                0.5,
            ),
            make_song(
                4,
                "Non Collaborative Candidate",
                "Artist D",
                "Rock",
                0.5,
            ),
        ]
    )

    ratings = pd.DataFrame(
        [
            {
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "songId": 2,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
        ]
    )

    all_ratings = pd.DataFrame(
        [
            # Target user
            {
                "userId": 1,
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "userId": 1,
                "songId": 2,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },

            # Similar user agrees on both shared songs & also likes song 3.
            {
                "userId": 2,
                "songId": 1,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "userId": 2,
                "songId": 2,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
            {
                "userId": 2,
                "songId": 3,
                "value": 5,
                "updatedAt": pd.Timestamp.now(tz="UTC"),
            },
        ]
    )

    recommendations = build_recommendations_from_data(
        songs=songs,
        ratings=ratings,
        favorite_genres=pd.DataFrame(
            columns=["genre"]
        ),
        favorite_artists=pd.DataFrame(
            columns=["artist"]
        ),
        all_ratings=all_ratings,
        user_id=1,
        limit=10,
    )

    collaborative_row = recommendations[
        recommendations["id"] == 3
    ].iloc[0]

    non_collaborative_row = recommendations[
        recommendations["id"] == 4
    ].iloc[0]

    assert collaborative_row["collaborative_support"] == 1
    assert collaborative_row["collaborative_score"] > 0.5

    assert non_collaborative_row["collaborative_support"] == 0
    assert non_collaborative_row["collaborative_score"] == 0.5

    assert (
        collaborative_row["score"]
        > non_collaborative_row["score"]
    )