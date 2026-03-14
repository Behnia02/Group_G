from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import TypedDict

import requests
from PIL import Image


DEFAULT_VISION_MODEL = "llava:7b"
DEFAULT_TIMEOUT_MESSAGE = (
    "Ollama did not return a response. Please make sure Ollama is running locally."
)
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

VISION_MODEL_HINTS = (
    "llava",
    "bakllava",
    "llama3.2-vision",
    "minicpm-v",
    "moondream",
)


class ImageDescriptionResult(TypedDict):
    description: str
    model_name: str
    original_image_path: str
    prepared_image_path: str
    elapsed_seconds: float


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
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "The Ollama request timed out. This often happens when the model is too heavy "
            "for the device or the image is too large."
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
    response = _request("GET", "/api/tags", timeout=10)
    models = response.get("models", [])
    names = [model.get("name", "").strip() for model in models]
    return [name for name in names if name]


def find_local_vision_models() -> list[str]:
    models = list_local_models()
    return [
        model
        for model in models
        if any(hint in model.lower() for hint in VISION_MODEL_HINTS)
    ]


def model_exists(model_name: str) -> bool:
    installed_models = list_local_models()
    return any(name == model_name or name.startswith(model_name) for name in installed_models)


def ensure_model(model_name: str = DEFAULT_VISION_MODEL, *, auto_pull: bool = True) -> None:
    if model_exists(model_name):
        return

    if not auto_pull:
        raise RuntimeError(
            f"The Ollama model '{model_name}' is not installed locally. "
            f"Install it first with: ollama pull {model_name}"
        )

    _request(
        "POST",
        "/api/pull",
        json={"name": model_name, "stream": False},
        timeout=900,
    )


def validate_image_path(image_path: str | Path) -> Path:
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file does not exist: {path}")

    if not path.is_file():
        raise FileNotFoundError(f"Image path is not a file: {path}")

    return path


def _encode_image_base64(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def prepare_image_for_ollama(
    image_path: str | Path,
    *,
    max_size: int = 768,
    quality: int = 80,
) -> Path:
    source_path = validate_image_path(image_path)

    cache_dir = source_path.parent / ".ollama_prepared"
    cache_dir.mkdir(parents=True, exist_ok=True)

    prepared_name = f"{source_path.stem}_prepared_{max_size}.jpg"
    prepared_path = cache_dir / prepared_name

    with Image.open(source_path) as image:
        image = image.convert("RGB")
        image.thumbnail((max_size, max_size))
        image.save(
            prepared_path,
            format="JPEG",
            quality=quality,
            optimize=True,
        )

    return prepared_path


def describe_image_with_ollama(
    image_path: str | Path,
    model_name: str = DEFAULT_VISION_MODEL,
    *,
    max_size: int = 768,
    quality: int = 80,
    timeout: int = 240,
    auto_pull_model: bool = True,
) -> ImageDescriptionResult:
    ensure_model(model_name, auto_pull=auto_pull_model)

    original_path = validate_image_path(image_path)
    prepared_path = prepare_image_for_ollama(
        original_path,
        max_size=max_size,
        quality=quality,
    )

    prompt = (
        "You are analyzing a satellite image.\n\n"
        "Describe only what is visibly present in the image in 4 to 6 concise sentences.\n"
        "Focus on land cover, vegetation, water, roads, buildings, bare soil, "
        "burned areas, flooding, erosion, deforestation, smoke, pollution, "
        "or other visible environmental features.\n"
        "Do not guess hidden causes.\n"
        "Do not perform environmental risk assessment.\n"
        "Do not mention uncertainty unless the image is genuinely unclear."
    )

    started = time.perf_counter()

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
                    "images": [_encode_image_base64(prepared_path)],
                }
            ],
        },
        timeout=timeout,
    )

    elapsed = time.perf_counter() - started
    content = response.get("message", {}).get("content", "").strip()

    if not content:
        raise RuntimeError(DEFAULT_TIMEOUT_MESSAGE)

    return {
        "description": content,
        "model_name": model_name,
        "original_image_path": str(original_path),
        "prepared_image_path": str(prepared_path),
        "elapsed_seconds": round(elapsed, 2),
    }


def assess_environmental_risk_structured(
    image_description: str,
    dataset_context: str,
    model_name: str = DEFAULT_VISION_MODEL,
    *,
    timeout: int = 180,
    auto_pull_model: bool = True,
) -> dict:
    ensure_model(model_name, auto_pull=auto_pull_model)

    prompt = f"""
You are an environmental risk analyst.

You will receive:
1. A satellite-image description.
2. Country-level environmental indicator context.

Assess environmental danger behind the scenes using these hidden questions:
- Does the description suggest recent deforestation or strong vegetation loss?
- Does it suggest land degradation, erosion, bare soil exposure, or stressed land cover?
- Does it suggest flooding, unusual water spread, or sediment-heavy water?
- Does it suggest wildfire, burn scars, or smoke?
- Does it suggest habitat fragmentation, urban sprawl, mining, or ecosystem disturbance?
- Does the country-level context indicate that forest change, degradation, or weak protection may increase concern?

Important:
- Image evidence is local.
- Dataset context is national and historical.
- Do not treat national context as exact proof for the local site.
- Be cautious and factual.

Return ONLY valid JSON with exactly this schema:

{{
  "deforestation_risk": {{"level": 0, "reason": ""}},
  "degradation_risk": {{"level": 0, "reason": ""}},
  "fire_risk": {{"level": 0, "reason": ""}},
  "flood_risk": {{"level": 0, "reason": ""}},
  "fragmentation_risk": {{"level": 0, "reason": ""}},
  "overall_visual_risk": {{"level": 0, "label": "LOW", "reason": ""}}
}}

Rules:
- Use level 0 for no clear sign / low concern
- Use level 1 for possible or moderate concern
- Use level 2 for strong concern
- overall_visual_risk.label must be one of: LOW, MODERATE, HIGH
- No markdown
- No extra text outside JSON

Image description:
{image_description}

Dataset context:
{dataset_context}
"""

    response = _request(
        "POST",
        "/api/chat",
        json={
            "model": model_name,
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )

    content = response.get("message", {}).get("content", "").strip()

    if not content:
        raise RuntimeError(DEFAULT_TIMEOUT_MESSAGE)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise RuntimeError("Ollama returned invalid JSON for risk assessment.")
