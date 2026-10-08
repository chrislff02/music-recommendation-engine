"""
Clean & normalize the enriched MusicMatch catalog.

This stage:
1. Normalizes raw genre tags into the smaller set of genres used by MusicMatch.
2. Removes alternate/non-standard song versions such as live tracks,
   demos, remixes, instrumentals & karaoke versions.
3. Removes duplicate artist/title combinations.
4. Keeps the most-listened-to version when duplicates exist.
5. Saves the cleaned catalog for later pipeline stages.
"""

import re

import pandas as pd

from .config import PROCESSED_CATALOG_DIR


# Map raw genre labels & common subgenres into the simplified
# genre categories used by the application.
GENRE_MAP = {
    # Rock
    "rock": "Rock",
    "alternative rock": "Rock",
    "indie rock": "Rock",
    "progressive rock": "Rock",
    "classic rock": "Rock",
    "hard rock": "Rock",
    "art rock": "Rock",
    "garage rock": "Rock",
    "psychedelic rock": "Rock",

    # Pop
    "pop": "Pop",
    "pop rock": "Pop",
    "dance pop": "Pop",
    "synthpop": "Pop",
    "electropop": "Pop",

    # Hip-Hop
    "hip hop": "Hip-Hop",
    "hip-hop": "Hip-Hop",
    "rap": "Hip-Hop",
    "gangsta rap": "Hip-Hop",
    "conscious hip hop": "Hip-Hop",
    "alternative hip hop": "Hip-Hop",

    # R&B
    "r&b": "R&B",
    "rhythm and blues": "R&B",
    "contemporary r&b": "R&B",
    "neo soul": "R&B",
    "soul": "R&B",

    # Electronic
    "electronic": "Electronic",
    "electronica": "Electronic",
    "house": "Electronic",
    "techno": "Electronic",
    "disco": "Electronic",
    "dance": "Electronic",

    # Metal
    "metal": "Metal",
    "heavy metal": "Metal",
    "thrash metal": "Metal",
    "alternative metal": "Metal",

    # Other
    "jazz": "Jazz",
    "blues": "Blues",
    "folk": "Folk",
    "country": "Country",
    "reggae": "Reggae",
    "classical": "Classical",
    "latin": "Latin",
}


# Title patterns that usually indicate an alternate or non-standard
# version rather than the main studio recording.
UNWANTED_TITLE_PATTERNS = [
    r"\blive\b",
    r"\bdemo\b",
    r"\bremix\b",
    r"\bradio edit\b",
    r"\bshort radio edit\b",
    r"\bclub mix\b",
    r"\bskit\b",
    r"\binstrumental\b",
    r"\bkaraoke\b",
]


def normalize_genre(value):
    """
    Convert a raw genre/tag value into one of MusicMatch's supported genres.
    Exact matches are checked first. If no exact match exists, the function
    looks for known genre names inside longer tags such as
    "alternative hip hop"/"progressive rock".
    Returns None when the genre cannot be mapped.
    """
    if pd.isna(value):
        return None

    genre = str(value).strip().casefold()

    # Prefer exact matches when possible.
    if genre in GENRE_MAP:
        return GENRE_MAP[genre]

    # Allow partial matches for longer tags/subgenres.
    for raw_genre, clean_genre in GENRE_MAP.items():
        if raw_genre in genre:
            return clean_genre

    return None


def is_unwanted_version(title):
    """
    Return True when a song title appears to be an alternate version.
    Missing titles are also treated as unusable so they can be removed
    during the cleaning stage.
    """
    if pd.isna(title):
        return True

    normalized_title = str(title).casefold()

    # Match the title against known markers such as "live"/"remix"
    # "instrumental"/"karaoke".
    return any(
        re.search(
            pattern,
            normalized_title,
        )
        for pattern in UNWANTED_TITLE_PATTERNS
    )


def main():
    """Clean the enriched catalog & save the next pipeline stage."""

    input_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_enriched.csv"
    )

    output_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_clean.csv"
    )

    songs = pd.read_csv(
        input_path
    )

    print(
        f"Starting songs: {len(songs)}"
    )


    # ----------------------------------------------
    # CLEAN GENRES
    # ----------------------------------------------

    # Convert raw genre/tag values into the simplified genre set used
    # by the frontend, database & recommendation engine.
    songs["normalized_genre"] = (
        songs["genre"]
        .apply(normalize_genre)
    )


    # ----------------------------------------------
    # REMOVE NON-STANDARD VERSIONS
    # ----------------------------------------------

    # Flag alternate versions such as live recordings/remixes
    # demos/instrumentals.
    songs["unwanted_version"] = (
        songs["title"]
        .apply(is_unwanted_version)
    )

    # Keep only the standard/main recording candidates.
    songs = songs[
        ~songs["unwanted_version"]
    ].copy()


    # ----------------------------------------------
    # REMOVE DUPLICATES
    # ----------------------------------------------

    # Create normalized comparison keys so capitalization & surrounding
    # whitespace do not cause the same song to appear multiple times.
    songs["title_key"] = (
        songs["title"]
        .astype(str)
        .str.casefold()
        .str.strip()
    )

    songs["artist_key"] = (
        songs["artist"]
        .astype(str)
        .str.casefold()
        .str.strip()
    )

    # When the same artist/title pair appears more than once, keep the
    # version with the highest listener count.
    songs = (
        songs
        .sort_values(
            by="listener_count",
            ascending=False,
        )
        .drop_duplicates(
            subset=[
                "artist_key",
                "title_key",
            ],
            keep="first",
        )
    )


    # ----------------------------------------------
    # CLEAN TEMPORARY COLUMNS
    # ----------------------------------------------

    # These helper columns are only needed during cleaning & should
    # not be carried into later pipeline stages.
    songs = songs.drop(
        columns=[
            "unwanted_version",
            "title_key",
            "artist_key",
        ]
    )

    # Save the cleaned catalog for the next processing step.
    songs.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Clean songs: {len(songs)}"
    )

    print(
        f"Output: {output_path}"
    )

    # Print genre counts to make it easy to inspect how well the
    # normalization step worked.
    print()
    print("Normalized genre counts:")

    print(
        songs["normalized_genre"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # Print a preview for a quick manual sanity check.
    print()

    print(
        songs[
            [
                "artist",
                "title",
                "release_year",
                "genre",
                "normalized_genre",
                "popularity",
            ]
        ]
        .head(40)
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()