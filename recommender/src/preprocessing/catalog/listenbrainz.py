"""
Helpers for retrieving popular recordings from the ListenBrainz API.

This module:
1. Builds authenticated-style request headers using the project User-Agent.
2. Requests the most popular recordings for a MusicBrainz artist ID.
3. Retries temporary failures such as rate limits & server errors.
4. Respects the Retry-After header when ListenBrainz provides one.
5. Returns only the configured number of top recordings per artist.
"""

import time

import requests

from .config import (
    LISTENBRAINZ_BASE_URL,
    REQUEST_TIMEOUT,
    TOP_RECORDINGS_PER_ARTIST,
    USER_AGENT,
)


# Shared headers sent with every ListenBrainz request.
# A descriptive User-Agent is important when using public music APIs.
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}


# Limit how many times temporary API failures are retried.
MAX_RETRIES = 4

# These status codes may represent temporary conditions such as
# rate limiting/ListenBrainz service availability problems.
RETRYABLE_STATUS_CODES = {
    401,
    429,
    500,
    502,
    503,
    504,
}


def get_top_recordings_for_artist(
    artist_mbid,
):
    """
    Fetch the most popular recordings for a MusicBrainz artist.

    Temporary request failures are retried with exponential backoff.
    When ListenBrainz provides a Retry-After header, that value is used
    when deciding how long to wait before the next attempt.

    Returns at most TOP_RECORDINGS_PER_ARTIST recording dictionaries.
    """
    # Build the ListenBrainz popularity endpoint using the artist's
    # MusicBrainz identifier.
    url = (
        f"{LISTENBRAINZ_BASE_URL}"
        f"/1/popularity/"
        f"top-recordings-for-artist/"
        f"{artist_mbid}"
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

        except requests.RequestException:
            # Network-level failures such as timeouts/connection
            # problems are retried unless this was the final attempt.
            if attempt == MAX_RETRIES:
                raise

            # Exponential backoff gives the remote service time to recover.
            wait_seconds = 2 ** attempt

            print(
                "  ListenBrainz request failed. "
                f"Retrying in {wait_seconds}s..."
            )

            time.sleep(
                wait_seconds
            )

            continue

        # Retry status codes that are commonly temporary, including
        # rate limits and server-side errors.
        if response.status_code in (
            RETRYABLE_STATUS_CODES
        ):
            if attempt == MAX_RETRIES:
                response.raise_for_status()

            # Prefer ListenBrainz's Retry-After value when available.
            # Otherwise, fall back to exponential backoff.
            wait_seconds = max(
                2.0,
                float(
                    response.headers.get(
                        "Retry-After",
                        2 ** attempt,
                    )
                ),
            )

            print(
                "  ListenBrainz returned "
                f"{response.status_code}. "
                f"Retrying in {wait_seconds}s..."
            )

            time.sleep(
                wait_seconds
            )

            continue

        # Raise immediately for non-retryable HTTP failures.
        response.raise_for_status()

        data = response.json()

        # ListenBrainz responses may be returned either directly as a list
        # or inside a "recordings" field, depending on the endpoint response.
        if isinstance(
            data,
            list,
        ):
            recordings = data
        else:
            recordings = data.get(
                "recordings",
                [],
            )

        # Keep the catalog controlled by limiting how many songs are
        # collected for each seed artist.
        return recordings[
            :TOP_RECORDINGS_PER_ARTIST
        ]

    # This is mainly a defensive fallback because successful requests
    # return above and final failures raise an exception.
    return []