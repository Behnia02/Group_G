from __future__ import annotations

# Imports and shared constants

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


# Typed result schema for the structured image step

class ImageDescriptionResult(TypedDict):
    description: dict
    model_name: str
    original_image_path: str
    prepared_image_path: str
    elapsed_seconds: float


# Low-level Ollama request helper

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


# Ollama availability and model utilities

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


# Image validation and preprocessing

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


# JSON extraction / repair helpers

def _extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise RuntimeError("Ollama did not return JSON.")

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

    raise RuntimeError("Could not extract a complete JSON object from the model output.")


def _repair_common_json_escapes(text: str) -> str:
    return re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)


# Helper functions for evidence states and scoring

def _coerce_evidence_state(value: str | None) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in {"none", "unclear", "present"}:
        return cleaned
    return "unclear"


def _evidence_state_to_score(state: str) -> float:
    mapping = {
        "none": 0.0,
        "unclear": 0.5,
        "present": 1.0,
    }
    return mapping.get(state, 0.5)


def _safe_reason(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _label_from_score(score: float) -> str:
    if score >= 1.35:
        return "HIGH"
    if score >= 0.65:
        return "MODERATE"
    return "LOW"


# Structured normalization for the image description

def _normalize_structured_description(data: dict) -> dict:
    return {
        "dominant_land_cover": str(data.get("dominant_land_cover", "")).strip(),
        "vegetation_density": str(data.get("vegetation_density", "unknown")).strip().lower(),
        "vegetation_pattern": str(data.get("vegetation_pattern", "unknown")).strip().lower(),
        "bare_soil_visibility": str(data.get("bare_soil_visibility", "unknown")).strip().lower(),
        "water_presence": str(data.get("water_presence", "unknown")).strip().lower(),
        "water_appearance": str(data.get("water_appearance", "unknown")).strip().lower(),
        "fragmentation_visibility": str(data.get("fragmentation_visibility", "unknown")).strip().lower(),
        "human_disturbance": str(data.get("human_disturbance", "unknown")).strip().lower(),
        "fire_or_smoke_visibility": str(data.get("fire_or_smoke_visibility", "unknown")).strip().lower(),
        "summary": str(data.get("summary", "")).strip(),
    }


# Python-side deterministic scoring
# The model no longer invents the final score directly

def _compute_visual_score(visual_evidence: dict) -> float:
    weights = {
        "vegetation_loss": 0.24,
        "land_degradation": 0.22,
        "water_anomaly": 0.16,
        "fire_signs": 0.16,
        "fragmentation": 0.22,
    }

    total = 0.0
    for key, weight in weights.items():
        state = _coerce_evidence_state(
            visual_evidence.get(key, {}).get("state")
            if isinstance(visual_evidence.get(key), dict)
            else None
        )
        total += _evidence_state_to_score(state) * weight

    return round(total * 2.0, 2)


def _compute_context_score(context_evidence: dict) -> float:
    weights = {
        "forest_change_pressure": 0.4,
        "land_degradation_pressure": 0.3,
        "protection_gap": 0.3,
    }

    total = 0.0
    for key, weight in weights.items():
        state = _coerce_evidence_state(
            context_evidence.get(key, {}).get("state")
            if isinstance(context_evidence.get(key), dict)
            else None
        )
        total += _evidence_state_to_score(state) * weight

    return round(total * 2.0, 2)


# Normalize the structured environmental assessment

def _normalize_environmental_assessment(data: dict) -> dict:
    visual_raw = data.get("visual_evidence", {}) if isinstance(data.get("visual_evidence"), dict) else {}
    context_raw = data.get("context_evidence", {}) if isinstance(data.get("context_evidence"), dict) else {}

    visual_evidence = {
        "vegetation_loss": {
            "state": _coerce_evidence_state(
                visual_raw.get("vegetation_loss", {}).get("state")
                if isinstance(visual_raw.get("vegetation_loss"), dict)
                else None
            ),
            "reason": _safe_reason(
                visual_raw.get("vegetation_loss", {}).get("reason")
                if isinstance(visual_raw.get("vegetation_loss"), dict)
                else None,
                "No clear information about vegetation loss was provided.",
            ),
        },
        "land_degradation": {
            "state": _coerce_evidence_state(
                visual_raw.get("land_degradation", {}).get("state")
                if isinstance(visual_raw.get("land_degradation"), dict)
                else None
            ),
            "reason": _safe_reason(
                visual_raw.get("land_degradation", {}).get("reason")
                if isinstance(visual_raw.get("land_degradation"), dict)
                else None,
                "No clear information about land degradation was provided.",
            ),
        },
        "water_anomaly": {
            "state": _coerce_evidence_state(
                visual_raw.get("water_anomaly", {}).get("state")
                if isinstance(visual_raw.get("water_anomaly"), dict)
                else None
            ),
            "reason": _safe_reason(
                visual_raw.get("water_anomaly", {}).get("reason")
                if isinstance(visual_raw.get("water_anomaly"), dict)
                else None,
                "No clear information about unusual water conditions was provided.",
            ),
        },
        "fire_signs": {
            "state": _coerce_evidence_state(
                visual_raw.get("fire_signs", {}).get("state")
                if isinstance(visual_raw.get("fire_signs"), dict)
                else None
            ),
            "reason": _safe_reason(
                visual_raw.get("fire_signs", {}).get("reason")
                if isinstance(visual_raw.get("fire_signs"), dict)
                else None,
                "No clear information about fire-related signs was provided.",
            ),
        },
        "fragmentation": {
            "state": _coerce_evidence_state(
                visual_raw.get("fragmentation", {}).get("state")
                if isinstance(visual_raw.get("fragmentation"), dict)
                else None
            ),
            "reason": _safe_reason(
                visual_raw.get("fragmentation", {}).get("reason")
                if isinstance(visual_raw.get("fragmentation"), dict)
                else None,
                "No clear information about fragmentation or disturbance was provided.",
            ),
        },
    }

    context_evidence = {
        "forest_change_pressure": {
            "state": _coerce_evidence_state(
                context_raw.get("forest_change_pressure", {}).get("state")
                if isinstance(context_raw.get("forest_change_pressure"), dict)
                else None
            ),
            "reason": _safe_reason(
                context_raw.get("forest_change_pressure", {}).get("reason")
                if isinstance(context_raw.get("forest_change_pressure"), dict)
                else None,
                "No clear country-level forest change pressure was provided.",
            ),
        },
        "land_degradation_pressure": {
            "state": _coerce_evidence_state(
                context_raw.get("land_degradation_pressure", {}).get("state")
                if isinstance(context_raw.get("land_degradation_pressure"), dict)
                else None
            ),
            "reason": _safe_reason(
                context_raw.get("land_degradation_pressure", {}).get("reason")
                if isinstance(context_raw.get("land_degradation_pressure"), dict)
                else None,
                "No clear country-level land degradation pressure was provided.",
            ),
        },
        "protection_gap": {
            "state": _coerce_evidence_state(
                context_raw.get("protection_gap", {}).get("state")
                if isinstance(context_raw.get("protection_gap"), dict)
                else None
            ),
            "reason": _safe_reason(
                context_raw.get("protection_gap", {}).get("reason")
                if isinstance(context_raw.get("protection_gap"), dict)
                else None,
                "No clear country-level protection gap was provided.",
            ),
        },
    }

    visual_score = _compute_visual_score(visual_evidence)
    context_score = _compute_context_score(context_evidence)
    overall_score = round((0.75 * visual_score) + (0.25 * context_score), 2)

    return {
        "visual_evidence": visual_evidence,
        "context_evidence": context_evidence,
        "visual_score": visual_score,
        "context_score": context_score,
        "overall_risk": {
            "level": overall_score,
            "label": _label_from_score(overall_score),
            "reason": str(data.get("overall_reason", "")).strip()
            or "Overall risk was computed in Python from structured visual and context evidence.",
        },
    }


def _heuristic_environmental_assessment(image_description: str | dict) -> dict:
    if not isinstance(image_description, dict):
        return _normalize_environmental_assessment({})

    def state_and_reason(value: str, *, present_values: set[str], none_values: set[str], present_reason: str, none_reason: str, unclear_reason: str) -> dict:
        cleaned = str(value or "").strip().lower()
        if cleaned in present_values:
            return {"state": "present", "reason": present_reason}
        if cleaned in none_values:
            return {"state": "none", "reason": none_reason}
        return {"state": "unclear", "reason": unclear_reason}

    visual = {
        "vegetation_loss": state_and_reason(
            image_description.get("vegetation_density", ""),
            present_values={"low"},
            none_values={"high"},
            present_reason="Sparse vegetation suggests possible vegetation loss or limited vegetative cover.",
            none_reason="Dense vegetation does not suggest visible vegetation loss.",
            unclear_reason="Vegetation condition is not clear enough to confirm visible vegetation loss.",
        ),
        "land_degradation": state_and_reason(
            image_description.get("bare_soil_visibility", ""),
            present_values={"medium", "high"},
            none_values={"none", "low"},
            present_reason="Visible bare soil suggests possible land degradation or exposed ground.",
            none_reason="Bare-soil exposure does not appear strong enough to suggest degradation.",
            unclear_reason="Bare-soil visibility is unclear, so land degradation remains uncertain.",
        ),
        "water_anomaly": state_and_reason(
            image_description.get("water_appearance", ""),
            present_values={"sediment_heavy"},
            none_values={"clear", "dark", "unknown", ""},
            present_reason="Water appearance suggests a possible anomaly such as sediment-heavy flow.",
            none_reason="Water appearance does not show a clear anomaly.",
            unclear_reason="Water conditions are too unclear to judge anomaly risk confidently.",
        ),
        "fire_signs": state_and_reason(
            image_description.get("fire_or_smoke_visibility", ""),
            present_values={"possible", "clear"},
            none_values={"none"},
            present_reason="The description suggests possible fire, smoke, or burn-related evidence.",
            none_reason="No visible signs of fire or smoke were identified.",
            unclear_reason="Fire or smoke evidence is unclear in the description.",
        ),
        "fragmentation": state_and_reason(
            image_description.get("fragmentation_visibility", ""),
            present_values={"medium", "high"},
            none_values={"none", "low"},
            present_reason="Fragmentation appears visible in the described land-cover pattern.",
            none_reason="Fragmentation does not appear strong in the described scene.",
            unclear_reason="Fragmentation remains uncertain from the available description.",
        ),
    }

    return _normalize_environmental_assessment({"visual_evidence": visual, "context_evidence": {}, "overall_reason": "Risk evidence was derived from the structured image description because the model did not return valid JSON."})


# Structured image description with Ollama
# We now standardize the image output as JSON instead of free text.

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
        "Return ONLY valid JSON.\n"
        "Do not use markdown.\n"
        "Do not include code fences.\n"
        "Do not guess hidden causes.\n"
        "Do not perform environmental risk assessment.\n"
        "Describe only what is visibly present.\n\n"
        "Look for both obvious and subtle visual features, including:\n"
        "- dominant land cover\n"
        "- vegetation density and vegetation pattern\n"
        "- patchiness or vegetation interruption\n"
        "- bare soil exposure\n"
        "- water presence and water appearance\n"
        "- visible roads, buildings, linear clearings, or other human disturbance\n"
        "- signs of fragmentation or land-cover transitions\n"
        "- visible burn scars, smoke, or ash if present\n\n"
        "Use conservative wording.\n"
        "If something is not clearly visible, say 'unknown' instead of guessing.\n\n"
        "Return exactly this JSON schema:\n"
        "{\n"
        '  "dominant_land_cover": "",\n'
        '  "vegetation_density": "low|medium|high|unknown",\n'
        '  "vegetation_pattern": "continuous|patchy|fragmented|unknown",\n'
        '  "bare_soil_visibility": "none|low|medium|high|unknown",\n'
        '  "water_presence": "none|small|moderate|large|unknown",\n'
        '  "water_appearance": "clear|sediment_heavy|dark|unknown",\n'
        '  "fragmentation_visibility": "none|low|medium|high|unknown",\n'
        '  "human_disturbance": "none|low|medium|high|unknown",\n'
        '  "fire_or_smoke_visibility": "none|possible|clear|unknown",\n'
        '  "summary": ""\n'
        "}"
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
            "options": {"temperature": 0},
        },
        timeout=timeout,
    )

    elapsed = time.perf_counter() - started
    content = response.get("message", {}).get("content", "").strip()

    if not content:
        raise RuntimeError(DEFAULT_TIMEOUT_MESSAGE)

    try:
        parsed = _normalize_structured_description(json.loads(content))
    except json.JSONDecodeError:
        extracted = _extract_first_json_object(content)
        try:
            parsed = _normalize_structured_description(json.loads(extracted))
        except json.JSONDecodeError:
            repaired = _repair_common_json_escapes(extracted)
            try:
                parsed = _normalize_structured_description(json.loads(repaired))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Ollama returned malformed JSON for image description: {exc}"
                ) from exc

    return {
        "description": parsed,
        "model_name": model_name,
        "original_image_path": str(original_path),
        "prepared_image_path": str(prepared_path),
        "elapsed_seconds": round(elapsed, 2),
    }


