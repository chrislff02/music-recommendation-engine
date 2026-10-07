import re

import pandas as pd

from .config import PROCESSED_CATALOG_DIR


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
    if pd.isna(value):
        return None

    genre = str(value).strip().casefold()

    if genre in GENRE_MAP:
        return GENRE_MAP[genre]

    # Allow partial matches for tags such as
    # "alternative hip hop" or "progressive rock".
    for raw_genre, clean_genre in GENRE_MAP.items():
        if raw_genre in genre:
            return clean_genre

    return None


def is_unwanted_version(title):
    if pd.isna(title):
        return True

    normalized_title = str(title).casefold()

    return any(
        re.search(
            pattern,
            normalized_title,
        )
        for pattern in UNWANTED_TITLE_PATTERNS
    )


def main():
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

    songs["normalized_genre"] = (
        songs["genre"]
        .apply(normalize_genre)
    )

    # ----------------------------------------------
    # REMOVE NON-STANDARD VERSIONS
    # ----------------------------------------------

    songs["unwanted_version"] = (
        songs["title"]
        .apply(is_unwanted_version)
    )

    songs = songs[
        ~songs["unwanted_version"]
    ].copy()

    # ----------------------------------------------
    # REMOVE DUPLICATES
    # ----------------------------------------------

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

    songs = songs.drop(
        columns=[
            "unwanted_version",
            "title_key",
            "artist_key",
        ]
    )

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

    print()

    print("Normalized genre counts:")

    print(
        songs["normalized_genre"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

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