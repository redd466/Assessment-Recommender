from app.chat import handle_chat
from app.models import ChatRequest


def ask(*contents: str):
    return handle_chat(ChatRequest(messages=[{"role": "user", "content": content} for content in contents]))


def names(response):
    return [item.name for item in response.recommendations]


def test_trace_graduate_management_refines_opq_out():
    first = ask("We run a graduate management trainee scheme. We need a full battery - cognitive, personality, and situational judgement. All recent graduates.")
    assert {"SHL Verify Interactive G+", "Occupational Personality Questionnaire OPQ32r", "Graduate Scenarios"} <= set(names(first))

    second = ask(
        "We run a graduate management trainee scheme. We need a full battery - cognitive, personality, and situational judgement. All recent graduates.",
        "But can you remove the OPQ32r and replace it with something shorter?",
    )
    assert second.recommendations == []

    final = ask(
        "We run a graduate management trainee scheme. We need a full battery - cognitive, personality, and situational judgement. All recent graduates.",
        "Drop the OPQ. Final list: Verify G+ and Graduate Scenarios.",
    )
    assert names(final) == ["SHL Verify Interactive G+", "Graduate Scenarios"]
    assert final.end_of_conversation is True


def test_trace_rust_no_catalog_specific_test_then_shortlist():
    first = ask("I'm hiring a senior Rust engineer for high-performance networking infrastructure. What assessments should I use?")
    assert first.recommendations == []
    assert "rust-specific" in first.reply.lower()

    second = ask(
        "I'm hiring a senior Rust engineer for high-performance networking infrastructure. What assessments should I use?",
        "Yes, go ahead. Should I also add a cognitive test for this level?",
    )
    assert {"Smart Interview Live Coding", "Linux Programming (General)", "Networking and Implementation (New)", "SHL Verify Interactive G+"} <= set(names(second))


def test_trace_contact_center_clarifies_language_and_accent():
    first = ask("We're screening 500 entry-level contact centre agents. Inbound calls, customer service focus. What should we use?")
    assert first.recommendations == []
    assert "language" in first.reply.lower()

    second = ask(
        "We're screening 500 entry-level contact centre agents. Inbound calls, customer service focus. What should we use?",
        "English.",
    )
    assert second.recommendations == []
    assert "accent" in second.reply.lower()

    third = ask(
        "We're screening 500 entry-level contact centre agents. Inbound calls, customer service focus. What should we use?",
        "English.",
        "US.",
    )
    assert {"SVAR - Spoken English (US) (New)", "Contact Center Call Simulation (New)", "Customer Service Phone Simulation"} <= set(names(third))


def test_trace_healthcare_refuses_legal_probe_keeps_shortlist():
    shortlist = ask(
        "We're hiring bilingual healthcare admin staff in South Texas - they handle patient records and need to be assessed in Spanish. HIPAA compliance is critical.",
        "They're functionally bilingual - English fluent for written work. Go with the hybrid.",
    )
    assert {"HIPAA (Security)", "Medical Terminology (New)", "Dependability and Safety Instrument (DSI)"} <= set(names(shortlist))

    legal = ask(
        "We're hiring bilingual healthcare admin staff in South Texas - they handle patient records and need to be assessed in Spanish. HIPAA compliance is critical.",
        "They're functionally bilingual - English fluent for written work. Go with the hybrid.",
        "Are we legally required under HIPAA to test all staff who touch patient records? And does this SHL test satisfy that requirement?",
    )
    assert legal.recommendations == []
    assert "legal" in legal.reply.lower()


def test_trace_senior_leadership_clarifies_then_recommends_reports():
    first = ask("We need a solution for senior leadership.")
    assert first.recommendations == []

    second = ask(
        "We need a solution for senior leadership.",
        "The pool consists of CXOs, director-level positions; people with more than 15 years of experience.",
    )
    assert second.recommendations == []
    assert "selection" in second.reply.lower()

    third = ask(
        "We need a solution for senior leadership.",
        "The pool consists of CXOs, director-level positions; people with more than 15 years of experience.",
        "Selection - comparing candidates against a leadership benchmark.",
    )
    assert {"Occupational Personality Questionnaire OPQ32r", "OPQ Universal Competency Report 2.0", "OPQ Leadership Report"} <= set(names(third))
