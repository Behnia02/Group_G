"""
ai_analysis.py
--------------
Ollama-based AI workflow for Project Okavango.

Step 1 — Vision model (llava):  describe what is in the satellite image.
Step 2 — Text model  (llama3.2): decide whether the area is at environmental risk.

Model names and prompts are read from models.yaml in the project root.
If a required model is not present locally it is pulled automatically.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import ollama
import yaml


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_models_config(config_path: str | Path = "models.yaml") -> dict[str, Any]:
    """
    Load AI model configuration from *config_path*.

    Returns a dict with keys:
        vision_model, vision_prompt, text_model, text_prompt
    Falls back to sensible defaults if the file is missing.
    """
    defaults: dict[str, Any] = {
        "vision_model": "llava",
        "vision_prompt": (
            "You are an environmental analyst. "
            "Describe what you see in this satellite image in 3-5 sentences. "
            "Focus on land use, vegetation, water bodies, and any signs of "
            "human activity or environmental stress."
        ),
        "text_model": "llama3.2",
        "text_prompt": (
            "You are an environmental risk assessor. "
            "Given the following satellite image description, answer these questions "
            "and then give a final verdict:\n"
            "1. Is there evidence of deforestation or vegetation loss?\n"
            "2. Are there signs of land degradation or desertification?\n"
            "3. Is there visible pollution or industrial activity?\n"
            "4. Are water bodies healthy or showing stress?\n"
            "5. Overall, is this area at ENVIRONMENTAL RISK? Answer YES or NO at the end.\n\n"
            "Description: {description}"
        ),
    }

    path = Path(config_path)
    if not path.exists():
        return defaults

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    # Merge with defaults so missing keys are filled in
    return {**defaults, **data}


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------

def _ensure_model(model_name: str) -> None:
    """Pull *model_name* from Ollama if it is not already available locally."""
    try:
        available = {m.model.split(":")[0] for m in ollama.list().models}
        base = model_name.split(":")[0]
        if base not in available:
            print(f"[Okavango] Pulling model '{model_name}' — this may take a few minutes…")
            ollama.pull(model_name)
    except Exception as exc:
        raise RuntimeError(
            f"Could not ensure model '{model_name}' is available: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# AI pipeline
# ---------------------------------------------------------------------------

def describe_image(image_path: str | Path, config: dict[str, Any]) -> str:
    """
    Use the vision model to produce a textual description of the
    satellite image at *image_path*.

    Parameters
    ----------
    image_path : str | Path
        Path to the PNG satellite image.
    config : dict
        Configuration dict from :func:`load_models_config`.

    Returns
    -------
    str
        Natural-language description of the image.
    """
    model = config["vision_model"]
    prompt = config["vision_prompt"]

    _ensure_model(model)

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [str(image_path)],
            }
        ],
    )
    return response.message.content.strip()


def assess_environmental_risk(description: str, config: dict[str, Any]) -> tuple[str, bool]:
    """
    Use the text model to decide whether the area described is at
    environmental risk.

    Parameters
    ----------
    description : str
        Image description from :func:`describe_image`.
    config : dict
        Configuration dict from :func:`load_models_config`.

    Returns
    -------
    tuple[str, bool]
        (full assessment text, True if area is flagged as at risk)
    """
    model = config["text_model"]
    prompt_template = config["text_prompt"]
    prompt = prompt_template.format(description=description)

    _ensure_model(model)

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    assessment = response.message.content.strip()

    # Detect risk verdict — look for YES in the last few lines
    last_lines = assessment.upper().split("\n")[-5:]
    at_risk = any("YES" in line for line in last_lines)

    return assessment, at_risk


def run_ai_pipeline(
    image_path: str | Path,
    config: dict[str, Any],
) -> tuple[str, str, bool]:
    """
    Run the full AI pipeline:
        image → description → risk assessment.

    Returns
    -------
    tuple[str, str, bool]
        (image_description, risk_assessment_text, at_risk_flag)
    """
    description = describe_image(image_path, config)
    assessment, at_risk = assess_environmental_risk(description, config)
    return description, assessment, at_risk
