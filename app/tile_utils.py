"""
tile_utils.py
-------------
Downloads a satellite image from ESRI World Imagery
given latitude, longitude, and zoom level.

Uses the standard Web Mercator (EPSG:3857) tile scheme.
Stitches a 3x3 grid of tiles into one image using Pillow.
"""

from __future__ import annotations

from io import BytesIO
import math
from pathlib import Path

import requests
from PIL import Image

# Constants
ESRI_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
TILE_SIZE = 256  # pixels per tile
GRID = 3         # download a 3x3 grid of tiles around the target location
MAX_MERCATOR_LAT = 85.05112878


# Coordinate helpers
def _lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert latitude/longitude to tile (x, y) at the given zoom level."""
    lat = max(-MAX_MERCATOR_LAT, min(MAX_MERCATOR_LAT, lat))
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    x = max(0, min(n - 1, x))
    y = max(0, min(n - 1, y))
    return x, y


# Image download
def download_satellite_image(
    lat: float,
    lon: float,
    zoom: int,
    output_dir: str | Path = "images",
) -> Path:
    """
    Download a satellite image from ESRI World Imagery centred on
    (lat, lon) at the given zoom level.

    A 3x3 grid of tiles is stitched together into a single PNG file
    saved inside *output_dir*.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees (-90 to 90).
    lon : float
        Longitude in decimal degrees (-180 to 180).
    zoom : int
        Zoom level (1–19; 17 gives ~1 m/pixel resolution).
    output_dir : str | Path
        Directory where the image will be saved.

    Returns
    -------
    Path
        Path to the saved PNG file.
    """
    if not -90.0 <= lat <= 90.0:
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("Longitude must be between -180 and 180 degrees.")
    if zoom < 0:
        raise ValueError("Zoom level must be non-negative.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = output_dir / f"satellite_{lat}_{lon}_z{zoom}.png"

    # Return cached image if it already exists
    if filename.exists():
        return filename

    cx, cy = _lat_lon_to_tile(lat, lon, zoom)
    half = GRID // 2

    canvas = Image.new("RGB", (TILE_SIZE * GRID, TILE_SIZE * GRID))

    headers = {"User-Agent": "ProjectOkavango/1.0 (educational)"}

    for row in range(GRID):
        for col in range(GRID):
            tx = cx - half + col
            ty = cy - half + row
            url = ESRI_URL.format(z=zoom, y=ty, x=tx)
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            with Image.open(BytesIO(response.content)) as tile_img:
                canvas.paste(tile_img.convert("RGB"), (col * TILE_SIZE, row * TILE_SIZE))

    canvas.save(filename)
    return filename
