"""
db_utils.py
-----------
Handles reading from and writing to the database/images.csv log file.
Every pipeline run is recorded. Before running, we check if the same
lat/lon/zoom already exists — if so, we return the cached result.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path("database/images.csv")

COLUMNS = [
    "timestamp",
    "latitude",
    "longitude",
    "zoom",
    "image_path",
    "image_description",
    "image_prompt",
    "image_model",
    "text_description",
    "text_prompt",
    "text_model",
    "visual_risk_score",
    "dataset_risk_score",
    "final_risk_score",
    "deforestation_risk",
    "deforestation_reason",
    "degradation_risk",
    "degradation_reason",
    "fire_risk",
    "fire_reason",
    "flood_risk",
    "flood_reason",
    "fragmentation_risk",
    "fragmentation_reason",
    "danger",
]


def _ensure_db() -> None:
    """Create the database directory and CSV file if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        pd.DataFrame(columns=COLUMNS).to_csv(DB_PATH, index=False)


def load_db() -> pd.DataFrame:
    """Load the full CSV database."""
    _ensure_db()
    try:
        df = pd.read_csv(DB_PATH)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = None
        return df
    except Exception:
        return pd.DataFrame(columns=COLUMNS)


def check_cache(lat: float, lon: float, zoom: int) -> dict | None:
    """
    Check if a result already exists for the given lat/lon/zoom.
    Returns the cached row as a dict, or None if not found.
    """
    df = load_db()
    if df.empty:
        return None

    match = df[
        (df["latitude"].astype(float).round(6) == round(lat, 6))
        & (df["longitude"].astype(float).round(6) == round(lon, 6))
        & (df["zoom"].astype(int) == int(zoom))
    ]

    if match.empty:
        return None

    return match.iloc[-1].to_dict()


def append_run(
    lat: float,
    lon: float,
    zoom: int,
    image_path: str,
    image_description: str,
    image_prompt: str,
    image_model: str,
    text_description: str,
    text_prompt: str,
    text_model: str,
    visual_risk_score: float,
    dataset_risk_score: float,
    final_risk_score: float,
    deforestation_risk: float,
    deforestation_reason: str,
    degradation_risk: float,
    degradation_reason: str,
    fire_risk: float,
    fire_reason: str,
    flood_risk: float,
    flood_reason: str,
    fragmentation_risk: float,
    fragmentation_reason: str,
    danger: str,
) -> None:
    """Append a new pipeline run to the CSV database."""
    _ensure_db()

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "zoom": int(zoom),
        "image_path": image_path,
        "image_description": image_description,
        "image_prompt": image_prompt,
        "image_model": image_model,
        "text_description": text_description,
        "text_prompt": text_prompt,
        "text_model": text_model,
        "visual_risk_score": round(visual_risk_score, 4),
        "dataset_risk_score": round(dataset_risk_score, 4),
        "final_risk_score": round(final_risk_score, 4),
        "deforestation_risk": round(deforestation_risk, 4),
        "deforestation_reason": deforestation_reason,
        "degradation_risk": round(degradation_risk, 4),
        "degradation_reason": degradation_reason,
        "fire_risk": round(fire_risk, 4),
        "fire_reason": fire_reason,
        "flood_risk": round(flood_risk, 4),
        "flood_reason": flood_reason,
        "fragmentation_risk": round(fragmentation_risk, 4),
        "fragmentation_reason": fragmentation_reason,
        "danger": danger,
    }

    df = load_db()
    new_row = pd.DataFrame([row])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DB_PATH, index=False)
