"""
ingestion/social_parser.py — Parser for social media intelligence (SOCMINT) reports.
Handles structured JSON exports and free-text intel reports.
"""

import logging
import json
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

HANDLE_RE   = re.compile(r"@([A-Za-z0-9_]{2,30})")
HASHTAG_RE  = re.compile(r"#([A-Za-z0-9_]+)")
URL_RE      = re.compile(r"https?://[^\s]+")
PHONE_RE    = re.compile(r"(?:\+91[-\s]?)?[6-9]\d{9}\b")
LOCATION_RE = re.compile(r"(?:location|place|city|from)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", re.IGNORECASE)


class SocialParser:
    """Parses social media intelligence reports."""

    def parse_text(self, text: str, source_name: str = "SOCIAL") -> Dict[str, Any]:
        handles  = HANDLE_RE.findall(text)
        hashtags = HASHTAG_RE.findall(text)
        urls     = URL_RE.findall(text)
        phones   = PHONE_RE.findall(text)
        locations = LOCATION_RE.findall(text)

        entities = []
        for h in set(handles):
            entities.append({"name": f"@{h}", "entity_type": "Person", "social_handle": h})
        for p in set(phones):
            entities.append({"name": p, "entity_type": "PhoneNumber", "number": p})
        for l in set(locations):
            entities.append({"name": l, "entity_type": "Location"})

        relationships = []
        handle_names = [f"@{h}" for h in set(handles)]
        for i, a in enumerate(handle_names):
            for b in handle_names[i+1:]:
                relationships.append({
                    "source_name": a, "target_name": b,
                    "relation_type": "ASSOCIATED_WITH",
                    "properties": {"source": "social_media", "hashtags": hashtags},
                })

        return {
            "source_type": "SOCIAL",
            "source_name": source_name,
            "raw_text": text,
            "handles": handles,
            "hashtags": hashtags,
            "urls": urls,
            "phones": phones,
            "locations": locations,
            "entities": entities,
            "relationships": relationships,
        }

    def parse_json(self, data: Dict | List, source_name: str = "SOCIAL_JSON") -> Dict[str, Any]:
        """Parse structured JSON social media export (e.g. scraped post data)."""
        if isinstance(data, list):
            all_text = " ".join(
                str(item.get("text", item.get("content", item.get("message", ""))))
                for item in data
            )
        else:
            all_text = str(data)
        return self.parse_text(all_text, source_name)


social_parser = SocialParser()
