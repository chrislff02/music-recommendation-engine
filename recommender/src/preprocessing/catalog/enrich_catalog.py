import math

import pandas as pd

from .config import PROCESSED_CATALOG_DIR
from .musicbrainz import (
    get_recording_details,
    search_song_by_title_and_artist,
)


def extract_genre(recording):
    tags = recording.get(
        "tags",
        [],
    )

    if not tags:
        return None

    valid_tags = [
        tag
        for tag in tags
        if tag.get("name")
    ]

    if not valid_tags:
        return None

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
    cleaned = (
        series
        .fillna(0)
        .clip(lower=0)
    )

    logged = cleaned.apply(
        lambda value: math.log1p(value)
    )

    minimum = logged.min()
    maximum = logged.max()

    if maximum == minimum:
        return pd.Series(
            [0.5] * len(logged),
            index=logged.index,
        )

    return (
        logged - minimum
    ) / (
        maximum - minimum
    )


def extract_earliest_release_year(
    recordings,
    expected_title,
):
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

        # Only use exact title matches.
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
            year = int(
                str(
                    first_release_date
                )[:4]
            )
        except ValueError:
            continue

        if 1900 <= year <= 2100:
            years.append(
                year
            )

    if not years:
        return None

    return min(years)


def main():
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

    songs = songs.reset_index(
        drop=True
    )

    release_years = []
    genres = []

    total = len(songs)

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
            recording = (
                get_recording_details(
                    recording_mbid
                )
            )

            search_results = (
                search_song_by_title_and_artist(
                    row["title"],
                    row["artist_mbid"],
                )
            )

            release_year = (
                extract_earliest_release_year(
                    search_results,
                    row["title"],
                )
            )

            genre = (
                extract_genre(
                    recording
                )
            )

        except Exception as error:
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

    songs["release_year"] = (
        release_years
    )

    songs["genre"] = (
        genres
    )

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