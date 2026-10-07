import time

import requests

from .config import (
    MUSICBRAINZ_BASE_URL,
    MUSICBRAINZ_REQUEST_DELAY,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}


MAX_RETRIES = 5

RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


def musicbrainz_get(
    endpoint,
    params=None,
):
    url = (
        f"{MUSICBRAINZ_BASE_URL}/{endpoint}"
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        # Keep MusicBrainz requests safely below
        # the public API rate limit.
        time.sleep(
            MUSICBRAINZ_REQUEST_DELAY
        )

        try:
            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

        except requests.RequestException as error:
            if attempt == MAX_RETRIES:
                raise

            wait_seconds = 2 ** attempt

            print(
                "  MusicBrainz request failed "
                f"({error}). "
                f"Retrying in {wait_seconds}s..."
            )

            time.sleep(
                wait_seconds
            )

            continue

        if response.status_code in (
            RETRYABLE_STATUS_CODES
        ):
            if attempt == MAX_RETRIES:
                response.raise_for_status()

            retry_after = (
                response.headers.get(
                    "Retry-After"
                )
            )

            if retry_after:
                try:
                    wait_seconds = max(
                        2.0,
                        float(retry_after),
                    )
                except ValueError:
                    wait_seconds = (
                        2 ** attempt
                    )
            else:
                wait_seconds = (
                    2 ** attempt
                )

            print(
                "  MusicBrainz returned "
                f"{response.status_code}. "
                f"Retrying in {wait_seconds}s..."
            )

            time.sleep(
                wait_seconds
            )

            continue

        response.raise_for_status()

        return response.json()

    raise RuntimeError(
        "MusicBrainz request failed "
        "after all retry attempts."
    )


def find_artist(
    artist_name,
):
    data = musicbrainz_get(
        "artist",
        params={
            "query": (
                f'artist:"{artist_name}"'
            ),
            "fmt": "json",
            "limit": 5,
        },
    )

    artists = data.get(
        "artists",
        [],
    )

    if not artists:
        return None

    exact_matches = [
        artist
        for artist in artists
        if artist.get(
            "name",
            "",
        ).casefold()
        == artist_name.casefold()
    ]

    if exact_matches:
        artist = exact_matches[0]
    else:
        artist = artists[0]

    return {
        "mbid": artist["id"],
        "name": artist["name"],
        "country": artist.get(
            "country"
        ),
        "score": artist.get(
            "score"
        ),
    }

def get_recording_details(
    recording_mbid,
):
    return musicbrainz_get(
        f"recording/{recording_mbid}",
        params={
            "fmt": "json",
            "inc": "releases+tags",
        },
    )

def search_recording_details(
    recording_mbid,
):
    data = musicbrainz_get(
        "recording",
        params={
            "query": f"rid:{recording_mbid}",
            "fmt": "json",
            "limit": 1,
        },
    )

    recordings = data.get(
        "recordings",
        [],
    )

    if not recordings:
        return None

    return recordings[0]

def search_song_by_title_and_artist(
    title,
    artist_mbid,
):
    query = (
        f'recording:"{title}" '
        f'AND arid:{artist_mbid}'
    )

    data = musicbrainz_get(
        "recording",
        params={
            "query": query,
            "fmt": "json",
            "limit": 100,
        },
    )

    return data.get(
        "recordings",
        [],
    )