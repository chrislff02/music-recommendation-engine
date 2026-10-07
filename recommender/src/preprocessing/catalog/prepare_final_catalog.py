import pandas as pd

from .config import PROCESSED_CATALOG_DIR


def main():
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
    #
    # If multiple MusicBrainz recordings represent the
    # same song, keep the most popular one.
    # --------------------------------------------------

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

    songs["release_year"] = pd.to_numeric(
        songs["release_year"],
        errors="coerce",
    ).astype("Int64")

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
    #
    # Keep genuinely unknown genres as null instead
    # of assigning possibly incorrect genres.
    # --------------------------------------------------

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
    #
    # ListenBrainz gave us milliseconds.
    # Store seconds for the application/database.
    # --------------------------------------------------

    if "duration_ms" in songs.columns:
        songs["duration"] = (
            pd.to_numeric(
                songs["duration_ms"],
                errors="coerce",
            )
            / 1000.0
        )
    else:
        songs["duration"] = pd.NA

    # --------------------------------------------------
    # DATABASE-FRIENDLY COLUMN NAMES
    # --------------------------------------------------

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

    print()
    print("Missing values:")

    print(
        final_songs
        .isna()
        .sum()
        .to_string()
    )

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

    print()
    print("Genre counts:")

    print(
        final_songs["genre"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

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