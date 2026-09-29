from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def main():
    tracks_path = RAW_DATA_DIR / "tracks.csv"
    genres_path = RAW_DATA_DIR / "genres.csv"
    echonest_path = RAW_DATA_DIR / "echonest.csv"
    features_path = RAW_DATA_DIR / "features.csv"

    print("=== File locations ===")
    print(f"tracks:   {tracks_path}")
    print(f"genres:   {genres_path}")
    print(f"echonest: {echonest_path}")
    print(f"features: {features_path}")
    print()

    tracks = pd.read_csv(tracks_path, header=[0, 1], index_col=0)
    genres = pd.read_csv(genres_path, index_col=0)
    echonest = pd.read_csv(echonest_path, header=[0, 1, 2], index_col=0)
    features = pd.read_csv(features_path, header=[0, 1, 2], index_col=0)

    datasets = {
        "tracks": tracks,
        "genres": genres,
        "echonest": echonest,
        "features": features,
    }

    for name, dataframe in datasets.items():
        print(f"=== {name.upper()} ===")
        print(f"Shape: {dataframe.shape}")
        print()
        print("Columns:")
        print(dataframe.columns)
        print()
        print("First 3 rows:")
        print(dataframe.head(3))
        print()
        print("-" * 80)
        print()

    print("=== RECOMMENDER DATA INSPECTION ===")

    track_columns = [
        ("track", "title"),
        ("track", "genre_top"),
        ("track", "duration"),
        ("artist", "name"),
    ]

    audio_columns = [
        ("echonest", "audio_features", "acousticness"),
        ("echonest", "audio_features", "danceability"),
        ("echonest", "audio_features", "energy"),
        ("echonest", "audio_features", "instrumentalness"),
        ("echonest", "audio_features", "liveness"),
        ("echonest", "audio_features", "speechiness"),
        ("echonest", "audio_features", "tempo"),
        ("echonest", "audio_features", "valence"),
    ]

    print()
    print("Track fields:")
    print(tracks[track_columns].head())

    print()
    print("Audio fields:")
    print(echonest[audio_columns].head())

    print()
    print("Missing values in track fields:")
    print(tracks[track_columns].isna().sum())

    print()
    print("Missing values in audio fields:")
    print(echonest[audio_columns].isna().sum())

    print()
    print("Track ID overlap:")
    overlap = tracks.index.intersection(echonest.index)

    print(f"tracks.csv rows: {len(tracks)}")
    print(f"echonest.csv rows: {len(echonest)}")
    print(f"IDs present in both: {len(overlap)}")

    print()
    print("Genre counts for Echo Nest subset:")
    echonest_tracks = tracks.loc[overlap]

    print(
        echonest_tracks[("track", "genre_top")]
        .value_counts(dropna=False)
        .head(25)
    )


if __name__ == "__main__":
    main()
    