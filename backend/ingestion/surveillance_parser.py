"""
ingestion/surveillance_parser.py — Parser for surveillance / watch reports.
Handles structured and free-text surveillance logs.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

PERSON_RE   = re.compile(r"(?:Subject|Suspect|Person|Individual)\s*[:\-]\s*([^\n,]+)", re.IGNORECASE)
LOCATION_RE = re.compile(r"(?:Location|Place|Venue|Spotted at)\s*[:\-]\s*([^\n,]+)", re.IGNORECASE)
TIME_RE     = re.compile(r"(?:Time|At)\s*[:\-]\s*(\d{1,2}[:\-]\d{2}\s*(?:AM|PM)?)", re.IGNORECASE)
DATE_RE     = re.compile(r"(?:Date)\s*[:\-]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", re.IGNORECASE)
VEHICLE_RE  = re.compile(r"\b[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{1,4}\b", re.IGNORECASE)
ACTIVITY_RE = re.compile(r"Activity\s*[:\-]\s*([^\n]+)", re.IGNORECASE)
ASSOCIATE_RE = re.compile(r"(?:Accompan|With|Associate)[a-z]*\s*[:\-]?\s*([A-Z][a-z]+ [A-Z][a-z]+)", re.IGNORECASE)


class SurveillanceParser:
    """Parses surveillance / watch report documents."""

    def parse_text(self, text: str, source_name: str = "SURVEILLANCE") -> Dict[str, Any]:
        persons   = self._extract_all(PERSON_RE, text)
        locations = self._extract_all(LOCATION_RE, text)
        vehicles  = VEHICLE_RE.findall(text)
        associates = self._extract_all(ASSOCIATE_RE, text)
        all_persons = list(set(persons + associates))

        result = {
            "source_type": "SURVEILLANCE",
            "source_name": source_name,
            "raw_text": text,
            "persons": all_persons,
            "locations": locations,
            "vehicles": vehicles,
            "date": self._extract_first(DATE_RE, text),
            "time": self._extract_first(TIME_RE, text),
            "activity": self._extract_first(ACTIVITY_RE, text),
            "entities": self._build_entities(all_persons, locations, vehicles),
            "relationships": self._build_relationships(all_persons, locations),
        }
        logger.info(f"Parsed surveillance report: {len(all_persons)} persons, {len(locations)} locations")
        return result

    def parse_file(self, path: str) -> Dict[str, Any]:
        p = Path(path)
        return self.parse_text(p.read_text(encoding="utf-8", errors="ignore"), p.name)

    def _extract_all(self, pattern: re.Pattern, text: str) -> List[str]:
        return [m.group(1).strip() for m in pattern.finditer(text) if m.group(1).strip()]

    def _extract_first(self, pattern: re.Pattern, text: str):
        m = pattern.search(text)
        return m.group(1).strip() if m else None

    def _build_entities(self, persons: List[str], locations: List[str], vehicles: List[str]) -> List[Dict]:
        entities = []
        for p in persons:
            entities.append({"name": p, "entity_type": "Person"})
        for l in locations:
            entities.append({"name": l, "entity_type": "Location"})
        for v in vehicles:
            entities.append({"name": v, "entity_type": "Vehicle", "plate_number": v})
        return entities

    def _build_relationships(self, persons: List[str], locations: List[str]) -> List[Dict]:
        rels = []
        for person in persons:
            for loc in locations:
                rels.append({
                    "source_name": person,
                    "target_name": loc,
                    "relation_type": "PRESENT_AT",
                    "properties": {},
                })
            for other_person in persons:
                if person != other_person:
                    rels.append({
                        "source_name": person,
                        "target_name": other_person,
                        "relation_type": "ASSOCIATED_WITH",
                        "properties": {"source": "surveillance"},
                    })
        return rels


surveillance_parser = SurveillanceParser()
