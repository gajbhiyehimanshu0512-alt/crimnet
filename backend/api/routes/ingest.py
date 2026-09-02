"""
api/routes/ingest.py — Data ingestion endpoints.
Handles file uploads and text input for all supported source types.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from config import settings
from ingestion.fir_parser import fir_parser
from ingestion.cdr_parser import cdr_parser
from ingestion.financial_parser import financial_parser
from ingestion.surveillance_parser import surveillance_parser
from ingestion.social_parser import social_parser
from nlp.entity_extractor import entity_extractor
from nlp.relation_extractor import relation_extractor
from graph.graph_builder import graph_builder
from ai.rag_engine import rag_engine

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".xlsx", ".xls", ".json", ".doc", ".docx"}


def _save_upload(file: UploadFile) -> tuple[bytes, str]:
    """Save uploaded file and return (bytes, filename)."""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    file_bytes = file.file.read()
    save_path = UPLOAD_DIR / f"{uuid.uuid4()}{ext}"
    save_path.write_bytes(file_bytes)
    return file_bytes, file.filename


async def _process_text_through_nlp(text: str, source_name: str, use_llm: bool = False) -> dict:
    """Run NLP extraction + graph storage on raw text."""
    entities = entity_extractor.extract(text, source_doc=source_name)
    relationships = relation_extractor.extract(text, entities, use_llm=use_llm)

    result = await graph_builder.ingest_extraction_result(
        {"entities": entities, "relationships": relationships, "document_text": text},
        source_doc=source_name,
    )

    # Store document in ChromaDB for RAG
    await rag_engine.add_document(
        text=text[:5000],
        doc_id=f"{source_name}_{uuid.uuid4().hex[:8]}",
        metadata={"source": source_name},
    )

    return {
        "source": source_name,
        "entities_extracted": len(entities),
        "entities_stored": result["entities_stored"],
        "relationships_stored": result["relationships_stored"],
        "entity_ids": result["entity_ids"],
    }


# ── FIR Endpoint ──────────────────────────────────────────────────────────────

@router.post("/fir", summary="Ingest First Information Report (FIR)")
async def ingest_fir(
    file: UploadFile = File(...),
    use_llm: bool = Form(default=False),
):
    """Upload a FIR document (PDF or TXT) for processing."""
    file_bytes, filename = _save_upload(file)
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        parsed = fir_parser.parse_pdf(file_bytes, filename)
    else:
        parsed = fir_parser.parse_text(file_bytes.decode("utf-8", errors="ignore"), filename)

    text = parsed.get("raw_text", "")
    if not text:
        raise HTTPException(status_code=422, detail="Could not extract text from document.")

    nlp_result = await _process_text_through_nlp(text, filename, use_llm)
    return {"status": "success", "parsed_fields": parsed, **nlp_result}


# ── CDR Endpoint ──────────────────────────────────────────────────────────────

@router.post("/cdr", summary="Ingest Call Detail Records (CDR)")
async def ingest_cdr(file: UploadFile = File(...)):
    """Upload a CDR CSV or Excel file."""
    file_bytes, filename = _save_upload(file)
    ext = Path(filename).suffix.lower()

    if ext in (".xlsx", ".xls"):
        parsed = cdr_parser.parse_excel(file_bytes, filename)
    else:
        parsed = cdr_parser.parse_csv(file_bytes, filename)

    if "error" in parsed:
        raise HTTPException(status_code=422, detail=parsed["error"])

    # CDR parsers already produce entities/relationships
    result = await graph_builder.ingest_extraction_result(parsed, source_doc=filename)
    return {
        "status": "success",
        "total_records": parsed["total_records"],
        **result,
    }


# ── Financial Endpoint ────────────────────────────────────────────────────────

@router.post("/financial", summary="Ingest financial transaction records")
async def ingest_financial(file: UploadFile = File(...)):
    """Upload a bank transaction CSV or Excel file."""
    file_bytes, filename = _save_upload(file)
    ext = Path(filename).suffix.lower()

    if ext in (".xlsx", ".xls"):
        parsed = financial_parser.parse_excel(file_bytes, filename)
    else:
        parsed = financial_parser.parse_csv(file_bytes, filename)

    if "error" in parsed:
        raise HTTPException(status_code=422, detail=parsed["error"])

    result = await graph_builder.ingest_extraction_result(parsed, source_doc=filename)
    return {
        "status": "success",
        "total_records": parsed["total_records"],
        "suspicious_count": parsed.get("suspicious_count", 0),
        **result,
    }


# ── Surveillance Endpoint ─────────────────────────────────────────────────────

@router.post("/surveillance", summary="Ingest surveillance report")
async def ingest_surveillance(
    file: Optional[UploadFile] = File(default=None),
    text: Optional[str] = Form(default=None),
    use_llm: bool = Form(default=False),
):
    """Upload surveillance report (TXT/PDF) or paste text directly."""
    if file:
        file_bytes, filename = _save_upload(file)
        raw_text = file_bytes.decode("utf-8", errors="ignore")
        parsed = surveillance_parser.parse_text(raw_text, filename)
    elif text:
        parsed = surveillance_parser.parse_text(text, "surveillance_text_input")
        filename = "surveillance_text_input"
    else:
        raise HTTPException(status_code=400, detail="Provide either a file or text.")

    result = await graph_builder.ingest_extraction_result(parsed, source_doc=filename)
    nlp_result = await _process_text_through_nlp(parsed.get("raw_text", ""), filename, use_llm)
    return {"status": "success", "parsed_fields": parsed, **result}


# ── Social Media Endpoint ─────────────────────────────────────────────────────

@router.post("/social", summary="Ingest social media intelligence")
async def ingest_social(
    text: str = Form(...),
    source_name: str = Form(default="social_media"),
):
    """Paste raw social media text or JSON for analysis."""
    parsed = social_parser.parse_text(text, source_name)
    result = await graph_builder.ingest_extraction_result(parsed, source_doc=source_name)
    return {"status": "success", **result}


# ── Generic Text Endpoint ─────────────────────────────────────────────────────

@router.post("/text", summary="Ingest free-text intelligence report")
async def ingest_text(
    text: str = Form(...),
    source_name: str = Form(default="manual_input"),
    use_llm: bool = Form(default=False),
):
    """Paste any free-text intelligence for NLP processing and graph storage."""
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Text too short.")
    result = await _process_text_through_nlp(text, source_name, use_llm)
    return {"status": "success", **result}
