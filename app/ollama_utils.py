from __future__ import annotations

import base64
from pathlib import Path
from typing import TypedDict

import requests


DEFAULT_VISION_MODEL = "llava:7b"
DEFAULT_TIMEOUT_MESSAGE = (
    "Ollama did not return a response. Please make sure Ollama is running locally."
)
OLLAMA_BASE_URL = "http://127.0.0.1:11434"


class RiskAssessmentResult(TypedDict):
    description: str
    risk_assessment: str
    is_at_risk: bool


def _request(
    method: str,
    path: str,
    *,
    json: dict | None = None,
    timeout: int = 180,
) -> dict:
    url = f"{OLLAMA_BASE_URL}{path}"
    try:
        response = requests.request(method, url, json=json, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "Could not connect to Ollama. Please make sure the Ollama app is installed and running locally."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("Ollama returned an invalid response.") from exc


def ollama_is_available() -> bool:
    try:
        _request("GET", "/api/tags", timeout=5)
        return True
    except RuntimeError:
        return False


def list_local_models() -> list[str]:
    """
    Return a list of locally available Ollama model names.
    """
    response = _request("GET", "/api/tags", timeout=10)
    models = response.get("models", [])
    return [model.get("name", "") for model in models]


def model_exists(model_name: str) -> bool:
    """
    Check whether a model is already available locally in Ollama.
    """
    installed_models = list_local_models()
    return any(name == model_name or name.startswith(model_name) for name in installed_models)


def ensure_model(model_name: str = DEFAULT_VISION_MODEL) -> None:
    """
    Ensure that the given Ollama model exists locally.
    If it is missing, pull it automatically.
    """
    if not model_exists(model_name):
        _request(
            "POST",
            "/api/pull",
            json={"name": model_name, "stream": False},
            timeout=600,
        )


def validate_image_path(image_path: str | Path) -> Path:
    """
    Validate that the given image path exists and points to a file.
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file does not exist: {path}")

    if not path.is_file():
        raise FileNotFoundError(f"Image path is not a file: {path}")

    return path


def _encode_image_base64(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def describe_image_with_ollama(
    image_path: str | Path,
    model_name: str = DEFAULT_VISION_MODEL,
) -> str:
    """
    Use an Ollama vision model to describe a satellite image.
    """
    ensure_model(model_name)
    path = validate_image_path(image_path)

    prompt = (
        "You are analyzing a satellite image. "
        "Describe what you see clearly and factually in 5 to 8 sentences. "
        "Focus on land cover, vegetation, water, roads, buildings, bare soil, "
        "burned areas, flooding, erosion, deforestation, smoke, pollution, "
        "or other visible environmental features. "
        "Do not invent details that are not visible."
    )

    response = _request(
        "POST",
        "/api/chat",
        json={
            "model": model_name,
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [_encode_image_base64(path)],
                }
            ],
        },
        timeout=300,
    )

    content = response.get("message", {}).get("content", "").strip()

    if not content:
        raise RuntimeError(DEFAULT_TIMEOUT_MESSAGE)

    return content


def assess_environmental_risk(
    image_description: str,
    model_name: str = DEFAULT_VISION_MODEL,
) -> tuple[str, bool]:
    """
    Ask Ollama to assess whether the described area may be at environmental risk.
    """
    ensure_model(model_name)

    prompt = (
        "You are an environmental risk analyst.\n\n"
        "Based on the following satellite-image description, decide whether the area "
        "shows signs of environmental risk.\n\n"
        "Examples of possible risk indicators include:\n"
        "- flooding or standing water in unusual areas\n"
        "- wildfire, burn scars, or smoke\n"
        "- erosion or severe bare-soil exposure\n"
        "- deforestation or land degradation\n"
        "- pollution or visible damage to ecosystems\n\n"
        "Return your answer in exactly this format:\n\n"
        "RISK: YES or NO\n"
        "REASON: <2 to 4 sentences>\n\n"
        f"Description:\n{image_description}"
    )

    response = _request(
        "POST",
        "/api/chat",
        json={
            "model": model_name,
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=180,
    )

    content = response.get("message", {}).get("content", "").strip()

    if not content:
        raise RuntimeError(DEFAULT_TIMEOUT_MESSAGE)

    normalized = content.upper()
    is_at_risk = "RISK: YES" in normalized

    return content, is_at_risk


def analyze_satellite_image(
    image_path: str | Path,
    model_name: str = DEFAULT_VISION_MODEL,
) -> RiskAssessmentResult:
    """
    Full workflow:
    1. Describe the satellite image.
    2. Assess environmental risk from that description.
    3. Return both results plus a boolean risk flag.
    """
    description = describe_image_with_ollama(image_path=image_path, model_name=model_name)
    risk_assessment, is_at_risk = assess_environmental_risk(
        image_description=description,
        model_name=model_name,
    )

    return {
        "description": description,
        "risk_assessment": risk_assessment,
        "is_at_risk": is_at_risk,
    }
