"""
Replace the current MusicMatch song catalog with the final processed catalog.
This script imports catalog_ready_for_db.csv into PostgreSQL.

It:
1. Loads the database connection from server/.env.
2. Requires explicit confirmation before replacing catalog data.
3. Preserves users and existing genre records.
4. Deletes ratings and favorite-artist selections tied to the old catalog.
5. Rebuilds Artist and Song data from the processed catalog.
6. Reuses or creates Genre records as needed.
7. Handles duplicate artist MusicBrainz IDs safely.
8. Commits the replacement only after the full import succeeds.
"""

from pathlib import Path
import os

import pandas as pd
import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Final processed catalog produced by prepare_final_catalog.py.
CATALOG_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "catalog"
    / "catalog_ready_for_db.csv"
)

# Reuse the same database configuration as the Node/Express backend.
SERVER_ENV_PATH = (
    PROJECT_ROOT
    / "server"
    / ".env"
)

def clean_optional_int(value):
    """Convert a nullable catalog value to int, preserving missing values."""
    if pd.isna(value):
        return None

    return int(value)


def clean_optional_float(value):
    """Convert a nullable catalog value to float, preserving missing values."""
    if pd.isna(value):
        return None

    return float(value)


def clean_optional_text(value):
    """
    Convert optional text into a cleaned string.
    Missing or empty values become None so PostgreSQL stores them as NULL.
    """
    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def main():
    """Replace the existing song catalog with the processed MusicMatch catalog."""

    # Load DATABASE_URL from the backend environment file.
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

    # Fail before touching the database if the prepared catalog is missing.
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


    # --------------------------------------------------
    # DESTRUCTIVE-IMPORT CONFIRMATION
    # --------------------------------------------------

    # Replacing the catalog invalidates song/artist foreign-key references,
    # so ratings & favorite-artist selections must be removed first.
    # Users & genre preferences can remain.
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

    # Require an exact confirmation word to reduce the chance of
    # accidentally replacing the production/local catalog.
    confirmation = input(
        "\nType REPLACE to continue: "
    )

    if confirmation != "REPLACE":
        print(
            "Import cancelled."
        )
        return

    # psycopg uses a transaction for this connection. The catalog is only
    # committed after the full replacement succeeds.
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

            # Ratings reference songs from the old catalog.
            cur.execute(
                """
                DELETE FROM "Rating"
                """
            )

            # Favorite artists reference Artist rows that will be replaced.
            cur.execute(
                """
                DELETE FROM "UserFavoriteArtist"
                """
            )

            # Songs must be removed before artists because Song references Artist.
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

            # Genre rows are preserved so existing favorite-genre selections
            # remain valid where possible.
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

            # Cache imported artists by name so repeated songs from the same
            # artist do not repeatedly query/insert the Artist table.
            artist_ids = {}

            # Track which MusicBrainz artist IDs have already been assigned.
            # Some collaboration credits can reuse a primary artist MBID under
            # a different display name, which would violate the unique constraint.
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

                    # Do not assign the same unique MusicBrainz ID to two
                    # different artist-credit names. This can happen when a
                    # collaboration recording is credited differently while
                    # ListenBrainz still returns the primary artist MBID.
                    if (
                        artist_mbid is not None
                        and artist_mbid in used_artist_mbids
                        and used_artist_mbids[artist_mbid] != artist_name
                    ):
                        safe_artist_mbid = None

                    # Insert the artist by name. If the name already exists,
                    # preserve any existing MBID & only fill it when missing.
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

                    # Track the final MBID stored by PostgreSQL so later
                    # artist-credit rows can avoid reusing it incorrectly.
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

                # Songs with unknown genres are allowed to keep genreId NULL.
                if genre_name is not None:

                    if genre_name not in genre_ids:

                        # Create only genres that do not already exist.
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

                # Each MusicBrainz recording ID should be unique. If a duplicate
                # somehow survives preprocessing, ON CONFLICT prevents a second
                # Song row from being created.
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

                        # externalId belonged to the older catalog source &
                        # is intentionally left NULL for the current catalog.
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

                # rowcount is 1 when a song was inserted & 0 when
                # ON CONFLICT skipped a duplicate MusicBrainz recording.
                inserted_songs += (
                    cur.rowcount
                )

                # Print progress periodically without flooding the terminal.
                if (
                    (index + 1) % 250 == 0
                    or index + 1 == len(songs)
                ):
                    print(
                        f"Imported "
                        f"{index + 1}/"
                        f"{len(songs)} songs"
                    )

            # Commit only after every delete/insert step has completed.
            # If an exception occurs before this point, the transaction can
            # roll back instead of leaving a partially replaced catalog.
            conn.commit()


    # ----------------------------------------------
    # IMPORT SUMMARY
    # ----------------------------------------------

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