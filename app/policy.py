import re

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|above|system|developer) instructions",
    r"reveal (your )?(prompt|system message|instructions)",
    r"jailbreak",
    r"act as (?!an shl)",
]

OFF_TOPIC_PATTERNS = [
    r"\blegal\b|\blawyer\b|\bcompliance advice\b|\bsue\b|\bcontract\b",
    r"\bsalary\b|\bcompensation\b|\binterview questions\b|\bjob description template\b",
    r"\bgeneral hiring advice\b|\bperformance improvement plan\b|\bfire\b|\btermination\b",
]


def refusal_reason(text: str) -> str | None:
    lowered = text.lower()
    if any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS):
        return "I can only follow the assignment rules and use the SHL catalog as my source."
    if any(re.search(pattern, lowered) for pattern in OFF_TOPIC_PATTERNS):
        return "I can help with SHL assessment selection, comparison, and refinement, but not general hiring, legal, or HR advice."
    if "shl" not in lowered and re.search(r"\b(weather|recipe|movie|travel|stock|crypto|medical)\b", lowered):
        return "I can only discuss SHL assessments from the catalog."
    return None
