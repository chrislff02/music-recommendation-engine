"""
Helpers for communicating with the MusicBrainz public API.

This module:
1. Sends MusicBrainz requests using the project's shared User-Agent.
2. Respects the public API rate limit by delaying requests.
3. Retries temporary failures such as rate limits & server errors.
4. Finds artists from human-readable names.
5. Loads recording metadata and tags.
6. Searches for recordings by title & artist.
"""

import time

import requests

from .config import (
    MUSICBRAINZ_BASE_URL,
    MUSICBRAINZ_REQUEST_DELAY,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


# Shared HTTP headers for every MusicBrainz request.
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}


# Maximum number of attempts before giving up on a request.
MAX_RETRIES = 5

# These HTTP responses are commonly temporary & worth retrying.
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
    """
    Send a GET request to the MusicBrainz API with retry handling.

    Requests are delayed to respect the public API rate limit.
    Temporary network/server failures are retried using exponential
    backoff, while Retry-After is respected when MusicBrainz provides it.

    Returns the parsed JSON response.
    """
    url = (
        f"{MUSICBRAINZ_BASE_URL}/{endpoint}"
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        # Keep requests below the MusicBrainz public API rate limit.
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
            # Retry temporary network-level failures unless this was
            # the final permitted attempt.
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

        # Rate limits & server errors are treated as temporary failures.
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

            # Prefer MusicBrainz's Retry-After value when it is valid.
            # Otherwise, fall back to exponential backoff.
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

        # Non-retryable HTTP failures should surface immediately.
        response.raise_for_status()

        return response.json()

    # Defensive fallback in case the retry loop exits unexpectedly.
    raise RuntimeError(
        "MusicBrainz request failed "
        "after all retry attempts."
    )


def find_artist(
    artist_name,
):
    """
    Find the best MusicBrainz artist match for a given artist name.

    Exact case-insensitive name matches are preferred. If no exact
    match exists, the highest-ranked MusicBrainz search result is used.

    Returns a simplified artist dictionary or None when no result exists.
    """
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

    # Prefer exact name matches so the catalog does not accidentally
    # resolve a seed artist to a similarly named performer.
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
        # MusicBrainz already returns results in relevance order.
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
    """
    Load detailed metadata for a specific MusicBrainz recording.

    Releases & community tags are included because later catalog
    stages use them for release-year and genre enrichment.
    """
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
    """
    Search MusicBrainz for a recording by its recording MBID.

    Returns the first matching recording or None when no result exists.
    """
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
    """
    Search for recordings using both song title & artist MBID.

    The returned results are used by later pipeline stages to compare
    matching recordings & estimate the earliest release year.
    """
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