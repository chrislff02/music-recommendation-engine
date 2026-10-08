"""
Build v1 of the MusicMatch song catalog.

The script:
1. Looks up each seed artist in MusicBrainz.
2. Uses the matched MusicBrainz artist ID to fetch popular recordings
   from ListenBrainz.
3. Combines the returned metadata into a single song table.
4. Removes incomplete and duplicate recordings.
5. Sorts songs by listener/listen counts.
6. Saves the prototype catalog for later enrichment steps.
"""

import json

import pandas as pd

from .artists import SEED_ARTISTS
from .config import (
    PROCESSED_CATALOG_DIR,
    RAW_CATALOG_DIR,
)
from .listenbrainz import (
    get_top_recordings_for_artist,
)
from .musicbrainz import (
    find_artist,
)


def main():
    """Build and save the initial MusicBrainz/ListenBrainz catalog."""

    # Final song rows that will become the prototype catalog.
    rows = []

    # Save the MusicBrainz artist matches separately so they can be
    # inspected later without repeating every artist lookup.
    artist_matches = []

    # Process every artist selected for the catalog seed list.
    for artist_name in SEED_ARTISTS:
        print(f"Finding {artist_name}...")

        try:
            # Resolve the human-readable artist name to a MusicBrainz artist.
            artist = find_artist(
                artist_name
            )
        except Exception as error:
            print(
                "  Failed to load "
                "MusicBrainz artist:",
                error,
            )
            continue

        # Skip seed artists that could not be matched confidently.
        if artist is None:
            print(
                "  No MusicBrainz match."
            )
            continue

        artist_matches.append(
            artist
        )

        print(
            f"  Found {artist['name']} "
            f"({artist['mbid']})"
        )

        try:
            # Use the MusicBrainz artist ID to retrieve the artist's
            # most-listened-to recordings from ListenBrainz.
            recordings = (
                get_top_recordings_for_artist(
                    artist["mbid"]
                )
            )
        except Exception as error:
            print(
                "  Failed to load "
                "ListenBrainz recordings:",
                error,
            )
            continue

        print(
            f"  {len(recordings)} recordings"
        )

        # Convert each ListenBrainz recording into the normalized columns
        # used by the rest of the catalog-processing pipeline.
        for recording in recordings:
            rows.append(
                {
                    "recording_mbid": (
                        recording.get(
                            "recording_mbid"
                        )
                    ),
                    "title": (
                        recording.get(
                            "recording_name"
                        )
                    ),
                    "artist_mbid": (
                        artist["mbid"]
                    ),
                    "artist": (
                        recording.get(
                            "artist_name"
                        )
                        or artist["name"]
                    ),
                    "release_mbid": (
                        recording.get(
                            "release_mbid"
                        )
                    ),
                    "release_name": (
                        recording.get(
                            "release_name"
                        )
                    ),
                    "listen_count": (
                        recording.get(
                            "total_listen_count"
                        )
                    ),
                    "listener_count": (
                        recording.get(
                            "total_user_count"
                        )
                    ),
                    "duration_ms": (
                        recording.get(
                            "length"
                        )
                    ),
                }
            )

    # Save the resolved MusicBrainz artist matches as raw reference data.
    raw_path = (
        RAW_CATALOG_DIR
        / "artist_matches.json"
    )

    raw_path.write_text(
        json.dumps(
            artist_matches,
            indent=2,
        ),
        encoding="utf-8",
    )

    songs = pd.DataFrame(
        rows
    )

    # Stop early if none of the seed artists produced usable recordings.
    if songs.empty:
        print(
            "No songs collected."
        )
        return

    # Core identifiers are required by later enrichment/import steps.
    songs = songs.dropna(
        subset=[
            "recording_mbid",
            "title",
            "artist",
        ]
    )

    # MusicBrainz recording IDs identify unique recordings, keep only
    # one row per recording if ListenBrainz returned duplicates.
    songs = songs.drop_duplicates(
        subset=[
            "recording_mbid",
        ]
    )

    # Put the most widely listened-to tracks first so the prototype
    # catalog favors recognizable songs.
    songs = songs.sort_values(
        by=[
            "listener_count",
            "listen_count",
        ],
        ascending=[
            False,
            False,
        ],
        na_position="last",
    )

    # This prototype becomes the input for the later enrichment,
    # cleaning, genre & final preparation stages.
    output_path = (
        PROCESSED_CATALOG_DIR
        / "catalog_prototype.csv"
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

    # Print a small preview so the script can be quickly sanity-checked
    # after a catalog build finishes.
    print()
    print(
        songs[
            [
                "artist",
                "title",
                "listener_count",
                "listen_count",
            ]
        ]
        .head(30)
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()