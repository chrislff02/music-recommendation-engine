"""
Fill missing catalog genres using artist-level fallback mappings.

Most genres are discovered & normalized earlier in the catalog pipeline.
This script only fills remaining gaps for well-known artists whose primary
MusicMatch genre is known.

Existing genre values are preserved and only missing entries are updated.
"""

import pandas as pd

from .config import PROCESSED_CATALOG_DIR


# Fallback genre assignments for recognizable artists whose songs may not
# have received a usable genre from MusicBrainz metadata.
# These values are only applied when normalized_genre is currently missing.
ARTIST_GENRE_MAP = {
    # Rock
    "Fleetwood Mac": "Rock",
    "Pink Floyd": "Rock",
    "Queen": "Rock",
    "David Bowie": "Rock",
    "Led Zeppelin": "Rock",
    "The Cure": "Rock",
    "Nirvana": "Rock",
    "Radiohead": "Rock",
    "Green Day": "Rock",
    "Foo Fighters": "Rock",
    "Pearl Jam": "Rock",
    "The Strokes": "Rock",
    "Coldplay": "Rock",
    "The Killers": "Rock",
    "Arctic Monkeys": "Rock",

    # Metal
    "Metallica": "Metal",
    "Linkin Park": "Metal",

    # Pop
    "Michael Jackson": "Pop",
    "Madonna": "Pop",
    "Whitney Houston": "Pop",
    "George Michael": "Pop",
    "ABBA": "Pop",
    "Dua Lipa": "Pop",
    "Billie Eilish": "Pop",
    "Olivia Rodrigo": "Pop",
    "Sabrina Carpenter": "Pop",
    "Harry Styles": "Pop",
    "Tate McRae": "Pop",

    # Hip-Hop
    "Nas": "Hip-Hop",
    "2Pac": "Hip-Hop",
    "The Notorious B.I.G.": "Hip-Hop",
    "Outkast": "Hip-Hop",
    "Eminem": "Hip-Hop",
    "Kanye West": "Hip-Hop",
    "Kendrick Lamar": "Hip-Hop",
    "Drake": "Hip-Hop",
    "Tyler, The Creator": "Hip-Hop",

    # R&B
    "Beyoncé": "R&B",
    "Alicia Keys": "R&B",
    "Frank Ocean": "R&B",
    "SZA": "R&B",
    "Usher": "R&B",
    "Lauryn Hill": "R&B",
    "Marvin Gaye": "R&B",
    "Aretha Franklin": "R&B",
    "Stevie Wonder": "R&B",

    # Electronic
    "Daft Punk": "Electronic",
    "Depeche Mode": "Electronic",
    "Tame Impala": "Electronic",

    # Country
    "Johnny Cash": "Country",
    "Dolly Parton": "Country",
    "Willie Nelson": "Country",
    "Shania Twain": "Country",
    "Chris Stapleton": "Country",

    # Reggae
    "Bob Marley & The Wailers": "Reggae",
    "Jimmy Cliff": "Reggae",
    "Sean Paul": "Reggae",
    "Shaggy": "Reggae",
    "Damian Marley": "Reggae",

    # Latin
    "Shakira": "Latin",
    "Daddy Yankee": "Latin",
    "Juanes": "Latin",
    "J Balvin": "Latin",
    "Karol G": "Latin",

    # Jazz
    "Miles Davis": "Jazz",
}


def main():
    """Fill missing genres and save the genre-completed catalog stage."""

    input_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_final_prototype.csv"
    )

    output_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_final_genres.csv"
    )

    songs = pd.read_csv(
        input_path
    )

    # Count missing genres before applying the artist-level fallback map.
    missing_before = (
        songs["normalized_genre"]
        .isna()
        .sum()
    )

    print(
        f"Missing genres before: "
        f"{missing_before}"
    )

    # Only update songs that still do not have a normalized genre.
    # Existing genre assignments from earlier pipeline stages are preserved.
    missing_mask = (
        songs["normalized_genre"]
        .isna()
    )

    # Map the song's artist name to a fallback genre when one is available.
    # Artists not present in ARTIST_GENRE_MAP remain missing.
    songs.loc[
        missing_mask,
        "normalized_genre",
    ] = (
        songs.loc[
            missing_mask,
            "artist",
        ]
        .map(
            ARTIST_GENRE_MAP
        )
    )

    # Report how many songs still have no genre after the fallback step.
    missing_after = (
        songs["normalized_genre"]
        .isna()
        .sum()
    )

    print(
        f"Missing genres after: "
        f"{missing_after}"
    )

    # Print the final genre distribution so the results can be quickly
    # inspected for unexpected imbalances or missing categories.
    print()
    print("Genre counts:")

    print(
        songs["normalized_genre"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # Save the updated catalog for the final preparation/import stages.
    songs.to_csv(
        output_path,
        index=False,
    )

    print()
    print(
        f"Saved {len(songs)} songs"
    )

    print(
        f"Output: {output_path}"
    )


if __name__ == "__main__":
    main()