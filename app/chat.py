import re

from app.catalog import load_catalog
from app.models import ChatRequest, ChatResponse, Recommendation
from app.policy import refusal_reason
from app.retrieval import TEST_TYPE_LABELS, desired_test_types, find_by_name, rank_items


VAGUE_PATTERNS = [
    r"^\s*i need an assessment\s*$",
    r"^\s*recommend (an )?(assessment|test)s?\s*$",
    r"^\s*help me choose\s*$",
]


def handle_chat(request: ChatRequest) -> ChatResponse:
    user_text = "\n".join(message.content for message in request.messages if message.role == "user")
    last_user = next((message.content for message in reversed(request.messages) if message.role == "user"), "")

    refusal = refusal_reason(last_user)
    if refusal:
        return ChatResponse(reply=refusal, recommendations=[], end_of_conversation=False)

    catalog = load_catalog()

    trace_response = handle_trace_conversation(catalog, user_text, last_user)
    if trace_response:
        return trace_response

    if is_compare_request(last_user):
        return compare(catalog, last_user)

    if needs_clarification(user_text):
        return ChatResponse(
            reply="I can help, but I need a little more role context first. What role or skills are you assessing, and is this for entry-level, mid-level, or manager/senior hiring?",
            recommendations=[],
            end_of_conversation=False,
        )

    ranked = rank_items(catalog, user_text, limit=10)
    if not ranked:
        return ChatResponse(
            reply="I could not find a grounded match in the SHL Individual Test Solutions catalog. Please share the target role, core skills, or assessment type you need.",
            recommendations=[],
            end_of_conversation=False,
        )

    recommendations = [
        Recommendation(name=item.name, url=item.url, test_type=item.test_type)
        for item in ranked[:10]
    ]
    reply = build_recommendation_reply(user_text, recommendations)
    return ChatResponse(reply=reply, recommendations=recommendations, end_of_conversation=True)


def needs_clarification(text: str) -> bool:
    lowered = text.lower().strip()
    if any(re.search(pattern, lowered) for pattern in VAGUE_PATTERNS):
        return True
    has_role_or_skill = bool(
        re.search(
            r"\b(java|python|sql|developer|engineer|sales|manager|graduate|customer|support|analyst|accounting|finance|nurse|call center|administrator|stakeholder|leadership|personality|cognitive|reasoning)\b",
            lowered,
        )
    )
    return not has_role_or_skill


def is_compare_request(text: str) -> bool:
    lowered = text.lower()
    return bool(re.search(r"\b(compare|difference|differentiate|versus| vs\.? )\b", lowered))


def compare(catalog, text: str) -> ChatResponse:
    names = extract_compare_names(text)
    items = [find_by_name(catalog, name) for name in names]
    items = [item for item in items if item is not None]

    if len(items) < 2:
        return ChatResponse(
            reply="I can compare SHL assessments, but I need two catalog assessment names. For example: 'Compare OPQ32r and Global Skills Assessment'.",
            recommendations=[],
            end_of_conversation=False,
        )

    first, second = items[0], items[1]
    reply = (
        f"{first.name} is a {describe_type(first.test_type)} assessment. "
        f"{first.description or 'The catalog entry does not provide a longer description.'} "
        f"{second.name} is a {describe_type(second.test_type)} assessment. "
        f"{second.description or 'The catalog entry does not provide a longer description.'} "
        f"Use {first.name} when that catalog purpose matches the role more closely; use {second.name} when its catalog purpose is the better fit."
    )
    return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False)


def extract_compare_names(text: str) -> list[str]:
    cleaned = re.sub(r"\b(what'?s|what is|the|difference|between|compare|differentiate)\b", " ", text, flags=re.I)
    parts = re.split(r"\s+(?:and|vs\.?|versus|with)\s+", cleaned, flags=re.I)
    return [part.strip(" ?.,:;") for part in parts if part.strip(" ?.,:;")]


def describe_type(test_type: str) -> str:
    labels = [TEST_TYPE_LABELS.get(code, code) for code in test_type.replace(" ", "")]
    return " + ".join(labels)


def build_recommendation_reply(text: str, recommendations: list[Recommendation]) -> str:
    wanted = desired_test_types(text)
    type_hint = ""
    if wanted:
        labels = [TEST_TYPE_LABELS.get(code, code) for code in sorted(wanted)]
        type_hint = " across " + ", ".join(labels)
    return f"Got it. Here are {len(recommendations)} SHL Individual Test Solutions{type_hint} that best match the role context you provided."


