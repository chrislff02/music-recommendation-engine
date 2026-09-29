from pathlib import Path
import os

import pandas as pd
import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
SERVER_ENV_PATH = PROJECT_ROOT / "server" / ".env"


def main():
    load_dotenv(SERVER_ENV_PATH)

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL was not found.")

    songs_path = PROCESSED_DATA_DIR / "songs.csv"

    songs = pd.read_csv(songs_path)

    print(f"Songs to import: {len(songs)}")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            artist_ids = {}
            genre_ids = {}

            inserted_songs = 0

            for _, row in songs.iterrows():
                artist_name = row["artist"]
                genre_name = row["genre"]

                # Find or create artist
                if artist_name not in artist_ids:
                    cur.execute(
                        """
                        INSERT INTO "Artist" (name)
                        VALUES (%s)
                        ON CONFLICT (name)
                        DO UPDATE SET name = EXCLUDED.name
                        RETURNING id
                        """,
                        (artist_name,),
                    )

                    artist_ids[artist_name] = cur.fetchone()[0]

                artist_id = artist_ids[artist_name]

                # Find or create genre
                genre_id = None

                if pd.notna(genre_name):
                    if genre_name not in genre_ids:
                        cur.execute(
                            """
                            INSERT INTO "Genre" (name)
                            VALUES (%s)
                            ON CONFLICT (name)
                            DO UPDATE SET name = EXCLUDED.name
                            RETURNING id
                            """,
                            (genre_name,),
                        )

                        genre_ids[genre_name] = cur.fetchone()[0]

                    genre_id = genre_ids[genre_name]

                # Insert song
                cur.execute(
                    """
                    INSERT INTO "Song" (
                        title,
                        "externalId",
                        "artistId",
                        "genreId",
                        tempo,
                        energy,
                        danceability,
                        valence,
                        acousticness,
                        instrumentalness,
                        speechiness,
                        liveness,
                        popularity,
                        duration,
                        "updatedAt"
                    )
                    VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT ("externalId")
                    DO NOTHING
                    """,
                    (
                        row["title"],
                        str(row["external_id"]),
                        artist_id,
                        genre_id,
                        row["tempo"],
                        row["energy"],
                        row["danceability"],
                        row["valence"],
                        row["acousticness"],
                        row["instrumentalness"],
                        row["speechiness"],
                        row["liveness"],
                        row["popularity"],
                        row["duration"],
                    ),
                )

                inserted_songs += cur.rowcount

            conn.commit()

    print()
    print("Import complete.")
    print(f"Artists created/used: {len(artist_ids)}")
    print(f"Genres created/used: {len(genre_ids)}")
    print(f"Songs inserted: {inserted_songs}")


if __name__ == "__main__":
    main()