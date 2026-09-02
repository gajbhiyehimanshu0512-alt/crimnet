"""
backend/tests/test_report_pdf.py — Unit tests for PDF report generation.
Run with: pytest backend/tests/test_report_pdf.py -v
"""

import pytest
import io
from unittest.mock import AsyncMock, patch


# ── PDF Generation (unit test, no Neo4j required) ────────────────────────────

def _make_sample_report() -> dict:
    """Return a sample report dict matching the ReportGenerator output schema."""
    from datetime import datetime, timezone
    return {
        "entity_id": "test-123",
        "entity_name": "Rajan Sharma",
        "entity_type": "Person",
        "risk_score": 78.5,
        "risk_level": "HIGH",
        "risk_breakdown": {
            "centrality_contribution": 15.0,
            "criminal_history_contribution": 30.0,
            "financial_contribution": 33.5,
        },
        "summary": "Rajan Sharma is assessed as a HIGH risk individual with significant network centrality.",
        "known_associates": [
            {"id": "a1", "name": "Mohan Pillai", "type": "Person"},
            {"id": "a2", "name": "Gang X", "type": "Organization"},
        ],
        "associate_count": 2,
        "timeline_highlights": [],
        "total_events": 5,
        "community_membership": "Community 3",
        "centrality_scores": {
            "pagerank": 0.045,
            "betweenness": 0.32,
            "degree": 0.21,
        },
        "recommendations": [
            "Priority investigation target. Assign dedicated case officer.",
            "Subject is a network broker — disrupting this node will fragment the criminal network.",
        ],
        "source_documents": ["FIR_123.pdf", "CDR_dump.csv"],
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def test_reportlab_produces_valid_pdf():
    """Verify reportlab itself can build a valid PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    doc.build([Paragraph("Test Report", styles['Title'])])
    buf.seek(0)
    content = buf.read()
    assert content[:5] == b'%PDF-'
    assert len(content) > 100


def test_report_pdf_content_valid():
    """Verify generate_report_pdf produces a valid PDF from a mock report."""
    from ai.report_generator import ReportGenerator

    gen = ReportGenerator()
    report_data = _make_sample_report()

    with patch.object(gen, 'generate_report', new_callable=AsyncMock, return_value=report_data):
        import asyncio
        buf = asyncio.run(gen.generate_report_pdf("test-123", use_llm=False))
        assert isinstance(buf, io.BytesIO)
        buf.seek(0)
        pdf_bytes = buf.read()
        assert pdf_bytes[:5] == b'%PDF-'
        assert len(pdf_bytes) > 500


def test_report_pdf_raises_on_error_report():
    """generate_report_pdf should raise ValueError if report contains error."""
    from ai.report_generator import ReportGenerator

    gen = ReportGenerator()
    with patch.object(gen, 'generate_report', new_callable=AsyncMock,
                      return_value={"error": "Entity not found"}):
        import asyncio
        with pytest.raises(ValueError, match="Entity not found"):
            asyncio.run(gen.generate_report_pdf("nonexistent"))


# ── API Integration (uses shared client/auth_headers fixtures) ────────────────

def test_pdf_endpoint_requires_auth(client):
    """PDF endpoint should reject unauthenticated requests."""
    resp = client.get("/api/ai/report/some-id/pdf")
    assert resp.status_code == 401


def test_pdf_endpoint_with_token_mocked(client, auth_headers):
    """PDF endpoint should return a PDF when entity exists (mocked)."""
    with patch("api.routes.ai.report_generator.generate_report_pdf",
               new_callable=AsyncMock) as mock_pdf:
        buf = io.BytesIO(b'%PDF-1.4 test')
        mock_pdf.return_value = buf
        resp = client.get("/api/ai/report/test-123/pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"


def test_pdf_endpoint_404_on_missing_entity(client, auth_headers):
    """PDF endpoint should return 404 if entity not found."""
    with patch("api.routes.ai.report_generator.generate_report_pdf",
               new_callable=AsyncMock) as mock_pdf:
        mock_pdf.side_effect = ValueError("Entity xyz not found")
        resp = client.get("/api/ai/report/xyz/pdf", headers=auth_headers)
        assert resp.status_code == 404
