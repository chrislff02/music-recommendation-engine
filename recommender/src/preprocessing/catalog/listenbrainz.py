import time

import requests

from .config import (
    LISTENBRAINZ_BASE_URL,
    REQUEST_TIMEOUT,
    TOP_RECORDINGS_PER_ARTIST,
    USER_AGENT,
)


HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}


MAX_RETRIES = 4

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
            if attempt == MAX_RETRIES:
                raise

            wait_seconds = 2 ** attempt

            print(
                "  ListenBrainz request failed. "
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

        response.raise_for_status()

        data = response.json()

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

        return recordings[
            :TOP_RECORDINGS_PER_ARTIST
        ]

    return []