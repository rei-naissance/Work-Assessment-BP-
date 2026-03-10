"""Sitter Packet Generator.

Produces a concise printable document for guests, pet sitters, and house sitters.
Contains:
- Emergency Quick Start (Chapter 1)
- Water Leak + Power Outage Playbooks (from Chapter 3)
- Guest & Sitter Mode (Chapter 4)
- Contacts & Vendors (Chapter 7)
"""
from __future__ import annotations

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Table, TableStyle,
)

from app.models.profile import Profile
from app.rules.engine import select_modules
from app.templates.narrative import (
    TemplateWriter, Block, clear_unknown_placeholders
)
from app.pdf.generator import render_blocks, _build_styles, BRAND


def generate_sitter_packet(
    profile: Profile,
    output_path: str,
    tier: str = "premium",
    ai_content: dict | None = None
) -> str:
    """Generate a sitter packet PDF.

    Args:
        profile: User profile with home/contacts info.
        output_path: Path for output PDF.
        tier: Binder tier (standard/premium).
        ai_content: Optional AI-generated content.

    Returns:
        Path to generated PDF.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Clear unknown tracker for fresh render
    clear_unknown_placeholders()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = _build_styles()
    writer = TemplateWriter()
    sections = select_modules(profile, tier=tier)

    story = []

    # Cover
    hi = profile.home_identity
    nickname = hi.home_nickname or "Home"
    story.append(Paragraph(f"{nickname} — Sitter Packet", styles["CoverTitle"]))
    story.append(Spacer(1, 12))

    full_address = ", ".join(filter(None, [hi.address_line1, hi.city, hi.state, hi.zip_code]))
    if full_address:
        story.append(Paragraph(f"Property: {full_address}", styles["BodyText"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "This packet contains essential information for guests and sitters. "
        "For the full home operating manual, see the complete binder.",
        styles["BodyText"]
    ))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND))
    story.append(PageBreak())

    # Section 1: Emergency Quick Start
    story.append(Paragraph("Section 1", styles["SectionNumber"]))
    story.append(Paragraph("Emergency Quick Start", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND))
    story.append(Spacer(1, 12))

    section_1_data = sections.get("section_1", {})
    blocks = writer.write_quick_start(section_1_data, profile, ai_content=ai_content)
    story += render_blocks(blocks, styles)
    story.append(PageBreak())

    # Section 3 (partial): Water Leak + Power Outage Playbooks ONLY
    story.append(Paragraph("Emergency Playbooks", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND))
    story.append(Spacer(1, 12))

    section_3_data = sections.get("section_3", {})
    # Filter to only water leak and power outage playbooks
    sitter_playbooks = {
        k: v for k, v in section_3_data.items()
        if "water" in k.lower() or "power" in k.lower() or "outage" in k.lower()
    }

    if sitter_playbooks:
        blocks = writer.write_playbooks(sitter_playbooks, profile, ai_content=ai_content)
        story += render_blocks(blocks, styles)
    else:
        story.append(Paragraph(
            "Water leak and power outage playbooks not available. "
            "See full binder for emergency procedures.",
            styles["BodyText"]
        ))
    story.append(PageBreak())

    # Section 4: Guest & Sitter Mode
    story.append(Paragraph("Section 4", styles["SectionNumber"]))
    story.append(Paragraph("Guest & Sitter Mode", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND))
    story.append(Spacer(1, 12))

    blocks = writer.write_guest_mode(profile, ai_content=ai_content)
    story += render_blocks(blocks, styles)
    story.append(PageBreak())

    # Section 7: Contacts & Vendors
    story.append(Paragraph("Section 7", styles["SectionNumber"]))
    story.append(Paragraph("Contacts & Vendors", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND))
    story.append(Spacer(1, 12))

    blocks = writer.write_contacts(profile, ai_content=ai_content)
    story += render_blocks(blocks, styles)

    # Footer note
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#d1d5db")))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "For complete emergency procedures, maintenance guides, and home systems information, "
        "refer to the full BinderPro.",
        styles["BodyText"]
    ))

    doc.build(story)
    return output_path


def generate_sitter_packet_markdown(
    profile: Profile,
    tier: str = "premium",
    ai_content: dict | None = None
) -> str:
    """Generate sitter packet as Markdown string.

    Args:
        profile: User profile.
        tier: Binder tier.
        ai_content: Optional AI content.

    Returns:
        Markdown string.
    """
    clear_unknown_placeholders()

    writer = TemplateWriter()
    sections = select_modules(profile, tier=tier)

    lines = []
    hi = profile.home_identity
    nickname = hi.home_nickname or "Home"

    lines.append(f"# {nickname} — Sitter Packet\n")
    full_address = ", ".join(filter(None, [hi.address_line1, hi.city, hi.state, hi.zip_code]))
    if full_address:
        lines.append(f"**Property:** {full_address}\n")
    lines.append(
        "This packet contains essential information for guests and sitters. "
        "For the full home operating manual, see the complete binder.\n"
    )
    lines.append("---\n")

    # Section 1: Quick Start
    lines.append("## Section 1: Emergency Quick Start\n")
    section_1_data = sections.get("section_1", {})
    blocks = writer.write_quick_start(section_1_data, profile, ai_content=ai_content)
    lines.append(_blocks_to_markdown(blocks))

    # Water + Power Playbooks
    lines.append("\n## Emergency Playbooks\n")
    section_3_data = sections.get("section_3", {})
    sitter_playbooks = {
        k: v for k, v in section_3_data.items()
        if "water" in k.lower() or "power" in k.lower() or "outage" in k.lower()
    }
    if sitter_playbooks:
        blocks = writer.write_playbooks(sitter_playbooks, profile, ai_content=ai_content)
        lines.append(_blocks_to_markdown(blocks))

    # Section 4: Guest Mode
    lines.append("\n## Section 4: Guest & Sitter Mode\n")
    blocks = writer.write_guest_mode(profile, ai_content=ai_content)
    lines.append(_blocks_to_markdown(blocks))

    # Section 7: Contacts
    lines.append("\n## Section 7: Contacts & Vendors\n")
    blocks = writer.write_contacts(profile, ai_content=ai_content)
    lines.append(_blocks_to_markdown(blocks))

    lines.append("\n---\n")
    lines.append(
        "*For complete emergency procedures and maintenance guides, "
        "refer to the full BinderPro.*\n"
    )

    return "\n".join(lines)


def _blocks_to_markdown(blocks: list[Block]) -> str:
    """Convert Block objects to Markdown."""
    lines = []
    for block in blocks:
        if block.type == "heading":
            prefix = "#" * block.level
            lines.append(f"{prefix} {block.text}\n")
        elif block.type == "subheading":
            prefix = "#" * (block.level + 1)
            lines.append(f"{prefix} {block.text}\n")
        elif block.type == "paragraph":
            lines.append(f"{block.text}\n")
        elif block.type == "numbered_list":
            for i, item in enumerate(block.items, 1):
                lines.append(f"{i}. {item}")
            lines.append("")
        elif block.type == "checklist":
            for item in block.items:
                lines.append(f"- [ ] {item}")
            lines.append("")
        elif block.type == "callout_box":
            lines.append(f"> **{block.text}**\n")
        elif block.type == "table":
            if block.headers:
                lines.append("| " + " | ".join(block.headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(block.headers)) + " |")
            for row in block.rows:
                lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
            lines.append("")
        elif block.type == "spacer":
            lines.append("")
        elif block.type == "page_break":
            lines.append("\n---\n")
    return "\n".join(lines)
