"""
Shared configuration for the MusicMatch catalog-building pipeline.

This module defines:
- Project and data directory paths
- MusicBrainz and ListenBrainz API endpoints
- HTTP request settings
- Catalog size and per-artist collection limits

The data directories are created automatically when this module is imported.
"""

from pathlib import Path


# Root directory of the full MusicMatch project.
PROJECT_ROOT = Path(__file__).resolve().parents[4]

# Shared data directory used by the catalog pipeline.
DATA_ROOT = PROJECT_ROOT / "data"

# Raw API/reference data is stored here.
RAW_CATALOG_DIR = (
    DATA_ROOT
    / "raw"
    / "catalog"
)

# Processed catalog stages are stored here.
PROCESSED_CATALOG_DIR = (
    DATA_ROOT
    / "processed"
    / "catalog"
)

# Make sure both catalog directories exist before any pipeline script
# tries to read or write files.
RAW_CATALOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PROCESSED_CATALOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# Public API base URLs used by the catalog pipeline.
MUSICBRAINZ_BASE_URL = (
    "https://musicbrainz.org/ws/2"
)

LISTENBRAINZ_BASE_URL = (
    "https://api.listenbrainz.org"
)


# Identifies the project when making requests to public music APIs.
USER_AGENT = (
    "MusicMatch/1.0 "
    "(music-recommendation-engine portfolio project)"
)


# Maximum time, in seconds, to wait for an HTTP request.
REQUEST_TIMEOUT = 30

# Delay between MusicBrainz requests to stay within the public API rate limit.
MUSICBRAINZ_REQUEST_DELAY = 1.1

# Long-term target size for the catalog-building pipeline.
TARGET_CATALOG_SIZE = 20_000

# Maximum number of popular recordings collected for each seed artist.
TOP_RECORDINGS_PER_ARTIST = 50