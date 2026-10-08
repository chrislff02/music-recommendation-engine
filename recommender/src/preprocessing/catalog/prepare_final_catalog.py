"""
Prepare the final MusicMatch catalog for PostgreSQL import.

This is the last catalog-processing stage before database import.

The script:
1. Removes rows missing required identifiers.
2. Cleans basic text fields.
3. Removes duplicate MusicBrainz recordings.
4. Removes duplicate artist/title combinations.
5. Validates release years.
6. Preserves unknown genres as null values.
7. Cleans popularity and count fields.
8. Converts duration from milliseconds to seconds.
9. Renames columns to match the database model.
10. Saves the final database-ready catalog.
"""

import pandas as pd

from .config import PROCESSED_CATALOG_DIR


def main():
    """Create & save the final database-ready MusicMatch catalog."""

    input_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_final_genres.csv"
    )

    output_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_ready_for_db.csv"
    )

    songs = pd.read_csv(
        input_path
    )

    print(
        f"Starting songs: {len(songs)}"
    )


    # --------------------------------------------------
    # KEEP ONLY ROWS WITH REQUIRED IDENTIFIERS
    # --------------------------------------------------

    # Every imported song must have a MusicBrainz recording ID,
    # title & artist so it can be identified consistently.
    songs = songs.dropna(
        subset=[
            "recording_mbid",
            "title",
            "artist",
        ]
    ).copy()


    # --------------------------------------------------
    # CLEAN BASIC TEXT FIELDS
    # --------------------------------------------------

    # Remove surrounding whitespace from core text values so equivalent
    # songs/artists are compared consistently during deduplication.
    songs["title"] = (
        songs["title"]
        .astype(str)
        .str.strip()
    )

    songs["artist"] = (
        songs["artist"]
        .astype(str)
        .str.strip()
    )

    songs["recording_mbid"] = (
        songs["recording_mbid"]
        .astype(str)
        .str.strip()
    )


    # --------------------------------------------------
    # REMOVE DUPLICATE MUSICBRAINZ RECORDINGS
    # --------------------------------------------------

    # MusicBrainz recording IDs should uniquely identify recordings.
    # If duplicate IDs remain, keep the row with the most listeners.
    songs = (
        songs
        .sort_values(
            by="listener_count",
            ascending=False,
            na_position="last",
        )
        .drop_duplicates(
            subset=[
                "recording_mbid",
            ],
            keep="first",
        )
        .copy()
    )


    # --------------------------------------------------
    # REMOVE DUPLICATE ARTIST + TITLE COMBINATIONS
    # --------------------------------------------------

    # Different MusicBrainz recordings can sometimes represent the
    # same song. Keep only the most-listened-to version.
    # Create case-insensitive comparison keys for duplicate detection.
    songs["title_key"] = (
        songs["title"]
        .str.casefold()
    )

    songs["artist_key"] = (
        songs["artist"]
        .str.casefold()
    )

    songs = (
        songs
        .sort_values(
            by="listener_count",
            ascending=False,
            na_position="last",
        )
        .drop_duplicates(
            subset=[
                "artist_key",
                "title_key",
            ],
            keep="first",
        )
        .copy()
    )


    # --------------------------------------------------
    # RELEASE YEAR
    # --------------------------------------------------

    # Convert release years to nullable integers.
    songs["release_year"] = pd.to_numeric(
        songs["release_year"],
        errors="coerce",
    ).astype("Int64")

    # Treat clearly invalid years as missing instead of importing
    # incorrect values into PostgreSQL.
    invalid_year = (
        songs["release_year"].notna()
        & (
            (songs["release_year"] < 1900)
            | (songs["release_year"] > 2100)
        )
    )

    songs.loc[
        invalid_year,
        "release_year",
    ] = pd.NA


    # --------------------------------------------------
    # GENRE
    # --------------------------------------------------

    # Keep genuinely unknown genres as null instead
    # of assigning possibly incorrect genres.
    # Normalize string placeholders that should really be missing values.
    songs["normalized_genre"] = (
        songs["normalized_genre"]
        .replace(
            {
                "": pd.NA,
                "None": pd.NA,
                "nan": pd.NA,
            }
        )
    )


    # --------------------------------------------------
    # POPULARITY
    # --------------------------------------------------

    # Ensure popularity is numeric & remains within the 0-1 range
    # expected by the recommendation engine.
    songs["popularity"] = pd.to_numeric(
        songs["popularity"],
        errors="coerce",
    )

    songs["popularity"] = (
        songs["popularity"]
        .clip(
            lower=0.0,
            upper=1.0,
        )
    )


    # --------------------------------------------------
    # LISTEN COUNTS
    # --------------------------------------------------

    # Convert listen statistics to nullable integers for database storage.
    songs["listen_count"] = pd.to_numeric(
        songs["listen_count"],
        errors="coerce",
    ).astype("Int64")

    songs["listener_count"] = pd.to_numeric(
        songs["listener_count"],
        errors="coerce",
    ).astype("Int64")


    # --------------------------------------------------
    # DURATION
    # --------------------------------------------------

    # ListenBrainz provides duration in milliseconds.
    # Store seconds because that is what the application/database uses.
    if "duration_ms" in songs.columns:
        songs["duration"] = (
            pd.to_numeric(
                songs["duration_ms"],
                errors="coerce",
            )
            / 1000.0
        )
    else:
        # Preserve the expected output column even when duration
        # metadata is unavailable.
        songs["duration"] = pd.NA


    # --------------------------------------------------
    # DATABASE-FRIENDLY COLUMN NAMES
    # --------------------------------------------------

    # Rename processed catalog fields to match the PostgreSQL/Prisma model.
    songs["musicBrainzId"] = (
        songs["recording_mbid"]
    )

    songs["artistMusicBrainzId"] = (
        songs["artist_mbid"]
    )

    songs["genre"] = (
        songs["normalized_genre"]
    )

    songs["releaseYear"] = (
        songs["release_year"]
    )

    songs["listenCount"] = (
        songs["listen_count"]
    )

    songs["listenerCount"] = (
        songs["listener_count"]
    )


    # --------------------------------------------------
    # FINAL DATABASE COLUMNS
    # --------------------------------------------------

    # Keep only the fields required by import_to_db.py & the current
    # Artist/Song database models.
    final_columns = [
        "musicBrainzId",
        "title",
        "artist",
        "artistMusicBrainzId",
        "genre",
        "releaseYear",
        "listenCount",
        "listenerCount",
        "popularity",
        "duration",
    ]

    final_songs = (
        songs[
            final_columns
        ]
        .reset_index(
            drop=True
        )
    )


    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    final_songs.to_csv(
        output_path,
        index=False,
    )


    # --------------------------------------------------
    # REPORT
    # --------------------------------------------------

    print()
    print(
        f"Final songs: {len(final_songs)}"
    )

    print(
        f"Output: {output_path}"
    )

    # Report missing metadata so the final catalog can be sanity-checked.
    print()
    print("Missing values:")

    print(
        final_songs
        .isna()
        .sum()
        .to_string()
    )

    # These checks should normally be zero after the deduplication steps.
    print()
    print(
        "Duplicate MusicBrainz IDs:",
        final_songs[
            "musicBrainzId"
        ].duplicated().sum(),
    )

    print(
        "Duplicate artist/title pairs:",
        final_songs.duplicated(
            subset=[
                "artist",
                "title",
            ]
        ).sum(),
    )

    # Show the final genre distribution to make catalog balance easy
    # to inspect before importing into PostgreSQL.
    print()
    print("Genre counts:")

    print(
        final_songs["genre"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # Print a small preview of the database-ready output.
    print()
    print("Sample:")

    print(
        final_songs
        .head(25)
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()