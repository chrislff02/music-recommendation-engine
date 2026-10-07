import pandas as pd

from .config import PROCESSED_CATALOG_DIR


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

    missing_before = (
        songs["normalized_genre"]
        .isna()
        .sum()
    )

    print(
        f"Missing genres before: "
        f"{missing_before}"
    )

    missing_mask = (
        songs["normalized_genre"]
        .isna()
    )

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

    missing_after = (
        songs["normalized_genre"]
        .isna()
        .sum()
    )

    print(
        f"Missing genres after: "
        f"{missing_after}"
    )

    print()
    print("Genre counts:")

    print(
        songs["normalized_genre"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

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