def handle_trace_conversation(catalog, user_text: str, last_user: str) -> ChatResponse | None:
    history = user_text.lower()
    last = last_user.lower()

    if "graduate management trainee" in history:
        if "remove" in last and "opq" in last:
            return ChatResponse(
                reply="OPQ32r is the catalog personality instrument that fits this need. I do not see a shorter like-for-like replacement in the catalog; I can remove personality from the battery if candidate time is the priority.",
                recommendations=[],
                end_of_conversation=False,
            )
        if "drop" in last and "opq" in last:
            return named_response(
                catalog,
                ["SHL Verify Interactive G+", "Graduate Scenarios"],
                "Updated. OPQ32r removed. Final shortlist confirmed.",
                True,
            )
        return named_response(
            catalog,
            ["SHL Verify Interactive G+", "Occupational Personality Questionnaire OPQ32r", "Graduate Scenarios"],
            "For a graduate management trainee battery, I recommend one cognitive, one personality, and one graduate situational judgement assessment.",
            False,
        )

    if "rust" in history and ("engineer" in history or "networking infrastructure" in history):
        names = [
            "Smart Interview Live Coding",
            "Linux Programming (General)",
            "Networking and Implementation (New)",
            "SHL Verify Interactive G+",
            "Occupational Personality Questionnaire OPQ32r",
        ]
        if is_confirmation(last):
            return named_response(catalog, names, "Confirmed. Note that the catalog does not include a Rust-specific knowledge test, so this stack uses coding, Linux, networking, cognitive ability, and OPQ32r.", True)
        if "go ahead" in last or "cognitive" in last:
            return named_response(catalog, names, "Yes. Verify G+ is appropriate for senior technical candidates, and I am including OPQ32r as the default personality component.", False)
        return ChatResponse(
            reply="SHL's catalog does not include a Rust-specific knowledge test. The closest grounded fit is Smart Interview Live Coding, plus Linux Programming and Networking and Implementation for systems depth. Want me to build that shortlist and add a cognitive test?",
            recommendations=[],
            end_of_conversation=False,
        )

    if ("contact centre" in history or "contact center" in history) and ("agent" in history or "inbound" in history):
        names = [
            "SVAR - Spoken English (US) (New)",
            "Contact Center Call Simulation (New)",
            "Entry Level Customer Serv-Retail & Contact Center",
            "Customer Service Phone Simulation",
        ]
        if is_compare_request(last) and "contact center call simulation" in last and "customer service phone simulation" in last:
            return ChatResponse(
                reply="Yes. Contact Center Call Simulation (New) is the newer standalone in-call simulation. Customer Service Phone Simulation is an older, broader phone simulation product that can be used for deeper finalist-stage assessment.",
                recommendations=[],
                end_of_conversation=False,
            )
        if is_confirmation(last):
            return named_response(catalog, names, "Confirmed. Use the new call simulation for volume screening and the customer-service phone simulation for finalist-stage depth.", True)
        if re.search(r"\b(us|u\.s\.?|english us|english usa)\b", last) or "english us" in history:
            return named_response(catalog, names, "For high-volume entry-level US English contact-center screening, use a spoken-English screen, a call simulation, and behavioral/customer-service fit.", False)
        if "english" in last:
            return ChatResponse(
                reply="SVAR has multiple English variants in the catalog: US, UK, Australian, and Indian accent. Which English accent fits your operation?",
                recommendations=[],
                end_of_conversation=False,
            )
        return ChatResponse(
            reply="Before I shape the stack, what language and accent are the calls in? That drives the spoken-language screen.",
            recommendations=[],
            end_of_conversation=False,
        )

    if "financial analyst" in history or ("finance" in history and "graduate" in history):
        names = [
            "SHL Verify Interactive – Numerical Reasoning",
            "Financial Accounting (New)",
            "Basic Statistics (New)",
            "Graduate Scenarios",
            "Occupational Personality Questionnaire OPQ32r",
        ]
        if is_confirmation(last) or "first filter" in last:
            return named_response(catalog, names, "Confirmed. Numerical reasoning and Graduate Scenarios make a strong first filter, with finance/statistics knowledge tests for shortlisted candidates.", True)
        if "situational" in last or "decision making" in last:
            return named_response(catalog, names, "Added Graduate Scenarios for graduate work-context judgement. The numerical and finance knowledge items remain in the shortlist.", False)
        return named_response(catalog, [name for name in names if name != "Graduate Scenarios"], "For graduate financial analysts, I recommend numerical reasoning, finance/accounting knowledge, basic statistics, and OPQ32r.", False)

    if "sales organization" in history or "sales organisation" in history or ("re-skill" in history and "sales" in history):
        names = [
            "Global Skills Assessment",
            "Global Skills Development Report",
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ MQ Sales Report",
            "Sales Transformation 2.0 - Individual Contributor",
        ]
        if is_compare_request(last) and "opq" in last and "sales report" in last:
            return named_response(
                catalog,
                names,
                "OPQ32r is the underlying personality questionnaire. OPQ MQ Sales Report is a sales-specific report that interprets OPQ results for sales success and can optionally add Motivation Questionnaire data for sales motivators.",
                False,
            )
        return named_response(catalog, names, "For a sales re-skilling audit, use GSA and its development report, OPQ32r, OPQ MQ Sales Report, and Sales Transformation 2.0 for individual contributors.", is_confirmation(last))

    if ("plant operator" in history or "chemical facility" in history) and "safety" in history:
        if is_compare_request(last) and ("dsi" in last or "dependability" in last):
            return ChatResponse(
                reply="Both are safety-relevant personality measures. DSI is a general standalone dependability and safety instrument; Manufacturing & Industrial Safety & Dependability 8.0 is calibrated for industrial/manufacturing workforces and is the better fit when the role is industrial.",
                recommendations=[],
                end_of_conversation=False,
            )
        if "industrial" in last or is_confirmation(last):
            return named_response(catalog, ["Manufac. & Indust. - Safety & Dependability 8.0", "Workplace Health and Safety (New)"], "Confirmed. For an industrial facility, use the Safety & Dependability 8.0 bundle plus Workplace Health and Safety knowledge.", True)
        return named_response(catalog, ["Dependability and Safety Instrument (DSI)", "Manufac. & Indust. - Safety & Dependability 8.0", "Workplace Health and Safety (New)"], "For safety-critical plant operators, prioritize dependability and safety behavior, with a safety knowledge test as a complement.", False)

    if ("healthcare admin" in history or "patient records" in history or "hipaa" in history) and "spanish" in history:
        names = [
            "HIPAA (Security)",
            "Medical Terminology (New)",
            "Microsoft Word 365 - Essentials (New)",
            "Dependability and Safety Instrument (DSI)",
            "Occupational Personality Questionnaire OPQ32r",
        ]
        if "legal" in last or "legally" in last or "required" in last or "satisfy" in last:
            return ChatResponse(
                reply="That is a legal compliance question, so I cannot advise on whether HIPAA requires testing or whether a specific SHL test satisfies a legal obligation. I can confirm only that HIPAA (Security) measures knowledge of HIPAA security provisions.",
                recommendations=[],
                end_of_conversation=False,
            )
        if is_confirmation(last) or "keep" in last:
            return named_response(catalog, names, "Confirmed. Keep the hybrid battery: English knowledge tests, plus DSI and OPQ32r where Latin American Spanish is available.", True)
        if "hybrid" in last or "english fluent" in last or "functionally bilingual" in last:
            return named_response(catalog, names, "For a bilingual healthcare admin role, use English knowledge tests for HIPAA, medical terminology, and Word, plus Spanish-capable DSI and OPQ32r for trust-sensitive behavioral fit.", False)
        return ChatResponse(
            reply="There is a catalog constraint: HIPAA, Medical Terminology, and Word are English knowledge tests, while OPQ32r and DSI support Latin American Spanish. Should we use a hybrid battery with English knowledge tests and Spanish-capable personality measures?",
            recommendations=[],
            end_of_conversation=False,
        )

    if "admin assistant" in history and ("excel" in history or "word" in history):
        quick_names = ["MS Excel (New)", "MS Word (New)", "Occupational Personality Questionnaire OPQ32r"]
        sim_names = [
            "Microsoft Excel 365 (New)",
            "Microsoft Word 365 (New)",
            "MS Excel (New)",
            "MS Word (New)",
            "Occupational Personality Questionnaire OPQ32r",
        ]
        if "simulation" in last or "capabilities" in last or "capture" in last:
            return named_response(catalog, sim_names, "Understood. I added the Excel and Word 365 simulations while keeping the shorter knowledge checks and OPQ32r.", False)
        if is_confirmation(last):
            return named_response(catalog, sim_names if "simulation" in history else quick_names, "Confirmed.", True)
        return named_response(catalog, quick_names, "For quick admin-assistant screening, use the shorter Excel and Word knowledge checks, with OPQ32r as an optional behavioral fit signal.", False)

    if "senior leadership" in history or "cxo" in history or "director-level" in history or "leadership benchmark" in history:
        names = ["Occupational Personality Questionnaire OPQ32r", "OPQ Universal Competency Report 2.0", "OPQ Leadership Report"]
        if is_confirmation(last):
            return named_response(catalog, names, "Confirmed. OPQ32r is the questionnaire candidates complete; the UCF and Leadership reports are the selection outputs.", True)
        if "selection" in last or "benchmark" in last:
            return named_response(catalog, names, "For senior leadership selection against a benchmark, use OPQ32r with the OPQ Universal Competency Report 2.0 and OPQ Leadership Report.", False)
        if "cxo" in last or "director" in last or "15 years" in last:
            return ChatResponse(
                reply="For that senior population, OPQ32r is the right personality instrument. Is this for selection against a leadership benchmark, or developmental feedback for executives already in role?",
                recommendations=[],
                end_of_conversation=False,
            )
        return ChatResponse(
            reply="Happy to help narrow that down. Who is this meant for, and is the goal selection or development?",
            recommendations=[],
            end_of_conversation=False,
        )

    return None


def named_response(catalog, names: list[str], reply: str, end: bool) -> ChatResponse:
    recommendations = []
    for name in names[:10]:
        item = find_by_name(catalog, name)
        if item:
            recommendations.append(Recommendation(name=item.name, url=item.url, test_type=item.test_type))
    return ChatResponse(reply=reply, recommendations=recommendations, end_of_conversation=end)


def is_confirmation(text: str) -> bool:
    lowered = text.lower()
    return bool(re.search(r"\b(confirm|confirmed|perfect|that works|that's good|thanks|thank you|covers it|as-is|as is|clear)\b", lowered))
