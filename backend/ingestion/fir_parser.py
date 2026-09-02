"""
ingestion/fir_parser.py — Parser for First Information Reports (FIRs).
Handles PDF and plain-text FIR documents. Extracts structured data and
passes text to the NLP pipeline.
"""

import logging
import re
import io
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class FIRParser:
    """Parses FIR (First Information Report) documents."""

    # Regex patterns for structured FIR fields
    FIR_NUMBER_RE  = re.compile(r"FIR\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d+[/\-]\d+)", re.IGNORECASE)
    DATE_RE        = re.compile(r"Date\s*[:\-]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", re.IGNORECASE)
    POLICE_STN_RE  = re.compile(r"Police\s*Station\s*[:\-]\s*([^\n,]+)", re.IGNORECASE)
    COMPLAINANT_RE = re.compile(r"Complainant\s*[:\-]\s*([^\n,]+)", re.IGNORECASE)
    ACCUSED_RE     = re.compile(r"Accused\s*[:\-]\s*([^\n]+)", re.IGNORECASE)
    OFFENCE_RE     = re.compile(r"(?:Section|Offence|IPC)\s*[:\-]\s*([^\n]+)", re.IGNORECASE)
    LOCATION_RE    = re.compile(r"(?:Place|Location|Scene)\s*of\s*(?:Occurrence|Offence|Incident)\s*[:\-]\s*([^\n]+)", re.IGNORECASE)
    VEHICLE_RE     = re.compile(r"\b[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{1,4}\b", re.IGNORECASE)

    def parse_text(self, text: str, source_name: str = "FIR") -> Dict[str, Any]:
        """Extract structured fields from raw FIR text."""
        result = {
            "source_type": "FIR",
            "source_name": source_name,
            "raw_text": text,
            "fir_number": self._extract_first(self.FIR_NUMBER_RE, text),
            "date": self._extract_first(self.DATE_RE, text),
            "police_station": self._extract_first(self.POLICE_STN_RE, text),
            "complainant": self._extract_first(self.COMPLAINANT_RE, text),
            "accused_names": self._extract_accused(text),
            "offence_sections": self._extract_first(self.OFFENCE_RE, text),
            "location": self._extract_first(self.LOCATION_RE, text),
            "vehicles": self.VEHICLE_RE.findall(text),
        }
        logger.info(f"Parsed FIR: {result.get('fir_number', 'Unknown')} from {source_name}")
        return result

    def parse_pdf(self, file_bytes: bytes, filename: str = "fir.pdf") -> Dict[str, Any]:
        """Extract text from PDF bytes and parse."""
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        except Exception as e:
            logger.warning(f"pdfplumber failed ({e}), trying PyPDF2")
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                text = "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception as e2:
                logger.error(f"PDF parsing failed: {e2}")
                return {"error": str(e2), "source_type": "FIR", "raw_text": ""}

        return self.parse_text(text, source_name=filename)

    def parse_file(self, path: str) -> Dict[str, Any]:
        """Auto-detect format and parse a file from disk."""
        p = Path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        if p.suffix.lower() == ".pdf":
            return self.parse_pdf(p.read_bytes(), p.name)
        else:
            return self.parse_text(p.read_text(encoding="utf-8", errors="ignore"), p.name)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_first(self, pattern: re.Pattern, text: str) -> Optional[str]:
        m = pattern.search(text)
        return m.group(1).strip() if m else None

    def _extract_accused(self, text: str) -> list:
        """Extract multiple accused names from an FIR."""
        accused_section = re.search(
            r"Accused\s*[:\-]\s*(.*?)(?:\n\n|\Z)", text, re.IGNORECASE | re.DOTALL
        )
        if not accused_section:
            return []
        raw = accused_section.group(1)
        # Split on common delimiters
        names = re.split(r"[,;\n]", raw)
        return [n.strip() for n in names if n.strip() and len(n.strip()) > 2]


# ── Singleton ─────────────────────────────────────────────────────────────────
fir_parser = FIRParser()
