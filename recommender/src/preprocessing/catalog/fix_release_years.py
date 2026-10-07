import pandas as pd

from .config import PROCESSED_CATALOG_DIR
from .musicbrainz import (
    search_song_by_title_and_artist,
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
                    "",
                )
            )
            .strip()
            .casefold()
        )

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
            years.append(year)

    if not years:
        return None

    return min(years)


def main():
    input_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_clean.csv"
    )

    output_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_final_prototype.csv"
    )

    songs = pd.read_csv(
        input_path
    )

    songs = songs.reset_index(
        drop=True
    )

    release_years = []

    total = len(songs)

    for index, row in songs.iterrows():
        print(
            f"[{index + 1}/{total}] "
            f"{row['artist']} - "
            f"{row['title']}"
        )

        try:
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

            # If MusicBrainz cannot find a better
            # year, keep the existing year.
            if release_year is None:
                release_year = row.get(
                    "release_year"
                )

        except Exception as error:
            print(
                "  Failed to update year:",
                error,
            )

            release_year = row.get(
                "release_year"
            )

        release_years.append(
            release_year
        )

    songs["release_year"] = (
        release_years
    )

    # Add decade for catalog balancing.
    songs["decade"] = (
        pd.to_numeric(
            songs["release_year"],
            errors="coerce",
        )
        // 10
        * 10
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

    print()
    print("Songs by decade:")

    print(
        songs["decade"]
        .value_counts(
            dropna=False
        )
        .sort_index()
        .to_string()
    )

    print()
    print("Songs by genre:")

    print(
        songs["normalized_genre"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )


if __name__ == "__main__":
    main()