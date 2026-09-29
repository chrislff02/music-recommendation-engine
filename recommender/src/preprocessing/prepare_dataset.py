from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def main():
    tracks_path = RAW_DATA_DIR / "tracks.csv"
    echonest_path = RAW_DATA_DIR / "echonest.csv"

    tracks = pd.read_csv(
        tracks_path,
        header=[0, 1],
        index_col=0,
    )

    echonest = pd.read_csv(
        echonest_path,
        header=[0, 1, 2],
        index_col=0,
    )

    # Keep only tracks that have Echo Nest audio features.
    track_ids = tracks.index.intersection(echonest.index)

    tracks = tracks.loc[track_ids]
    echonest = echonest.loc[track_ids]

    songs = pd.DataFrame(index=track_ids)

    # Basic song metadata
    songs["title"] = tracks[("track", "title")]
    songs["artist"] = tracks[("artist", "name")]
    songs["genre"] = tracks[("track", "genre_top")]
    songs["duration"] = tracks[("track", "duration")]
    songs["listens"] = tracks[("track", "listens")]

    # Audio characteristics used by the recommendation engine
    songs["acousticness"] = echonest[
        ("echonest", "audio_features", "acousticness")
    ]
    songs["danceability"] = echonest[
        ("echonest", "audio_features", "danceability")
    ]
    songs["energy"] = echonest[
        ("echonest", "audio_features", "energy")
    ]
    songs["instrumentalness"] = echonest[
        ("echonest", "audio_features", "instrumentalness")
    ]
    songs["liveness"] = echonest[
        ("echonest", "audio_features", "liveness")
    ]
    songs["speechiness"] = echonest[
        ("echonest", "audio_features", "speechiness")
    ]
    songs["tempo"] = echonest[
        ("echonest", "audio_features", "tempo")
    ]
    songs["valence"] = echonest[
        ("echonest", "audio_features", "valence")
    ]

    # Give the FMA track ID an explicit column name.
    songs.index.name = "external_id"

    print("=== Cleaned dataset ===")
    print(f"Rows before cleaning: {len(songs)}")

    # A usable song needs at least a title and artist.
    songs = songs.dropna(subset=["title", "artist"])

    # Log-transform listens so a small number of extremely popular
    # tracks do not dominate the popularity scale.
    log_listens = np.log1p(songs["listens"])

    min_listens = log_listens.min()
    max_listens = log_listens.max()

    # Normalize popularity to a value between 0 and 1.
    if max_listens == min_listens:
        songs["popularity"] = 0.0
    else:
        songs["popularity"] = (
            (log_listens - min_listens)
            / (max_listens - min_listens)
        )

    print(f"Rows after cleaning: {len(songs)}")
    print()

    print("First 5 rows:")
    print(songs.head())
    print()

    print("Missing values:")
    print(songs.isna().sum())
    print()

    print("Popularity summary:")
    print(songs["popularity"].describe())

    # Make sure the processed-data folder exists.
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    output_path = PROCESSED_DATA_DIR / "songs.csv"
    songs.to_csv(output_path)

    print()
    print("Saved cleaned dataset to:")
    print(output_path)


if __name__ == "__main__":
    main()