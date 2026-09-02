"""
ai/report_generator.py — Generates formatted intelligence reports per entity.
Uses the LLM + graph data to produce structured investigation reports.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from graph.neo4j_client import neo4j_client
from ai.risk_scorer import risk_scorer
from analytics.timeline_builder import timeline_builder
from config import settings

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates structured intelligence reports for entities."""

    async def generate_report(self, entity_id: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Generate a complete intelligence report for an entity.
        """
        # ── 1. Fetch entity data ──────────────────────────────────────────────
        entity_record = await neo4j_client.get_entity(entity_id)
        if not entity_record:
            return {"error": f"Entity {entity_id} not found"}

        node   = entity_record.get("n", {})
        labels = entity_record.get("labels", ["Unknown"])
        name   = node.get("name", entity_id)

        # ── 2. Risk score ─────────────────────────────────────────────────────
        risk = await risk_scorer.score_entity(entity_id)

        # ── 3. Known associates (1-hop neighbors) ─────────────────────────────
        neighbors = await neo4j_client.get_neighbors(entity_id, depth=1)
        associates = [
            {"id": n["id"], "name": n.get("name", ""), "type": n.get("labels", [""])[0]}
            for n in neighbors.get("nodes", [])
            if n.get("id") != entity_id
        ][:20]

        # ── 4. Timeline ───────────────────────────────────────────────────────
        timeline = await timeline_builder.get_entity_timeline(entity_id)
        timeline_highlights = timeline.get("events", [])[:10]

        # ── 5. LLM narrative summary ──────────────────────────────────────────
        ai_summary = ""
        if use_llm:
            ai_summary = await self._generate_llm_summary(name, labels, risk, associates, timeline_highlights)

        # ── 6. Recommendations ────────────────────────────────────────────────
        recommendations = self._generate_recommendations(risk)

        report = {
            "entity_id": entity_id,
            "entity_name": name,
            "entity_type": labels[0] if labels else "Unknown",
            "risk_score": risk.get("risk_score", 0),
            "risk_level": risk.get("risk_level", "UNKNOWN"),
            "risk_breakdown": risk.get("breakdown", {}),
            "summary": ai_summary or self._fallback_summary(name, risk, associates),
            "known_associates": associates,
            "associate_count": len(associates),
            "timeline_highlights": timeline_highlights,
            "total_events": timeline.get("total_events", 0),
            "community_membership": f"Community {node.get('community_id', 'N/A')}",
            "centrality_scores": {
                "pagerank":     node.get("pagerank"),
                "betweenness":  node.get("betweenness_centrality"),
                "degree":       node.get("degree_centrality"),
            },
            "recommendations": recommendations,
            "source_documents": node.get("source_documents", []),
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }

        return report

    async def _generate_llm_summary(
        self,
        name: str,
        labels: List[str],
        risk: Dict,
        associates: List[Dict],
        timeline: List[Dict],
    ) -> str:
        try:
            from langchain_ollama import OllamaLLM

            associate_names = ", ".join(a["name"] for a in associates[:5]) or "none identified"
            recent_events   = "; ".join(
                f"{e.get('event_type', '')} with {e.get('other_entity', '')}"
                for e in timeline[:5]
            ) or "no recent events"

            prompt = f"""You are a senior criminal intelligence analyst.
Write a concise (3-5 sentences) intelligence assessment for the following subject.

Subject: {name} ({', '.join(labels)})
Risk Level: {risk.get('risk_level')} (Score: {risk.get('risk_score', 0):.1f}/100)
Known Associates: {associate_names}
Recent Activity: {recent_events}

Write the assessment in professional law enforcement report style.
Focus on network position, threat level, and investigative priority."""

            llm = OllamaLLM(base_url=settings.ollama_url, model=settings.ollama_model)
            return llm.invoke(prompt)
        except Exception as e:
            logger.warning(f"LLM summary generation failed: {e}")
            return ""

    def _fallback_summary(self, name: str, risk: Dict, associates: List[Dict]) -> str:
        level  = risk.get("risk_level", "UNKNOWN")
        score  = risk.get("risk_score", 0)
        n_assoc = len(associates)
        return (
            f"{name} has been assessed as {level} risk (score: {score:.1f}/100) "
            f"with {n_assoc} known associates in the network. "
            "Further investigation is recommended based on network centrality analysis."
        )

    def _generate_recommendations(self, risk: Dict) -> List[str]:
        recs = []
        level = risk.get("risk_level", "LOW")
        score = risk.get("risk_score", 0)

        if level == "CRITICAL":
            recs.append("🔴 URGENT: Initiate immediate surveillance and request interception warrant.")
            recs.append("Coordinate with financial intelligence unit for asset tracing.")
        elif level == "HIGH":
            recs.append("🟠 Priority investigation target. Assign dedicated case officer.")
            recs.append("Cross-reference with pending FIRs and court records.")
        elif level == "MEDIUM":
            recs.append("🟡 Monitor communications and financial activity.")
            recs.append("Verify known addresses and associates.")
        else:
            recs.append("🟢 Maintain in watch list. No immediate action required.")

        bd = risk.get("breakdown", {})
        if bd.get("betweenness_contribution", 0) > 10:
            recs.append("Subject is a network broker — disrupting this node will fragment the criminal network.")
        if bd.get("criminal_history_contribution", 0) > 15:
            recs.append("Prior criminal history significantly elevates risk profile.")

        return recs


    async def generate_report_pdf(self, entity_id: str, use_llm: bool = True) -> io.BytesIO:
        """
        Generate a PDF version of the intelligence report.
        Returns a BytesIO buffer containing the PDF.
        """
        report = await self.generate_report(entity_id, use_llm=use_llm)
        if "error" in report:
            raise ValueError(report["error"])

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=20*mm, rightMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        story: list = []

        # Custom styles
        title_style = ParagraphStyle('ReportTitle', parent=styles['Title'],
                                      fontSize=18, textColor=colors.HexColor('#1e293b'),
                                      spaceAfter=6)
        subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                         fontSize=10, textColor=colors.grey,
                                         spaceAfter=12)
        heading_style = ParagraphStyle('H2', parent=styles['Heading2'],
                                        fontSize=13, textColor=colors.HexColor('#e63946'),
                                        spaceBefore=14, spaceAfter=6)
        body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                     fontSize=10, leading=14, spaceAfter=6)
        rec_style = ParagraphStyle('Rec', parent=styles['Normal'],
                                    fontSize=10, leading=14, leftIndent=12, spaceAfter=4)

        # ── Header ─────────────────────────────────────────────────────────
        story.append(Paragraph('INTELLIGENCE REPORT — RESTRICTED', title_style))
        story.append(Paragraph(
            f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")} · '
            f'For Law Enforcement Use Only', subtitle_style))
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#334155')))
        story.append(Spacer(1, 8))

        # ── Subject ────────────────────────────────────────────────────────
        story.append(Paragraph('SUBJECT', heading_style))
        risk_color = {'CRITICAL': '#dc2626', 'HIGH': '#ea580c', 'MEDIUM': '#ca8a04', 'LOW': '#16a34a'}
        rc = risk_color.get(report.get('risk_level', ''), '#1e293b')
        story.append(Paragraph(
            f'<b>{report["entity_name"]}</b> — {report["entity_type"]}', body_style))
        story.append(Paragraph(
            f'Risk Level: <font color="{rc}"><b>{report["risk_level"]}</b></font> '
            f'(Score: {report["risk_score"]:.1f}/100)', body_style))
        story.append(Paragraph(
            f'Community: {report["community_membership"]}', body_style))
        story.append(Spacer(1, 6))

        # ── Executive Summary ──────────────────────────────────────────────
        story.append(Paragraph('EXECUTIVE SUMMARY', heading_style))
        story.append(Paragraph(report.get('summary', 'N/A'), body_style))

        # ── Risk Breakdown ─────────────────────────────────────────────────
        story.append(Paragraph('RISK BREAKDOWN', heading_style))
        bd = report.get('risk_breakdown', {})
        if bd:
            tdata = [['Factor', 'Score']]
            for k, v in bd.items():
                tdata.append([k.replace('_contribution', '').replace('_', ' ').title(), f'{v:.1f}'])
            t = Table(tdata, colWidths=[140, 60])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#475569')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
            ]))
            story.append(t)

        # ── Centrality Scores ──────────────────────────────────────────────
        story.append(Paragraph('NETWORK POSITION', heading_style))
        cs = report.get('centrality_scores', {})
        if cs:
            story.append(Paragraph(
                f'PageRank: {(cs.get("pagerank") or 0) * 1000:.2f} · '
                f'Betweenness: {((cs.get("betweenness") or 0) * 100):.1f}% · '
                f'Degree: {((cs.get("degree") or 0) * 100):.1f}%', body_style))

        # ── Known Associates ───────────────────────────────────────────────
        story.append(Paragraph(f'KNOWN ASSOCIATES ({report.get("associate_count", 0)})', heading_style))
        for a in report.get('known_associates', [])[:15]:
            story.append(Paragraph(f'• {a["name"]} ({a["type"]})', rec_style))

        # ── Recommendations ────────────────────────────────────────────────
        story.append(Paragraph('INVESTIGATIVE RECOMMENDATIONS', heading_style))
        for r in report.get('recommendations', []):
            story.append(Paragraph(f'• {r}', rec_style))

        # ── Footer ─────────────────────────────────────────────────────────
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#94a3b8')))
        story.append(Paragraph(
            f'Sources: {"; ".join(report.get("source_documents", [])) or "N/A"} · '
            f'Generated: {report.get("generated_at", "")}',
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)))

        doc.build(story)
        buf.seek(0)
        return buf


# ── Singleton ─────────────────────────────────────────────────────────────────
report_generator = ReportGenerator()
