from pathlib import Path
import os

import pandas as pd
import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]

CATALOG_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "catalog"
    / "catalog_ready_for_db.csv"
)

SERVER_ENV_PATH = (
    PROJECT_ROOT
    / "server"
    / ".env"
)


def clean_optional_int(value):
    if pd.isna(value):
        return None

    return int(value)


def clean_optional_float(value):
    if pd.isna(value):
        return None

    return float(value)


def clean_optional_text(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def main():
    load_dotenv(
        SERVER_ENV_PATH
    )

    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL was not found."
        )

    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Catalog file was not found: "
            f"{CATALOG_PATH}"
        )

    songs = pd.read_csv(
        CATALOG_PATH
    )

    print(
        f"Songs to import: {len(songs)}"
    )

    print()
    print(
        "WARNING:"
    )
    print(
        "This will replace the existing song catalog."
    )
    print(
        "Old ratings and favorite-artist selections "
        "will be deleted because they reference "
        "the old songs/artists."
    )
    print(
        "Users and favorite genres will be preserved."
    )

    confirmation = input(
        "\nType REPLACE to continue: "
    )

    if confirmation != "REPLACE":
        print(
            "Import cancelled."
        )
        return

    with psycopg.connect(
        database_url
    ) as conn:
        with conn.cursor() as cur:

            # ------------------------------------------
            # REMOVE OLD CATALOG-DEPENDENT DATA
            # ------------------------------------------

            print()
            print(
                "Removing old catalog data..."
            )

            cur.execute(
                """
                DELETE FROM "Rating"
                """
            )

            cur.execute(
                """
                DELETE FROM "UserFavoriteArtist"
                """
            )

            cur.execute(
                """
                DELETE FROM "Song"
                """
            )

            cur.execute(
                """
                DELETE FROM "Artist"
                """
            )

            # ------------------------------------------
            # PRELOAD EXISTING GENRES
            # ------------------------------------------

            cur.execute(
                """
                SELECT id, name
                FROM "Genre"
                """
            )

            genre_ids = {
                name: genre_id
                for genre_id, name
                in cur.fetchall()
            }

            artist_ids = {}
            used_artist_mbids = {}


            inserted_artists = 0
            inserted_genres = 0
            inserted_songs = 0

            # ------------------------------------------
            # IMPORT SONGS
            # ------------------------------------------

            for index, row in songs.iterrows():

                artist_name = (
                    str(
                        row["artist"]
                    ).strip()
                )

                artist_mbid = (
                    clean_optional_text(
                        row[
                            "artistMusicBrainzId"
                        ]
                    )
                )

                genre_name = (
                    clean_optional_text(
                        row["genre"]
                    )
                )

                # --------------------------------------
                # FIND OR CREATE ARTIST
                # --------------------------------------

                if artist_name not in artist_ids:
                    safe_artist_mbid = artist_mbid

                    if (
                        artist_mbid is not None
                        and artist_mbid in used_artist_mbids
                        and used_artist_mbids[artist_mbid] != artist_name
                    ):
                        safe_artist_mbid = None

                    cur.execute(
                        """
                        INSERT INTO "Artist" (
                            name,
                            "musicBrainzId"
                        )
                        VALUES (
                            %s,
                            %s
                        )
                        ON CONFLICT (name)
                        DO UPDATE SET
                            "musicBrainzId" =
                                COALESCE(
                                    "Artist"."musicBrainzId",
                                    EXCLUDED."musicBrainzId"
                                )
                        RETURNING
                            id,
                            "musicBrainzId"
                        """,
                        (
                            artist_name,
                            safe_artist_mbid,
                        ),
                    )

                    artist_id, stored_mbid = (
                        cur.fetchone()
                    )

                    artist_ids[
                        artist_name
                    ] = artist_id

                    if stored_mbid is not None:
                        used_artist_mbids[
                            stored_mbid
                        ] = artist_name

                    inserted_artists += 1

                artist_id = artist_ids[
                    artist_name
                ]

                # --------------------------------------
                # FIND OR CREATE GENRE
                # --------------------------------------

                genre_id = None

                if genre_name is not None:

                    if genre_name not in genre_ids:

                        cur.execute(
                            """
                            INSERT INTO "Genre" (
                                name
                            )
                            VALUES (
                                %s
                            )
                            ON CONFLICT (name)
                            DO UPDATE SET
                                name = EXCLUDED.name
                            RETURNING id
                            """,
                            (
                                genre_name,
                            ),
                        )

                        genre_id = (
                            cur.fetchone()[0]
                        )

                        genre_ids[
                            genre_name
                        ] = genre_id

                        inserted_genres += 1

                    else:
                        genre_id = (
                            genre_ids[
                                genre_name
                            ]
                        )

                # --------------------------------------
                # INSERT SONG
                # --------------------------------------

                cur.execute(
                    """
                    INSERT INTO "Song" (
                        title,
                        "externalId",
                        "musicBrainzId",
                        "releaseYear",
                        "listenCount",
                        "listenerCount",
                        "artistId",
                        "genreId",
                        popularity,
                        duration,
                        "updatedAt"
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT ("musicBrainzId")
                    DO NOTHING
                    """,
                    (
                        str(
                            row["title"]
                        ).strip(),

                        None,

                        clean_optional_text(
                            row[
                                "musicBrainzId"
                            ]
                        ),

                        clean_optional_int(
                            row[
                                "releaseYear"
                            ]
                        ),

                        clean_optional_int(
                            row[
                                "listenCount"
                            ]
                        ),

                        clean_optional_int(
                            row[
                                "listenerCount"
                            ]
                        ),

                        artist_id,

                        genre_id,

                        clean_optional_float(
                            row[
                                "popularity"
                            ]
                        ),

                        clean_optional_float(
                            row[
                                "duration"
                            ]
                        ),
                    ),
                )

                inserted_songs += (
                    cur.rowcount
                )

                if (
                    (index + 1) % 250 == 0
                    or index + 1 == len(songs)
                ):
                    print(
                        f"Imported "
                        f"{index + 1}/"
                        f"{len(songs)} songs"
                    )

            conn.commit()

    print()
    print(
        "Import complete."
    )

    print(
        f"Artists created/used: "
        f"{len(artist_ids)}"
    )

    print(
        f"New genres created: "
        f"{inserted_genres}"
    )

    print(
        f"Songs inserted: "
        f"{inserted_songs}"
    )


if __name__ == "__main__":
    main()