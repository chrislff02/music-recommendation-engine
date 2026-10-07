from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA_ROOT = PROJECT_ROOT / "data"

RAW_CATALOG_DIR = (
    DATA_ROOT
    / "raw"
    / "catalog"
)

PROCESSED_CATALOG_DIR = (
    DATA_ROOT
    / "processed"
    / "catalog"
)

RAW_CATALOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PROCESSED_CATALOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


MUSICBRAINZ_BASE_URL = (
    "https://musicbrainz.org/ws/2"
)

LISTENBRAINZ_BASE_URL = (
    "https://api.listenbrainz.org"
)


USER_AGENT = (
    "MusicMatch/1.0 "
    "(music-recommendation-engine portfolio project)"
)


REQUEST_TIMEOUT = 30

MUSICBRAINZ_REQUEST_DELAY = 1.1

TARGET_CATALOG_SIZE = 20_000

TOP_RECORDINGS_PER_ARTIST = 50