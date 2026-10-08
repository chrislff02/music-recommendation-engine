"""
Enrich the prototype MusicMatch catalog with additional metadata.

This stage:
1. Loads the initial catalog produced by build_catalog.py.
2. Looks up detailed MusicBrainz recording metadata.
3. Searches MusicBrainz for matching recordings to estimate the
   earliest release year.
4. Extracts the strongest available genre tag.
5. Converts listener counts into a normalized 0-1 popularity score.
6. Saves the enriched catalog for the cleaning stage.
"""

import math

import pandas as pd

from .config import PROCESSED_CATALOG_DIR
from .musicbrainz import (
    get_recording_details,
    search_song_by_title_and_artist,
)


def extract_genre(recording):
    """
    Return the highest-ranked MusicBrainz tag for a recording.

    MusicBrainz recordings may contain several user/community tags.
    The tag with the highest count is used as the raw genre value
    for later normalization.
    """
    tags = recording.get(
        "tags",
        [],
    )

    if not tags:
        return None

    # Ignore tag entries that do not contain a usable name.
    valid_tags = [
        tag
        for tag in tags
        if tag.get("name")
    ]

    if not valid_tags:
        return None

    # Higher tag counts generally indicate stronger agreement that the
    # recording belongs to that genre/style.
    valid_tags.sort(
        key=lambda tag: tag.get(
            "count",
            0,
        ),
        reverse=True,
    )

    return valid_tags[0]["name"]


def normalize_popularity(
    series,
):
    """
    Convert raw listener counts into a normalized popularity score.

    A logarithmic transformation reduces the effect of extremely popular
    tracks before min-max scaling the values into the 0-1 range.

    If every song has the same transformed listener count, a neutral
    popularity value of 0.5 is returned for all songs.
    """
    # Missing/negative listener counts should not contribute
    # artificial popularity.
    cleaned = (
        series
        .fillna(0)
        .clip(lower=0)
    )

    # Listener counts are highly skewed, so log1p compresses large values
    # while preserving relative differences between songs.
    logged = cleaned.apply(
        lambda value: math.log1p(value)
    )

    minimum = logged.min()
    maximum = logged.max()

    # Avoid division by zero when every song has the same count.
    if maximum == minimum:
        return pd.Series(
            [0.5] * len(logged),
            index=logged.index,
        )

    # Min-max scale the transformed values into the 0-1 range.
    return (
        logged - minimum
    ) / (
        maximum - minimum
    )


def extract_earliest_release_year(
    recordings,
    expected_title,
):
    """
    Find the earliest plausible release year for an exact song-title match.

    Search results may include reissues/alternate recordings/similarly
    named tracks so only exact case-insensitive title matches are considered.

    Returns None when no valid year can be found.
    """
    years = []

    expected_title = (
        str(expected_title)
        .strip()
        .casefold()
    )

    for recording in recordings:
        recording_title = (
            str(
                recording.get(
                    "title",
                    ""
                )
            )
            .strip()
            .casefold()
        )

        # Ignore search results whose title does not exactly match the
        # song currently being enriched.
        if recording_title != expected_title:
            continue

        first_release_date = (
            recording.get(
                "first-release-date"
            )
        )

        if not first_release_date:
            continue

        try:
            # MusicBrainz dates may contain only a year/full date.
            # The first four characters are enough for this catalog.
            year = int(
                str(
                    first_release_date
                )[:4]
            )
        except ValueError:
            continue

        # Filter out obviously invalid date values.
        if 1900 <= year <= 2100:
            years.append(
                year
            )

    if not years:
        return None

    # The earliest matching date is used to reduce the chance of storing
    # a later reissue/remaster year instead of the original release year.
    return min(years)


def main():
    """Enrich the prototype catalog & save the next pipeline stage."""

    input_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_prototype.csv"
    )

    output_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_enriched.csv"
    )

    songs = pd.read_csv(
        input_path
    )

    # Reset the index so progress output runs cleanly from 1 through N.
    songs = songs.reset_index(
        drop=True
    )

    release_years = []
    genres = []

    total = len(songs)

    # Enrich each song individually because MusicBrainz metadata is
    # retrieved using the song's recording & artist identifiers.
    for index, row in songs.iterrows():
        recording_mbid = row[
            "recording_mbid"
        ]

        print(
            f"[{index + 1}/{total}] "
            f"{row['artist']} - "
            f"{row['title']}"
        )

        try:
            # Load detailed metadata for the exact MusicBrainz recording.
            recording = (
                get_recording_details(
                    recording_mbid
                )
            )

            # Search by title + artist so release dates from matching
            # recordings can be compared.
            search_results = (
                search_song_by_title_and_artist(
                    row["title"],
                    row["artist_mbid"],
                )
            )

            # Use the earliest valid exact-title match as the release year.
            release_year = (
                extract_earliest_release_year(
                    search_results,
                    row["title"],
                )
            )

            # Store the strongest raw MusicBrainz genre/tag.
            # It will be normalized later by clean_catalog.py.
            genre = (
                extract_genre(
                    recording
                )
            )

        except Exception as error:
            # One failed MusicBrainz request should not stop the entire
            # catalog enrichment process.
            print(
                "  Failed to enrich:",
                error,
            )

            release_year = None
            genre = None

        release_years.append(
            release_year
        )

        genres.append(
            genre
        )

    # Attach the collected enrichment results back to the song table.
    songs["release_year"] = (
        release_years
    )

    songs["genre"] = (
        genres
    )

    # Popularity is based on unique listener counts rather than raw listens,
    # then normalized so the recommender can use it as a 0-1 signal.
    songs["popularity"] = (
        normalize_popularity(
            songs["listener_count"]
        )
    )

    songs.to_csv(
        output_path,
        index=False,
    )

    print()
    print(
        f"Saved {len(songs)} enriched songs"
    )

    print(
        f"Output: {output_path}"
    )

    # Print a small preview for a quick sanity check after enrichment.
    print()

    print(
        songs[
            [
                "artist",
                "title",
                "release_year",
                "genre",
                "listener_count",
                "popularity",
            ]
        ]
        .head(30)
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()