"""
config_loader.py
----------------
Reads models.yaml from the project root and exposes
model names, prompts, and settings for the AI workflow.
"""

from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_PATH = Path("models.yaml")


def load_config() -> dict:
    """Load and return the full models.yaml config."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"models.yaml not found at {CONFIG_PATH.resolve()}. "
            "Please make sure it exists in the project root."
        )
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_image_model_config() -> dict:
    """Return the image model section from models.yaml."""
    return load_config()["image_model"]


def get_text_model_config() -> dict:
    """Return the text model section from models.yaml."""
    return load_config()["text_model"]


def get_risk_thresholds() -> dict:
    """Return the risk threshold section from models.yaml."""
    return load_config().get("risk_thresholds", {"high": 1.0, "moderate": 0.45})
