import sys
from pathlib import Path

import pandas as pd

sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
    )
)

from src.preprocessing.recommend import (
    build_recommendations_from_data,
)


def make_song(
    song_id,
    title,
    artist,
    genre,
    tempo,
    energy,
    danceability,
    valence,
    acousticness,
    instrumentalness,
    speechiness,
    liveness,
    popularity,
):
    return {
        "id": song_id,
        "title": title,
        "externalId": str(song_id),
        "artist": artist,
        "genre": genre,
        "tempo": tempo,
        "energy": energy,
        "danceability": danceability,
        "valence": valence,
        "acousticness": acousticness,
        "instrumentalness": instrumentalness,
        "speechiness": speechiness,
        "liveness": liveness,
        "popularity": popularity,
        "duration": 200,
    }


def test_rated_songs_are_excluded():
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Song",
                "Artist A",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.8,
            ),
            make_song(
                2,
                "Candidate Song",
                "Artist B",
                "Rock",
                121,
                0.79,
                0.71,
                0.69,
                0.21,
                0.11,
                0.09,
                0.19,
                0.7,
            ),
            make_song(
                3,
                "Another Candidate",
                "Artist C",
                "Pop",
                90,
                0.4,
                0.5,
                0.6,
                0.5,
                0.2,
                0.1,
                0.3,
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
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Neutral Song",
                "Artist A",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.8,
            ),
            make_song(
                2,
                "Candidate Song",
                "Artist B",
                "Rock",
                121,
                0.79,
                0.71,
                0.69,
                0.21,
                0.11,
                0.09,
                0.19,
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
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Song",
                "Artist A",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.9,
            ),
            make_song(
                2,
                "Artist B Song 1",
                "Artist B",
                "Rock",
                121,
                0.79,
                0.71,
                0.69,
                0.21,
                0.11,
                0.09,
                0.19,
                0.9,
            ),
            make_song(
                3,
                "Artist B Song 2",
                "Artist B",
                "Rock",
                122,
                0.78,
                0.72,
                0.68,
                0.22,
                0.12,
                0.08,
                0.18,
                0.85,
            ),
            make_song(
                4,
                "Artist B Song 3",
                "Artist B",
                "Rock",
                123,
                0.77,
                0.73,
                0.67,
                0.23,
                0.13,
                0.07,
                0.17,
                0.8,
            ),
            make_song(
                5,
                "Artist C Song",
                "Artist C",
                "Rock",
                119,
                0.76,
                0.69,
                0.66,
                0.24,
                0.14,
                0.06,
                0.16,
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

def test_high_rated_genre_gets_higher_genre_score():
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Rock Song",
                "Artist A",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.8,
            ),
            make_song(
                2,
                "Disliked Pop Song",
                "Artist B",
                "Pop",
                100,
                0.4,
                0.5,
                0.4,
                0.6,
                0.2,
                0.1,
                0.3,
                0.7,
            ),
            make_song(
                3,
                "Rock Candidate",
                "Artist C",
                "Rock",
                121,
                0.79,
                0.71,
                0.69,
                0.21,
                0.11,
                0.09,
                0.19,
                0.75,
            ),
            make_song(
                4,
                "Pop Candidate",
                "Artist D",
                "Pop",
                101,
                0.41,
                0.51,
                0.39,
                0.59,
                0.21,
                0.11,
                0.29,
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
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Old Rock Rating",
                "Artist A",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.8,
            ),
            make_song(
                2,
                "Recent Rock Rating",
                "Artist B",
                "Rock",
                121,
                0.79,
                0.71,
                0.69,
                0.21,
                0.11,
                0.09,
                0.19,
                0.8,
            ),
            make_song(
                3,
                "Rock Candidate",
                "Artist C",
                "Rock",
                122,
                0.78,
                0.72,
                0.68,
                0.22,
                0.12,
                0.08,
                0.18,
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
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Song A",
                "Artist A",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
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

def test_favorite_genre_boosts_recommendation():
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Song",
                "Rated Artist",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.5,
            ),
            make_song(
                2,
                "Favorite Genre Candidate",
                "Artist A",
                "Jazz",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.5,
            ),
            make_song(
                3,
                "Other Genre Candidate",
                "Artist B",
                "Pop",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
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
    songs = pd.DataFrame(
        [
            make_song(
                1,
                "Liked Song",
                "Rated Artist",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.5,
            ),
            make_song(
                2,
                "Favorite Artist Candidate",
                "Favorite Artist",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.5,
            ),
            make_song(
                3,
                "Other Artist Candidate",
                "Other Artist",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
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
    songs_list = []

    # Ten rated songs with identical musical characteristics.
    for song_id in range(1, 11):
        songs_list.append(
            make_song(
                song_id,
                f"Rated Song {song_id}",
                f"Rated Artist {song_id}",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.5,
            )
        )

    # Two otherwise identical candidates.
    songs_list.extend(
        [
            make_song(
                11,
                "Favorite Artist Candidate",
                "Favorite Artist",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
                0.5,
            ),
            make_song(
                12,
                "Other Artist Candidate",
                "Other Artist",
                "Rock",
                120,
                0.8,
                0.7,
                0.7,
                0.2,
                0.1,
                0.1,
                0.2,
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

    # --------------------------------------------------
    # SPARSE USER:
    # only one meaningful rating
    # --------------------------------------------------

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

    # --------------------------------------------------
    # EXPERIENCED USER:
    # ten meaningful ratings -> full confidence
    # --------------------------------------------------

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

    # With sparse feedback, onboarding should create
    # a noticeable favorite-artist advantage.
    assert sparse_boost > 0

    # Once the user has ten meaningful ratings,
    # confidence reaches 1.0 and onboarding no longer
    # changes the final score.
    assert abs(dense_boost) < 1e-9

    # Therefore onboarding has more influence for
    # a new/sparse user than an experienced user.
    assert sparse_boost > dense_boost