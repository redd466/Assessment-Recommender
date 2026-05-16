import math
import re
from collections import Counter

from app.models import CatalogItem

TOKEN_RE = re.compile(r"[a-z0-9+#.]+")

TEST_TYPE_LABELS = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}

SYNONYMS = {
    "developer": ["programming", "software", "coding", "java", "python", "net"],
    "engineer": ["technical", "engineering", "programming"],
    "stakeholder": ["communication", "collaboration", "professional", "competencies"],
    "manager": ["management", "leadership", "supervisor"],
    "sales": ["account", "customer", "retail"],
    "support": ["customer", "service", "contact", "call"],
    "personality": ["opq", "behavior", "behaviour", "motivational", "personality"],
    "cognitive": ["ability", "reasoning", "numerical", "deductive", "inductive"],
}

SKILL_ALIASES = {
    ".net": ["net", "c#"],
    "c#": ["c#", "csharp", ".net"],
    "javascript": ["javascript", "js", "node", "react", "angular"],
    "java": ["java", "spring"],
    "python": ["python"],
    "sql": ["sql", "database"],
    "excel": ["excel", "spreadsheet"],
}


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def desired_test_types(text: str) -> set[str]:
    lowered = text.lower()
    desired: set[str] = set()
    if re.search(r"\b(personality|behavior|behaviour|opq|motivation)\b", lowered):
        desired.add("P")
    if re.search(r"\b(cognitive|ability|aptitude|reasoning|numerical|verbal|deductive|inductive)\b", lowered):
        desired.add("A")
    if re.search(r"\b(skill|technical|coding|programming|knowledge|java|python|sql|excel|developer|engineer)\b", lowered):
        desired.add("K")
    if re.search(r"\b(simulation|hands[- ]on|work sample|call center)\b", lowered):
        desired.add("S")
    if re.search(r"\b(competenc|stakeholder|collaboration|communication)\b", lowered):
        desired.add("C")
    return desired


def rank_items(catalog: list[CatalogItem], query: str, limit: int = 10) -> list[CatalogItem]:
    query_terms = expand_query(tokens(query))
    wanted_types = desired_test_types(query)
    scored: list[tuple[float, CatalogItem]] = []

    for item in catalog:
        text = " ".join(
            [
                item.name,
                item.description,
                " ".join(item.job_levels),
                " ".join(item.languages),
                TEST_TYPE_LABELS.get(item.test_type[:1], ""),
            ]
        )
        doc_terms = Counter(tokens(text))
        score = bm25ish(query_terms, doc_terms)
        score += exact_name_bonus(item, query_terms)
        score += test_type_bonus(item, wanted_types)
        score += role_bonus(item, query)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: (-pair[0], pair[1].name.lower()))
    return diversify([item for _, item in scored], wanted_types, limit)


def expand_query(base_terms: list[str]) -> list[str]:
    expanded = list(base_terms)
    joined = " ".join(base_terms)
    for term in base_terms:
        expanded.extend(SYNONYMS.get(term, []))
        expanded.extend(SKILL_ALIASES.get(term, []))
    for key, values in SKILL_ALIASES.items():
        if key in joined:
            expanded.extend(values)
    return expanded


def bm25ish(query_terms: list[str], doc_terms: Counter[str]) -> float:
    score = 0.0
    doc_len = sum(doc_terms.values()) or 1
    for term in query_terms:
        tf = doc_terms.get(term, 0)
        if tf:
            score += (1 + math.log(tf)) / math.sqrt(doc_len / 80)
    return score


def exact_name_bonus(item: CatalogItem, query_terms: list[str]) -> float:
    name_terms = set(tokens(item.name))
    hits = sum(1 for term in set(query_terms) if term in name_terms)
    return hits * 3.0


def test_type_bonus(item: CatalogItem, wanted_types: set[str]) -> float:
    if not wanted_types:
        return 0.0
    item_types = set(item.test_type.replace(" ", ""))
    return 4.0 if item_types & wanted_types else -1.5


def role_bonus(item: CatalogItem, query: str) -> float:
    lowered = query.lower()
    levels = " ".join(item.job_levels).lower()
    score = 0.0
    if "graduate" in lowered or "entry" in lowered or "junior" in lowered:
        score += 1.0 if ("graduate" in levels or "entry" in levels) else 0.0
    if "mid" in lowered or "4 years" in lowered or "5 years" in lowered:
        score += 1.0 if "mid-professional" in levels else 0.0
    if "manager" in lowered or "lead" in lowered or "senior" in lowered:
        score += 1.0 if "manager" in levels or "senior" in levels else 0.0
    return score


def diversify(items: list[CatalogItem], wanted_types: set[str], limit: int) -> list[CatalogItem]:
    if not wanted_types or len(wanted_types) == 1:
        return items[:limit]
    selected: list[CatalogItem] = []
    remaining = items[:]
    for test_type in sorted(wanted_types):
        for item in remaining:
            if test_type in item.test_type:
                selected.append(item)
                remaining.remove(item)
                break
    for item in remaining:
        if len(selected) >= limit:
            break
        selected.append(item)
    return selected[:limit]


def find_by_name(catalog: list[CatalogItem], name: str) -> CatalogItem | None:
    query = set(tokens(name))
    if not query:
        return None
    best: tuple[float, CatalogItem] | None = None
    for item in catalog:
        item_terms = set(tokens(item.name))
        description_terms = set(tokens(item.description))
        acronym = "".join(term[0] for term in tokens(item.name) if term and term[0].isalnum())
        overlap = len(query & item_terms) * 2 + len(query & description_terms)
        if any(term == acronym for term in query):
            overlap += 5
        if overlap and (best is None or overlap > best[0]):
            best = (overlap, item)
    return best[1] if best else None
