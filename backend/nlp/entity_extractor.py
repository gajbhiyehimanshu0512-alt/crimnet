"""
nlp/entity_extractor.py — Named Entity Recognition pipeline.
Uses spaCy (transformer model) + custom Indian-context patterns to extract
all relevant entities from raw criminal / intelligence documents.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy-load spaCy to avoid slow startup in tests / simple imports
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        from config import settings
        from nlp.custom_ner_rules import add_custom_patterns

        try:
            _nlp = spacy.load(settings.spacy_model)
            logger.info(f"Loaded spaCy model: {settings.spacy_model}")
        except OSError:
            logger.warning(
                f"Model {settings.spacy_model} not found, falling back to {settings.spacy_model_fallback}"
            )
            try:
                _nlp = spacy.load(settings.spacy_model_fallback)
            except OSError:
                logger.error("No spaCy model available. Run: python -m spacy download en_core_web_sm")
                raise

        _nlp = add_custom_patterns(_nlp)
    return _nlp


# ── Label → entity_type mapping ───────────────────────────────────────────────

SPACY_LABEL_MAP = {
    "PERSON":        "Person",
    "ORG":           "Organization",
    "GPE":           "Location",
    "LOC":           "Location",
    "FAC":           "Location",
    "VEHICLE_PLATE": "Vehicle",
    "FIR_NUMBER":    "Event",
    "PHONE_IN":      "PhoneNumber",
    "PHONE":         "PhoneNumber",
    "AADHAAR":       "Person",
    "PAN":           "Person",
    "BANK_ACCOUNT":  "BankAccount",
    "CRIMINAL_ORG":  "Organization",
    "CRIMINAL_ROLE": "Person",
    "CONTRABAND":    "Event",
}


class EntityExtractor:
    """Extracts named entities from raw text using spaCy + custom rules."""

    def extract(self, text: str, source_doc: str = "") -> List[Dict[str, Any]]:
        """
        Run full NER pipeline on text.

        Returns:
            List of entity dicts:
            {name, entity_type, label, start_char, end_char, context, source_doc}
        """
        if not text or not text.strip():
            return []

        nlp = _get_nlp()
        doc = nlp(text[:1_000_000])  # Cap at 1M chars

        seen: Dict[str, Dict] = {}
        for ent in doc.ents:
            entity_type = SPACY_LABEL_MAP.get(ent.label_, None)
            if entity_type is None:
                continue

            name = ent.text.strip()
            if not name or len(name) < 2:
                continue

            # Deduplicate by normalised name + type
            key = f"{entity_type}:{name.lower()}"
            if key not in seen:
                context_start = max(0, ent.start_char - 80)
                context_end   = min(len(text), ent.end_char + 80)
                seen[key] = {
                    "name": name,
                    "entity_type": entity_type,
                    "spacy_label": ent.label_,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                    "context": text[context_start:context_end].replace("\n", " "),
                    "source_doc": source_doc,
                    "aliases": [],
                }
            else:
                # Track alternative spellings as aliases
                if name not in seen[key]["aliases"] and name != seen[key]["name"]:
                    seen[key]["aliases"].append(name)

        entities = list(seen.values())
        logger.info(f"Extracted {len(entities)} entities from '{source_doc}'")
        return entities

    def extract_batch(self, texts: List[str], source_docs: Optional[List[str]] = None) -> List[List[Dict]]:
        """Batch extraction using spaCy's pipe() for efficiency."""
        nlp = _get_nlp()
        docs = list(nlp.pipe(texts, batch_size=16))
        results = []
        for i, doc in enumerate(docs):
            src = (source_docs or [])[i] if source_docs and i < len(source_docs) else ""
            # Reuse single-doc logic
            fake_text = texts[i]
            entities = self.extract(fake_text, src)
            results.append(entities)
        return results

    # ── Convenience helpers ───────────────────────────────────────────────────

    def extract_persons(self, text: str) -> List[str]:
        return [e["name"] for e in self.extract(text) if e["entity_type"] == "Person"]

    def extract_locations(self, text: str) -> List[str]:
        return [e["name"] for e in self.extract(text) if e["entity_type"] == "Location"]

    def extract_phones(self, text: str) -> List[str]:
        return [e["name"] for e in self.extract(text) if e["entity_type"] == "PhoneNumber"]

    def extract_vehicles(self, text: str) -> List[str]:
        return [e["name"] for e in self.extract(text) if e["entity_type"] == "Vehicle"]


# ── Singleton ─────────────────────────────────────────────────────────────────
entity_extractor = EntityExtractor()