# Structured risk assessment with split task groups
# The model only classifies evidence
# Final scores are computed in Python afterwards

def assess_environmental_risk_structured(
    image_description: str | dict,
    dataset_context: str,
    model_name: str = DEFAULT_VISION_MODEL,
    *,
    timeout: int = 180,
    auto_pull_model: bool = True,
) -> dict:
    ensure_model(model_name, auto_pull=auto_pull_model)

    if isinstance(image_description, dict):
        image_description_text = json.dumps(image_description, ensure_ascii=False)
    else:
        image_description_text = str(image_description)

    prompt = f"""
You are an environmental risk analyst.

You will receive:
1. A structured satellite-image description.
2. Country-level environmental indicator context.

Your task has two separate groups:
1. Visual evidence from the image description
2. Country-level context evidence from the dataset

Assess environmental danger behind the scenes using these hidden questions.

Questions for visual evidence:
- Does the image description suggest vegetation loss, sparse cover, or stressed vegetation?
- Does it suggest land degradation, erosion, exposed soil, or disturbed ground?
- Does it suggest flooding, unusual water spread, sediment-heavy water, or abnormal water appearance?
- Does it suggest fire, smoke, burn scars, or thermal disturbance?
- Does it suggest fragmentation, human disturbance, linear clearings, roads, urban sprawl, mining, or abrupt land-cover transitions?

Questions for country-level context evidence:
- Does the country-level context suggest meaningful forest change pressure?
- Does it suggest meaningful land degradation pressure?
- Does it suggest weak protection, ecosystem pressure, or a protection gap?

Important rules:
- Keep visual evidence and context evidence separate.
- Image evidence is local.
- Dataset context is national and historical.
- Do not treat country-level context as exact proof for the local site.
- Do not invent a final score.
- Only classify evidence states and explain them briefly.
- Use conservative reasoning.
- If the evidence is absent, use "none".
- If the evidence is ambiguous, partial, or incomplete, use "unclear".
- If the evidence is supported by the description or context, use "present".
- Consider not only extreme disaster signs but also moderate environmental stress.

Return ONLY valid JSON.
Do not use markdown.
Do not include code fences.

Return exactly this schema:

{{
  "visual_evidence": {{
    "vegetation_loss": {{"state": "none", "reason": ""}},
    "land_degradation": {{"state": "none", "reason": ""}},
    "water_anomaly": {{"state": "none", "reason": ""}},
    "fire_signs": {{"state": "none", "reason": ""}},
    "fragmentation": {{"state": "none", "reason": ""}}
  }},
  "context_evidence": {{
    "forest_change_pressure": {{"state": "none", "reason": ""}},
    "land_degradation_pressure": {{"state": "none", "reason": ""}},
    "protection_gap": {{"state": "none", "reason": ""}}
  }},
  "overall_reason": ""
}}

Structured image description:
{image_description_text}

Dataset context:
{dataset_context}
"""

    response = _request(
        "POST",
        "/api/chat",
        json={
            "model": model_name,
            "stream": False,
            "format": "json",
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": 0},
        },
        timeout=timeout,
    )

    content = response.get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError(DEFAULT_TIMEOUT_MESSAGE)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        try:
            extracted = _extract_first_json_object(content)
            parsed = json.loads(extracted)
        except RuntimeError:
            return _heuristic_environmental_assessment(image_description)
        except json.JSONDecodeError:
            repaired = _repair_common_json_escapes(extracted)
            try:
                parsed = json.loads(repaired)
            except json.JSONDecodeError as exc:
                return _heuristic_environmental_assessment(image_description)

    return _normalize_environmental_assessment(parsed)
