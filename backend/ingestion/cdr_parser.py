"""
ingestion/cdr_parser.py — Parser for Call Detail Records (CDRs).
Handles CSV/Excel CDR files and builds phone-to-phone call edges.
"""

import logging
import io
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

# Expected column aliases for flexible header matching
COLUMN_ALIASES = {
    "caller":    ["caller", "calling_number", "a_party", "from", "msisdn_a", "phone_a"],
    "receiver":  ["receiver", "called_number", "b_party", "to", "msisdn_b", "phone_b"],
    "timestamp": ["date", "datetime", "timestamp", "call_date", "start_time", "date_time"],
    "duration":  ["duration", "call_duration", "seconds", "duration_sec"],
    "tower":     ["tower", "cell_id", "bts", "cell", "tower_id", "location", "bts_id"],
    "call_type": ["call_type", "type", "direction", "voice_sms"],
}


class CDRParser:
    """Parses Call Detail Records from CSV or Excel files."""

    def parse_dataframe(self, df: pd.DataFrame, source_name: str = "CDR") -> Dict[str, Any]:
        """Normalize a DataFrame into standardized CDR records."""
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        mapping = {}
        for std, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in df.columns:
                    mapping[std] = alias
                    break

        records = []
        for _, row in df.iterrows():
            caller   = str(row.get(mapping.get("caller", ""), "")).strip()
            receiver = str(row.get(mapping.get("receiver", ""), "")).strip()
            ts       = str(row.get(mapping.get("timestamp", ""), "")).strip()
            duration = row.get(mapping.get("duration", ""), 0)
            tower    = str(row.get(mapping.get("tower", ""), "")).strip()
            ctype    = str(row.get(mapping.get("call_type", ""), "voice")).strip()

            if not caller or not receiver:
                continue

            records.append({
                "caller": caller,
                "receiver": receiver,
                "timestamp": ts,
                "duration_sec": float(duration) if duration else 0,
                "tower_location": tower,
                "call_type": ctype,
                "source_doc": source_name,
            })

        logger.info(f"Parsed {len(records)} CDR records from '{source_name}'")
        return {
            "source_type": "CDR",
            "source_name": source_name,
            "total_records": len(records),
            "records": records,
            # Derived entities
            "entities": self._derive_entities(records),
            "relationships": self._derive_relationships(records),
        }

    def parse_csv(self, file_bytes: bytes, filename: str = "cdr.csv") -> Dict[str, Any]:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
        except Exception as e:
            logger.error(f"CSV parse error: {e}")
            return {"error": str(e)}
        return self.parse_dataframe(df, filename)

    def parse_excel(self, file_bytes: bytes, filename: str = "cdr.xlsx") -> Dict[str, Any]:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception as e:
            logger.error(f"Excel parse error: {e}")
            return {"error": str(e)}
        return self.parse_dataframe(df, filename)

    def _derive_entities(self, records: List[Dict]) -> List[Dict]:
        """Build unique PhoneNumber entity list from CDR records."""
        phones = set()
        for r in records:
            phones.add(r["caller"])
            phones.add(r["receiver"])
        return [{"name": p, "entity_type": "PhoneNumber", "number": p} for p in phones if p]

    def _derive_relationships(self, records: List[Dict]) -> List[Dict]:
        """Build CALLED relationships from CDR records."""
        rels = []
        for r in records:
            rels.append({
                "source_name": r["caller"],
                "target_name": r["receiver"],
                "relation_type": "CALLED",
                "properties": {
                    "timestamp": r["timestamp"],
                    "duration_sec": r["duration_sec"],
                    "tower_location": r["tower_location"],
                    "call_type": r["call_type"],
                },
            })
        return rels


# ── Singleton ─────────────────────────────────────────────────────────────────
cdr_parser = CDRParser()
