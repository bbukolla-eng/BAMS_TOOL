import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


async def generate_proposal_pdf(proposal, db) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=20, spaceAfter=6, textColor=colors.HexColor("#1a3a5c"))
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#1a3a5c"), spaceBefore=12, spaceAfter=4)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, spaceAfter=8, leading=14)
    story = []

    # Header
    story.append(Paragraph("BAMS AI", ParagraphStyle("Company", parent=styles["Normal"], fontSize=11, textColor=colors.grey)))
    story.append(Paragraph("PROPOSAL", title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a3a5c")))
    story.append(Spacer(1, 12))

    # Proposal metadata table
    meta_data = [
        ["Proposal #:", proposal.proposal_number or f"P-{proposal.id:04d}", "Date:", str(proposal.created_at.date())],
        ["To:", proposal.client_name or "", "Valid Until:", str(proposal.expiry_date or "")],
        ["Attention:", proposal.attention_to or "", "", ""],
    ]
    meta_table = Table(meta_data, colWidths=[1.2*inch, 2.8*inch, 1.2*inch, 1.8*inch])
    meta_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#1a3a5c")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 16))

    # Project Description
    if proposal.project_description:
        story.append(Paragraph("PROJECT DESCRIPTION", heading_style))
        story.append(Paragraph(proposal.project_description, body_style))

    # Scope of Work
    if proposal.scope_of_work:
        story.append(Paragraph("SCOPE OF WORK", heading_style))
        story.append(Paragraph(proposal.scope_of_work, body_style))

    # Inclusions
    if proposal.inclusions:
        story.append(Paragraph("INCLUSIONS", heading_style))
        story.append(Paragraph(proposal.inclusions, body_style))

    # Exclusions
    if proposal.exclusions:
        story.append(Paragraph("EXCLUSIONS", heading_style))
        story.append(Paragraph(proposal.exclusions, body_style))

    # Clarifications
    if proposal.clarifications:
        story.append(Paragraph("CLARIFICATIONS & ASSUMPTIONS", heading_style))
        story.append(Paragraph(proposal.clarifications, body_style))

    # Bid total (if bid linked)
    if proposal.bid_id:
        from sqlalchemy import select

        from models.bid import Bid
        bid_result = await db.execute(select(Bid).where(Bid.id == proposal.bid_id))
        bid = bid_result.scalar_one_or_none()
        if bid:
            story.append(Spacer(1, 12))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
            story.append(Spacer(1, 8))
            price_data = [
                ["BASE BID TOTAL", f"${bid.grand_total:,.2f}"],
            ]
            price_table = Table(price_data, colWidths=[4*inch, 2*inch])
            price_table.setStyle(TableStyle([
                ("FONT", (0, 0), (-1, -1), "Helvetica-Bold", 14),
                ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#1a3a5c")),
                ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#1a3a5c")),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LINEABOVE", (0, 0), (-1, 0), 2, colors.HexColor("#1a3a5c")),
                ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#1a3a5c")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(price_table)

    # Terms
    if proposal.terms_conditions:
        story.append(Spacer(1, 16))
        story.append(Paragraph("TERMS & CONDITIONS", heading_style))
        story.append(Paragraph(proposal.terms_conditions, body_style))

    # Signature block
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 8))
    sig_data = [
        ["Submitted by:", "", "Accepted by:", ""],
        ["", "", "", ""],
        ["Signature:", "___________________________", "Signature:", "___________________________"],
        ["Date:", "___________________________", "Date:", "___________________________"],
    ]
    sig_table = Table(sig_data, colWidths=[1.2*inch, 2.1*inch, 1.2*inch, 2.1*inch])
    sig_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
        ("FONT", (0, 0), (0, 0), "Helvetica-Bold", 10),
        ("FONT", (2, 0), (2, 0), "Helvetica-Bold", 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_table)

    doc.build(story)
    return buf.getvalue()
