"""
api/routes/ai.py — AI / LLM endpoints.
Handles natural language Q&A and intelligence report generation.
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ai.rag_engine import rag_engine
from ai.report_generator import report_generator
from ai.risk_scorer import risk_scorer

router = APIRouter()
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


@router.post("/query", summary="Natural language investigator Q&A")
async def query(request: QueryRequest):
    """
    Answer investigator questions using Graph RAG.
    Examples:
    - "Who are the associates of Rajan Sharma?"
    - "What locations did the gang visit in October?"
    - "Who is the most influential person in the network?"
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    result = await rag_engine.answer(request.question)
    return result


@router.get("/report/{entity_id}", summary="Generate intelligence report")
async def generate_report(entity_id: str, use_llm: bool = True):
    """
    Generate a full intelligence report for an entity including:
    - Risk score and level
    - Known associates
    - Event timeline
    - AI-generated narrative summary
    - Recommendations
    """
    report = await report_generator.generate_report(entity_id, use_llm=use_llm)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return report


@router.get("/report/{entity_id}/pdf", summary="Download intelligence report as PDF")
async def generate_report_pdf(entity_id: str, use_llm: bool = True):
    """
    Generate a PDF intelligence report for an entity.
    Returns the PDF as a downloadable file.
    """
    try:
        buf = await report_generator.generate_report_pdf(entity_id, use_llm=use_llm)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Build a safe filename from the entity ID
    safe_name = entity_id.replace(" ", "_").replace("/", "-")[:50]
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="intel-report-{safe_name}.pdf"'
        },
    )


@router.get("/risk/{entity_id}", summary="Get entity risk score")
async def get_risk(entity_id: str):
    """Retrieve composite risk score for an entity."""
    result = await risk_scorer.score_entity(entity_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
