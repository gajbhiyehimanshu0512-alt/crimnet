"""
nlp/custom_ner_rules.py — Indian-context custom NER patterns for spaCy.
Adds recognition for: vehicle plates, FIR numbers, Aadhaar, PAN, phone numbers,
and common Indian criminal network terminology.
"""

import re
import spacy
from spacy.language import Language
from spacy.matcher import Matcher
from typing import List


# ── Regex Patterns ────────────────────────────────────────────────────────────

PATTERNS = {
    # Indian vehicle registration: MH-01-AB-1234 or MH01AB1234
    "VEHICLE_PLATE": re.compile(
        r"\b[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{1,4}\b", re.IGNORECASE
    ),
    # FIR number: FIR No. 123/2024 or CR No. 456/24
    "FIR_NUMBER": re.compile(
        r"\b(?:FIR|CR|RC|CRN)\.?\s*(?:No\.?|#)?\s*\d{1,6}[/\-]\d{2,4}\b", re.IGNORECASE
    ),
    # Aadhaar: 12-digit number (sometimes formatted)
    "AADHAAR": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    # PAN card: ABCDE1234F
    "PAN": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    # Indian mobile numbers: +91-XXXXXXXXXX or 10-digit starting with 6-9
    "PHONE_IN": re.compile(r"(?:\+91[-\s]?)?[6-9]\d{9}\b"),
    # Bank account numbers (9–18 digits)
    "BANK_ACCOUNT": re.compile(r"\b\d{9,18}\b"),
    # IFSC code
    "IFSC": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
}

ENTITY_RULER_PATTERNS = [
    # Gang / syndicate / criminal org keywords
    {"label": "CRIMINAL_ORG", "pattern": [{"LOWER": {"IN": ["syndicate", "gang", "cartel", "mafia", "network"]}}]},
    {"label": "CRIMINAL_ORG", "pattern": [{"LOWER": "don"}, {"IS_ALPHA": True}]},
    # Roles
    {"label": "CRIMINAL_ROLE", "pattern": [{"LOWER": {"IN": [
        "kingpin", "handler", "courier", "hawala", "informant",
        "hitman", "extortionist", "don", "bhai", "boss"
    ]}}]},
    # Drugs
    {"label": "CONTRABAND", "pattern": [{"LOWER": {"IN": [
        "heroin", "cocaine", "smack", "charas", "ganja", "methamphetamine",
        "mdma", "ecstasy", "brown-sugar"
    ]}}]},
]


def add_custom_patterns(nlp: Language) -> Language:
    """
    Registers a custom pipeline component that adds Indian-context
    entity recognition to the spaCy NLP pipeline.
    """

    if "indian_ner_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler", name="indian_ner_ruler", before="ner")
        ruler.add_patterns(ENTITY_RULER_PATTERNS)

    if "regex_ner" not in nlp.pipe_names:
        @Language.component("regex_ner")
        def regex_ner(doc):
            new_ents = list(doc.ents)
            for label, pattern in PATTERNS.items():
                for match in pattern.finditer(doc.text):
                    start_char, end_char = match.start(), match.end()
                    span = doc.char_span(start_char, end_char, label=label)
                    if span is not None:
                        new_ents.append(span)
            # Filter overlapping spans (keep longest)
            from spacy.util import filter_spans
            doc.ents = filter_spans(new_ents)
            return doc

        nlp.add_pipe("regex_ner", after="ner")

    return nlp


def extract_regex_entities(text: str) -> List[dict]:
    """
    Pure regex extraction (no spaCy) for quick entity detection.
    Returns list of {text, label, start, end}.
    """
    results = []
    for label, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            results.append({
                "text": m.group(),
                "label": label,
                "start": m.start(),
                "end": m.end(),
            })
    return results
