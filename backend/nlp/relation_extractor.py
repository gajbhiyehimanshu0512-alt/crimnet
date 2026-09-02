"""
nlp/relation_extractor.py — Extracts relationships between entities.
Uses spaCy dependency parsing for rule-based extraction, with an optional
LLM-assisted zero-shot pass for complex / implicit relationships.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Verb-pattern → Relationship type mapping ──────────────────────────────────

VERB_TO_REL = {
    # Communication
    "called": "CALLED",
    "contacted": "CALLED",
    "texted": "CALLED",
    "messaged": "CALLED",
    "spoke": "CALLED",
    # Presence / meeting
    "met": "MET_WITH",
    "meeting": "MET_WITH",
    "accompanied": "ASSOCIATED_WITH",
    "visited": "PRESENT_AT",
    "seen": "PRESENT_AT",
    "spotted": "PRESENT_AT",
    "observed": "PRESENT_AT",
    "arrived": "PRESENT_AT",
    "travelled": "TRAVELED_TO",
    "traveled": "TRAVELED_TO",
    # Affiliation
    "member": "MEMBER_OF",
    "associate": "ASSOCIATED_WITH",
    "associated": "ASSOCIATED_WITH",
    "works": "MEMBER_OF",
    "operates": "MEMBER_OF",
    "belongs": "MEMBER_OF",
    # Finance
    "transferred": "TRANSFERRED_TO",
    "sent": "TRANSFERRED_TO",
    "paid": "TRANSFERRED_TO",
    "received": "TRANSFERRED_TO",
    "deposited": "TRANSFERRED_TO",
    # Ownership
    "owns": "OWNS",
    "owned": "OWNS",
    "registered": "OWNS",
    "controls": "OWNS",
    # Legal
    "accused": "CO_ACCUSED_IN",
    "arrested": "CO_ACCUSED_IN",
    "charged": "CO_ACCUSED_IN",
}


class RelationExtractor:
    """
    Extracts subject-predicate-object triples from text and maps them
    to typed graph relationships.
    """

    def extract(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        use_llm: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Extract relationships from text given the list of already-extracted entities.

        Args:
            text: Raw input text.
            entities: List of entity dicts from EntityExtractor.
            use_llm: Whether to augment with LLM zero-shot extraction.

        Returns:
            List of relationship dicts:
            {source_name, target_name, relation_type, properties, confidence}
        """
        relationships = []

        # Build name set for fast lookup
        entity_names = {e["name"].lower(): e["name"] for e in entities}

        # 1. Dependency-parse based extraction
        dep_rels = self._dependency_extract(text, entity_names)
        relationships.extend(dep_rels)

        # 2. Co-occurrence heuristic: entities in same sentence → ASSOCIATED_WITH
        cooc_rels = self._cooccurrence_extract(text, entities)
        relationships.extend(cooc_rels)

        # 3. Optional LLM zero-shot
        if use_llm:
            llm_rels = self._llm_extract(text, entities)
            relationships.extend(llm_rels)

        # Deduplicate
        seen = set()
        unique = []
        for r in relationships:
            key = (r["source_name"], r["target_name"], r["relation_type"])
            if key not in seen:
                seen.add(key)
                unique.append(r)

        logger.info(f"Extracted {len(unique)} relationships")
        return unique

    def _dependency_extract(
        self, text: str, entity_names: Dict[str, str]
    ) -> List[Dict]:
        """Rule-based extraction using spaCy dependency parse."""
        try:
            from nlp.entity_extractor import _get_nlp
            nlp = _get_nlp()
            doc = nlp(text[:500_000])
        except Exception as e:
            logger.warning(f"spaCy dependency parse failed: {e}")
            return []

        results = []
        for sent in doc.sents:
            sent_ents = [
                tok for tok in sent
                if tok.text.lower() in entity_names
            ]
            if len(sent_ents) < 2:
                continue

            for token in sent:
                verb = token.lemma_.lower()
                if token.pos_ in ("VERB", "NOUN") and verb in VERB_TO_REL:
                    rel_type = VERB_TO_REL[verb]
                    subj = self._find_subject(token, entity_names)
                    obj  = self._find_object(token, entity_names)
                    if subj and obj and subj != obj:
                        results.append({
                            "source_name": entity_names[subj],
                            "target_name": entity_names[obj],
                            "relation_type": rel_type,
                            "properties": {"verb": verb, "sentence": sent.text[:200]},
                            "confidence": 0.75,
                        })
        return results

    def _find_subject(self, token, entity_names: Dict[str, str]) -> Optional[str]:
        """Walk up the dependency tree to find the subject entity."""
        for child in token.subtree:
            if child.dep_ in ("nsubj", "nsubjpass") and child.text.lower() in entity_names:
                return child.text.lower()
        return None

    def _find_object(self, token, entity_names: Dict[str, str]) -> Optional[str]:
        """Walk the dependency tree to find the object entity."""
        for child in token.subtree:
            if child.dep_ in ("dobj", "pobj", "attr", "conj") and child.text.lower() in entity_names:
                return child.text.lower()
        return None

    def _cooccurrence_extract(
        self, text: str, entities: List[Dict]
    ) -> List[Dict]:
        """
        If two persons / orgs appear in the same sentence, create a weak
        ASSOCIATED_WITH relationship (low confidence, high recall).
        """
        try:
            from nlp.entity_extractor import _get_nlp
            nlp = _get_nlp()
            doc = nlp(text[:500_000])
        except Exception:
            return []

        entity_names = {e["name"].lower(): e for e in entities}
        results = []

        for sent in doc.sents:
            found = []
            for token in sent:
                if token.text.lower() in entity_names:
                    e = entity_names[token.text.lower()]
                    if e["entity_type"] in ("Person", "Organization"):
                        found.append(e["name"])
            # Pair-wise
            found = list(set(found))
            for i in range(len(found)):
                for j in range(i + 1, len(found)):
                    results.append({
                        "source_name": found[i],
                        "target_name": found[j],
                        "relation_type": "ASSOCIATED_WITH",
                        "properties": {"sentence": sent.text[:200]},
                        "confidence": 0.5,
                    })
        return results

    def _llm_extract(self, text: str, entities: List[Dict]) -> List[Dict]:
        """
        LLM zero-shot relation extraction.
        Prompts the local LLM to output structured JSON triples.
        """
        try:
            from langchain_ollama import OllamaLLM
            from langchain.prompts import PromptTemplate
            from config import settings
            import json

            entity_list = ", ".join(set(e["name"] for e in entities[:20]))

            prompt_text = f"""You are a criminal intelligence analyst.
Given the following text, extract relationships between these entities: {entity_list}

Text:
\"\"\"
{text[:2000]}
\"\"\"

Output ONLY a JSON array. Each item must have:
- "source": entity name
- "target": entity name  
- "relation": one of [CALLED, MET_WITH, ASSOCIATED_WITH, PRESENT_AT, TRANSFERRED_TO, OWNS, MEMBER_OF, CO_ACCUSED_IN, TRAVELED_TO]
- "evidence": brief quote from text

Example: [{{"source": "John", "target": "Mumbai", "relation": "PRESENT_AT", "evidence": "John was seen in Mumbai"}}]

JSON:"""

            llm = OllamaLLM(base_url=settings.ollama_url, model=settings.ollama_model)
            response = llm.invoke(prompt_text)

            # Extract JSON from response
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if not json_match:
                return []

            triples = json.loads(json_match.group())
            results = []
            for t in triples:
                if t.get("source") and t.get("target") and t.get("relation"):
                    results.append({
                        "source_name": t["source"],
                        "target_name": t["target"],
                        "relation_type": t["relation"],
                        "properties": {"evidence": t.get("evidence", "")},
                        "confidence": 0.85,
                    })
            logger.info(f"LLM extracted {len(results)} relationships")
            return results

        except Exception as e:
            logger.warning(f"LLM relation extraction failed: {e}")
            return []


# ── Singleton ─────────────────────────────────────────────────────────────────
relation_extractor = RelationExtractor()
