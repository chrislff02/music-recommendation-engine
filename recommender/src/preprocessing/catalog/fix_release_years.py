"""
Improve release-year metadata for the cleaned MusicMatch catalog.

This stage:
1. Searches MusicBrainz again using each song's title & artist ID.
2. Finds the earliest valid release year from exact title matches.
3. Falls back to the existing release year when no better value is found.
4. Adds a decade column for catalog inspection & balancing.
5. Saves the updated catalog for later genre completion/final preparation.
"""

import pandas as pd

from .config import PROCESSED_CATALOG_DIR
from .musicbrainz import (
    search_song_by_title_and_artist,
)


def extract_earliest_release_year(
    recordings,
    expected_title,
):
    """
    Return the earliest valid release year from exact title matches.

    MusicBrainz search results may contain reissues/similarly named
    recordings, so only exact case-insensitive title matches are used.

    Returns None when no suitable release year can be found.
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
                    "",
                )
            )
            .strip()
            .casefold()
        )

        # Ignore results that do not exactly match the expected song title.
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
            # The first four characters are enough for the catalog.
            year = int(
                str(
                    first_release_date
                )[:4]
            )
        except ValueError:
            continue

        # Ignore obviously invalid year values.
        if 1900 <= year <= 2100:
            years.append(year)

    if not years:
        return None

    # Prefer the earliest matching year to reduce the chance of storing
    # a later reissue/remaster date.
    return min(years)


def main():
    """Refresh release years and save the updated catalog stage."""

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

    # Reset the index so progress messages count cleanly from 1 -> N.
    songs = songs.reset_index(
        drop=True
    )

    release_years = []

    total = len(songs)

    # Re-check release years one song at a time using MusicBrainz search.
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

            # If MusicBrainz does not provide a better value,
            # preserve the release year found during enrichment.
            if release_year is None:
                release_year = row.get(
                    "release_year"
                )

        except Exception as error:
            # One failed request should not stop the full catalog update.
            # Preserve the current year when the lookup fails.
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

    # Replace the catalog's release-year column with the improved values.
    songs["release_year"] = (
        release_years
    )

    # Group release years into decades. This is mainly useful for
    # inspecting catalog coverage & balancing songs across eras.
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

    # Show decade coverage so gaps/overrepresented eras are easy to spot.
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

    # Show genre distribution as an additional catalog sanity check.
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