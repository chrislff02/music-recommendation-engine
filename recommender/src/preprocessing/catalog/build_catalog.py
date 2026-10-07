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
    rows = []
    artist_matches = []

    for artist_name in SEED_ARTISTS:
        print(f"Finding {artist_name}...")

        try:
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

    if songs.empty:
        print(
            "No songs collected."
        )
        return

    songs = songs.dropna(
        subset=[
            "recording_mbid",
            "title",
            "artist",
        ]
    )

    songs = songs.drop_duplicates(
        subset=[
            "recording_mbid",
        ]
    )

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