import json
import re
from functools import lru_cache
from pathlib import Path

from app.models import CatalogItem

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "catalog.json"

TYPE_LABEL_TO_CODE = {
    "Ability & Aptitude": "A",
    "Assessment Exercises": "E",
    "Biodata & Situational Judgment": "B",
    "Biodata & Situational Judgement": "B",
    "Competencies": "C",
    "Development & 360": "D",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
}

MOJIBAKE_REPLACEMENTS = {
    "\u00c3\u00a2\u00e2\u201a\u00ac\u00e2\u20ac\u0153": "-",
    "\u00c3\u00a2\u00e2\u201a\u00ac\u00e2\u20ac\u009d": "-",
    "\u00c3\u00a2\u00e2\u201a\u00ac\u00cb\u0153": "'",
    "\u00c3\u00a2\u00e2\u201a\u00ac\u00e2\u201e\u00a2": "'",
    "\u00c3\u00a2\u00e2\u201a\u00ac\u00c5\u201c": '"',
    "\u00c3\u00a2\u00e2\u201a\u00ac\u00c2\u009d": '"',
    "\u00c3\u00a2\u00e2\u201a\u00ac\u00c2\u00a2": "-",
    "\u00c3\u00a2\u00e2\u20ac\u017e\u00c2\u00a2": "TM",
    "\u00c3\u0192\u00c2\u00a9": "e",
    "\u00c3\u0192\u00c2\u00a7": "c",
    "\u00c3\u0192\u00c2\u00b1": "n",
    "\u00c3\u0192\u00c2\u00a1": "a",
    "\u00c3\u0192\u00c2\u00b3": "o",
    "\u00c3\u0192\u00c2\u00ad": "i",
    "\u00c3\u0192\u00c2\u00ba": "u",
}


@lru_cache(maxsize=1)
def load_catalog() -> list[CatalogItem]:
    if not CATALOG_PATH.exists():
        return _fallback_catalog()
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return [CatalogItem.model_validate(normalize_catalog_item(item)) for item in raw]


def catalog_urls() -> set[str]:
    return {item.url for item in load_catalog()}


def normalize_catalog_item(item: dict) -> dict:
    """Accept both our compact schema and richer raw SHL scrape records."""
    if "url" in item and "test_type" in item:
        return item

    keys = item.get("keys") or []
    test_type = " ".join(
        dict.fromkeys(TYPE_LABEL_TO_CODE.get(key, key[:1].upper()) for key in keys if key)
    )
    return {
        "name": clean_text(item.get("name", "")),
        "url": item.get("url") or item.get("link") or "",
        "test_type": test_type,
        "description": clean_text(item.get("description", "")),
        "job_levels": item.get("job_levels") or [],
        "languages": item.get("languages") or [],
        "assessment_length_minutes": parse_minutes(item.get("duration") or item.get("duration_raw")),
        "remote_testing": parse_yes_no(item.get("remote")),
        "adaptive_irt": parse_yes_no(item.get("adaptive")),
    }


def clean_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    for source, target in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def parse_yes_no(value: str | bool | None) -> bool | None:
    if isinstance(value, bool) or value is None:
        return value
    lowered = value.strip().lower()
    if lowered in {"yes", "true", "1"}:
        return True
    if lowered in {"no", "false", "0"}:
        return False
    return None


def parse_minutes(value: str | int | None) -> int | None:
    if isinstance(value, int):
        return value
    if not value:
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def _fallback_catalog() -> list[CatalogItem]:
    """Small seed so tests and health checks work before the scraper is run."""
    seed = [
        {
            "name": "Java 8 (New)",
            "url": "https://www.shl.com/products/product-catalog/view/java-8-new/",
            "test_type": "K",
            "description": "Multi-choice test that measures knowledge of Java 8 programming.",
            "job_levels": ["Mid-Professional", "Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "assessment_length_minutes": 10,
            "remote_testing": True,
            "adaptive_irt": False,
        },
        {
            "name": "Occupational Personality Questionnaire OPQ32r",
            "url": "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
            "test_type": "P",
            "description": "Personality assessment used to understand workplace behavioral preferences.",
            "job_levels": ["Graduate", "Mid-Professional", "Manager"],
            "languages": ["English (USA)"],
            "assessment_length_minutes": 25,
            "remote_testing": True,
            "adaptive_irt": False,
        },
        {
            "name": "Verify Interactive - Deductive Reasoning",
            "url": "https://www.shl.com/products/product-catalog/view/verify-interactive-deductive-reasoning/",
            "test_type": "A",
            "description": "Ability assessment measuring deductive reasoning for professional roles.",
            "job_levels": ["Graduate", "Mid-Professional", "Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "assessment_length_minutes": 18,
            "remote_testing": True,
            "adaptive_irt": True,
        },
    ]
    return [CatalogItem.model_validate(item) for item in seed]
